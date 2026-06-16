"""Run batch actual temporary smoke for readiness-passed IEEE39 bus faults.

This script runs actual Simulink smoke for the 37 all-remaining bus-fault
temporary local copies that passed readiness dry-run. It does not export
labels, does not train GCN, does not retrain the reranker, and does not run a
GCN usefulness audit.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BATCH_ID = "bus_fault_all_remaining_manual_wiring"
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
READINESS_DIR = BASE / "readiness_dry_run"
PLAN_JSON = READINESS_DIR / "batch_actual_smoke_plan_manifest.json"
READINESS_SUMMARY_JSON = READINESS_DIR / "batch_readiness_dry_run_summary.json"
DEFAULT_OUT = BASE / "batch_smoke_outputs"

SUMMARY_FIELDS = [
    "target_bus",
    "scenario_id",
    "special_handling",
    "actual_simulink_run",
    "dry_run",
    "smoke_executed",
    "simulation_success",
    "physical_fault_or_breaker_action_executed",
    "measurement_extraction_status",
    "training_ready_candidate_smoke",
    "timeout_or_error_message",
    "fault_start_s",
    "fault_clear_s",
    "duration_s",
    "selected_fault_block_path",
    "temp_model_path",
    "actual_checked_model_path",
    "source_slx_modified",
    "temporary_slx_committed",
    "labels_exported",
    "candidate_label_exported",
    "gcn_trained",
    "reranker_retrained",
    "gcn_usefulness_audit_run",
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "unstable_flag",
    "signal_source_summary",
    "old_formal_gate",
    "current_candidate_count",
    "b39_b26_status",
    "next_action",
]


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=True)
        handle.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8") as handle:
        handle.write(text)


def _matlab_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _float_or_nan(value: Any) -> float:
    try:
        if value is None or str(value).strip() == "":
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _validate_readiness() -> tuple[dict[str, Any], dict[str, Any]]:
    summary = _read_json(READINESS_SUMMARY_JSON)
    plan = _read_json(PLAN_JSON)
    if summary.get("num_ready_for_next_round_actual_smoke") != 37 or summary.get("num_blocked_before_smoke") != 0:
        raise RuntimeError("Readiness summary is not 37 ready / 0 blocked; refusing batch smoke.")
    if plan.get("actual_smoke_run_this_round") is not False or plan.get("should_run_smoke_now") is not False:
        raise RuntimeError("Plan manifest must be a next-round plan only before this smoke runner starts.")
    ready = list(plan.get("ready_buses", []))
    if len(ready) != 37:
        raise RuntimeError(f"Expected 37 ready buses in manifest, got {len(ready)}.")
    return summary, plan


def _write_matlab_runner(
    out_dir: Path,
    bus: str,
    actual_model_path: Path,
    selected_fault_block_path: str,
    fault_start_s: float,
    duration_s: float,
    simulation_stop_time: float,
) -> Path:
    scenario_id = f"BF_{bus}_TEMP_SMOKE"
    matlab_dir = ROOT / "matlab/simulink_ieee39"
    summary_name = f"_matlab_batch_smoke_{bus}.csv"
    fault_suffix = selected_fault_block_path.replace("Grid/", "Grid/")
    script_path = out_dir / f"run_{scenario_id}.m"
    script = f"""
cd('{_matlab_path(matlab_dir)}');
addpath('{_matlab_path(matlab_dir)}');
configure_ieee39_short_filegen_paths();
if ~exist('{_matlab_path(out_dir)}', "dir")
    mkdir('{_matlab_path(out_dir)}');
end
success = false;
physicalExecuted = false;
errorMessage = "";
simOut = [];
try
    load_system('{_matlab_path(actual_model_path)}');
    [~, modelName, ~] = fileparts('{_matlab_path(actual_model_path)}');
    faultBlock = string(modelName) + "/{fault_suffix}";
    in = Simulink.SimulationInput(modelName);
    in = in.setModelParameter("StopTime", "{simulation_stop_time:.6f}");
    in = in.setBlockParameter(faultBlock, "enable_temporal_fault", "1");
    in = in.setBlockParameter(faultBlock, "fault_start_time", "{fault_start_s:.6f}");
    in = in.setBlockParameter(faultBlock, "fault_duration", "{duration_s:.6f}");
    simOut = sim(in);
    success = true;
    physicalExecuted = true;
    close_system(modelName, 0);
catch ME
    errorMessage = string(ME.message);
    try
        [~, modelName, ~] = fileparts('{_matlab_path(actual_model_path)}');
        close_system(modelName, 0);
    catch
    end
end
if success
    try
        signalSummary = extract_ieee39_signal_summary(simOut, "{scenario_id}", '{_matlab_path(out_dir)}');
    catch ME
        signalSummary = struct();
        signalSummary.min_voltage_pu = NaN;
        signalSummary.max_voltage_pu = NaN;
        signalSummary.min_frequency_hz = NaN;
        signalSummary.max_frequency_hz = NaN;
        signalSummary.max_speed_deviation = NaN;
        signalSummary.max_rotor_angle_separation_deg = NaN;
        signalSummary.measurement_extraction_status = "measurement_extract_failed";
        signalSummary.signal_source_summary = "";
        errorMessage = string(ME.message);
    end
else
    signalSummary = struct();
    signalSummary.min_voltage_pu = NaN;
    signalSummary.max_voltage_pu = NaN;
    signalSummary.min_frequency_hz = NaN;
    signalSummary.max_frequency_hz = NaN;
    signalSummary.max_speed_deviation = NaN;
    signalSummary.max_rotor_angle_separation_deg = NaN;
    signalSummary.measurement_extraction_status = "simulation_failed";
    signalSummary.signal_source_summary = "";
end
unstable = signalSummary.min_frequency_hz < 49.0 || signalSummary.min_voltage_pu < 0.8 || signalSummary.max_rotor_angle_separation_deg > 180.0;
trainingReady = success && physicalExecuted && string(signalSummary.measurement_extraction_status) == "voltage_speed_angle";
summaryTable = table( ...
    string("{scenario_id}"), string("{bus}"), {fault_start_s:.6f}, {fault_start_s + duration_s:.6f}, {duration_s:.6f}, ...
    success, physicalExecuted, string(signalSummary.measurement_extraction_status), trainingReady, string(errorMessage), ...
    signalSummary.min_voltage_pu, signalSummary.max_voltage_pu, signalSummary.min_frequency_hz, signalSummary.max_frequency_hz, ...
    signalSummary.max_speed_deviation, signalSummary.max_rotor_angle_separation_deg, unstable, string(signalSummary.signal_source_summary), ...
    'VariableNames', {{'scenario_id','target_bus','fault_start_s','fault_clear_s','duration_s','simulation_success','physical_fault_or_breaker_action_executed','measurement_extraction_status','training_ready_candidate_smoke','timeout_or_error_message','min_voltage_pu','max_voltage_pu','min_frequency_hz','max_frequency_hz','max_speed_deviation','max_rotor_angle_separation_deg','unstable_flag','signal_source_summary'}} ...
);
writetable(summaryTable, fullfile('{_matlab_path(out_dir)}', "{summary_name}"));
"""
    _write_text(script_path, script.strip() + "\n")
    return script_path


def _run_matlab(script_path: Path, timeout_seconds: int) -> tuple[str, bool, str]:
    try:
        completed = subprocess.run(
            ["matlab", "-batch", f"run('{_matlab_path(script_path)}')"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
        output = completed.stdout or ""
        if completed.returncode != 0:
            return output, False, f"MATLAB exited with code {completed.returncode}"
        return output, False, ""
    except subprocess.TimeoutExpired as exc:
        return exc.stdout or "", True, f"MATLAB run timed out after {timeout_seconds} seconds"
    except FileNotFoundError:
        return "", False, "MATLAB executable not found on PATH"


def _read_matlab_summary(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    with open(_fs_path(path), encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[0] if rows else None


def _row_from_matlab(
    bus: str,
    readiness: dict[str, Any],
    matlab_summary: dict[str, str] | None,
    timed_out: bool,
    error_message: str,
) -> dict[str, Any]:
    scenario_id = f"BF_{bus}_TEMP_SMOKE"
    simulation_success = bool(matlab_summary and _boolish(matlab_summary.get("simulation_success")))
    measurement_status = (
        str(matlab_summary.get("measurement_extraction_status", ""))
        if matlab_summary
        else ("simulation_timeout" if timed_out else "simulation_failed")
    )
    physical_executed = bool(matlab_summary and _boolish(matlab_summary.get("physical_fault_or_breaker_action_executed")))
    signal_source = str(matlab_summary.get("signal_source_summary", "")) if matlab_summary else ""
    training_ready = bool(
        simulation_success
        and physical_executed
        and measurement_status == "voltage_speed_angle"
        and "frequency=generator_speed_proxy" in signal_source
    )
    timeout_or_error = ""
    if timed_out:
        timeout_or_error = error_message
    elif not simulation_success:
        timeout_or_error = error_message or (str(matlab_summary.get("timeout_or_error_message", "")) if matlab_summary else "")
    elif measurement_status != "voltage_speed_angle":
        timeout_or_error = str(matlab_summary.get("timeout_or_error_message", "")) if matlab_summary else ""
    next_action = (
        "smoke quality review before any label export"
        if training_ready
        else "diagnose failed smoke before quality review"
    )
    return {
        "batch_id": BATCH_ID,
        "target_bus": bus,
        "scenario_id": scenario_id,
        "special_handling": bool(readiness.get("special_handling")),
        "actual_simulink_run": True,
        "dry_run": False,
        "smoke_executed": True,
        "simulation_success": simulation_success,
        "physical_fault_or_breaker_action_executed": physical_executed,
        "measurement_extraction_status": measurement_status,
        "training_ready_candidate_smoke": training_ready,
        "timeout_or_error_message": timeout_or_error,
        "fault_start_s": 0.5,
        "fault_clear_s": 0.58,
        "duration_s": 0.08,
        "selected_fault_block_path": f"Grid/Fault_{bus}_TEMP",
        "temp_model_path": readiness.get("temp_model_path", ""),
        "actual_checked_model_path": readiness.get("actual_checked_model_path", ""),
        "source_slx_modified": False,
        "temporary_slx_committed": False,
        "labels_exported": False,
        "candidate_label_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "min_voltage_pu": _float_or_nan(matlab_summary.get("min_voltage_pu")) if matlab_summary else math.nan,
        "max_voltage_pu": _float_or_nan(matlab_summary.get("max_voltage_pu")) if matlab_summary else math.nan,
        "min_frequency_hz": _float_or_nan(matlab_summary.get("min_frequency_hz")) if matlab_summary else math.nan,
        "max_frequency_hz": _float_or_nan(matlab_summary.get("max_frequency_hz")) if matlab_summary else math.nan,
        "max_speed_deviation": _float_or_nan(matlab_summary.get("max_speed_deviation")) if matlab_summary else math.nan,
        "max_rotor_angle_separation_deg": _float_or_nan(matlab_summary.get("max_rotor_angle_separation_deg")) if matlab_summary else math.nan,
        "unstable_flag": bool(matlab_summary and _boolish(matlab_summary.get("unstable_flag"))),
        "signal_source_summary": signal_source,
        "old_formal_gate": "35 / 33 / 33",
        "current_candidate_count": 42,
        "b39_b26_status": "existing_candidate_labels_not_formal",
        "next_action": next_action,
    }


def _write_per_bus_outputs(out_dir: Path, row: dict[str, Any]) -> None:
    bus = str(row["target_bus"])
    csv_path = out_dir / f"batch_smoke_{bus}_summary.csv"
    json_path = out_dir / f"batch_smoke_{bus}_report.json"
    md_path = out_dir / f"batch_smoke_{bus}_report.md"
    _write_csv(csv_path, [row], SUMMARY_FIELDS)
    _write_json(json_path, row)
    md = f"""# IEEE39 {bus} Batch Actual Temporary Smoke

This is actual temporary smoke evidence only. It is not a candidate label and
not a formal label.

| field | value |
| --- | --- |
| scenario_id | `{row['scenario_id']}` |
| actual_simulink_run | `{str(row['actual_simulink_run']).lower()}` |
| simulation_success | `{str(row['simulation_success']).lower()}` |
| measurement_extraction_status | `{row['measurement_extraction_status']}` |
| training_ready_candidate_smoke | `{str(row['training_ready_candidate_smoke']).lower()}` |
| unstable_flag | `{str(row['unstable_flag']).lower()}` |
| next_action | `{row['next_action']}` |

No labels were exported, GCN was not trained, the reranker was not retrained,
and no GCN usefulness audit was run. `phasor_RMS` is not EMT, and
`generator_speed_proxy` is not direct frequency.
"""
    _write_text(md_path, md)


def _summary_md(summary: dict[str, Any]) -> str:
    return f"""# IEEE39 All-Remaining Bus-Fault Batch Actual Smoke

This round ran actual Simulink smoke for the readiness-passed temporary local
copies. It did not export labels, did not train GCN, did not retrain the
reranker, and did not run a GCN usefulness audit.

| metric | value |
| --- | ---: |
| total_targets | {summary['total_targets']} |
| num_smoke_attempted | {summary['num_smoke_attempted']} |
| num_simulation_success | {summary['num_simulation_success']} |
| num_simulation_failed | {summary['num_simulation_failed']} |
| num_timeout | {summary['num_timeout']} |
| unstable_flag_true_count | {summary['unstable_flag_true_count']} |

Successful smoke is only temporary smoke evidence. The 37 new targets are not
candidate labels. The next step is smoke quality review for successful buses
before any label export.
"""


def _doc_md(summary: dict[str, Any]) -> str:
    return f"""# IEEE39 All-Remaining Bus-Fault Batch Actual Smoke

This round is batch actual smoke for the 37 readiness-passed IEEE39 bus-fault
temporary local copies. Actual Simulink smoke was run, but this round did not
export labels, did not train GCN, did not retrain the reranker, and did not run
a GCN usefulness audit.

## Result

- total targets: `{summary['total_targets']}`
- smoke attempted: `{summary['num_smoke_attempted']}`
- simulation success: `{summary['num_simulation_success']}`
- simulation failed: `{summary['num_simulation_failed']}`
- timeout: `{summary['num_timeout']}`
- unstable_flag true count: `{summary['unstable_flag_true_count']}`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

Even if a smoke run succeeded, it is only temporary smoke evidence. The 37 new
targets are still not candidate labels. The next required step is smoke quality
review for successful buses. Failed or timeout buses cannot enter quality
review before diagnosis.

B16 special handling is preserved, and the old B16 fault was not moved.
B39/B26 remain existing candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.
"""


def _quality_review_candidate_list(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": BATCH_ID,
        "ready_for_quality_review_buses": summary["successful_buses"],
        "blocked_from_quality_review_buses": summary["failed_buses"] + summary["timeout_buses"],
        "ready_count": len(summary["successful_buses"]),
        "blocked_count": len(summary["failed_buses"]) + len(summary["timeout_buses"]),
        "should_run_quality_review_now": False,
        "should_export_labels_now": False,
        "should_train_now": False,
        "criteria": {
            "simulation_success": True,
            "measurement_extraction_status": "voltage_speed_angle",
            "physical_fault_or_breaker_action_executed": True,
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    _, plan = _validate_readiness()
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    ready_buses = list(plan["ready_buses"])
    rows: list[dict[str, Any]] = []
    for index, bus in enumerate(ready_buses, start=1):
        readiness = _read_json(READINESS_DIR / f"readiness_dry_run_{bus}.json")
        actual_model_text = readiness.get("actual_checked_model_path") or readiness.get("temp_model_path")
        actual_model_path = Path(str(actual_model_text))
        if not actual_model_path.exists():
            row = _row_from_matlab(bus, readiness, None, False, f"Actual checked model not found: {actual_model_path}")
        else:
            print(f"[{index}/{len(ready_buses)}] Running {bus} actual temporary smoke...")
            runner = _write_matlab_runner(
                out_dir,
                bus,
                actual_model_path,
                str(readiness.get("selected_fault_block_path", f"Grid/Fault_{bus}_TEMP")),
                float(readiness.get("fault_start_s", 0.5)),
                float(readiness.get("duration_s", 0.08)),
                float(args.simulation_stop_time),
            )
            stdout, timed_out, error = _run_matlab(runner, args.timeout_seconds)
            stdout_path = out_dir / f"_matlab_stdout_{bus}.log"
            _write_text(stdout_path, stdout)
            matlab_summary = _read_matlab_summary(out_dir / f"_matlab_batch_smoke_{bus}.csv")
            row = _row_from_matlab(bus, readiness, matlab_summary, timed_out, error)
        _write_per_bus_outputs(out_dir, row)
        rows.append(row)

    successful = [r["target_bus"] for r in rows if r["simulation_success"] and r["measurement_extraction_status"] == "voltage_speed_angle"]
    timeout = [r["target_bus"] for r in rows if r["measurement_extraction_status"] == "simulation_timeout"]
    failed = [r["target_bus"] for r in rows if r["target_bus"] not in successful and r["target_bus"] not in timeout]
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["measurement_extraction_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    summary = {
        "batch_id": BATCH_ID,
        "smoke_scope": "actual_temporary_smoke_only",
        "total_targets": 37,
        "num_smoke_attempted": len(rows),
        "num_simulation_success": len(successful),
        "num_simulation_failed": len(failed),
        "num_timeout": len(timeout),
        "successful_buses": successful,
        "failed_buses": failed,
        "timeout_buses": timeout,
        "measurement_extraction_status_counts": status_counts,
        "unstable_flag_true_count": sum(1 for r in rows if r["unstable_flag"]),
        "unstable_flag_false_count": sum(1 for r in rows if not r["unstable_flag"]),
        "min_voltage_by_bus": {r["target_bus"]: r["min_voltage_pu"] for r in rows},
        "max_frequency_by_bus": {r["target_bus"]: r["max_frequency_hz"] for r in rows},
        "max_rotor_angle_separation_by_bus": {r["target_bus"]: r["max_rotor_angle_separation_deg"] for r in rows},
        "special_b16_smoke_status": next((r["measurement_extraction_status"] for r in rows if r["target_bus"] == "B16"), ""),
        "b16_old_fault_not_moved": True,
        "current_candidate_count": 42,
        "old_formal_gate": "35 / 33 / 33",
        "actual_simulink_run": True,
        "dry_run": False,
        "labels_exported": False,
        "candidate_labels_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "should_export_labels_now": False,
        "should_train_now": False,
        "recommended_next_step": (
            "run batch smoke quality review for successful buses before any label export"
            if successful
            else "diagnose batch smoke failures before any quality review or label export"
        ),
    }
    _write_json(out_dir / "batch_actual_smoke_summary.json", summary)
    _write_text(out_dir / "batch_actual_smoke_summary.md", _summary_md(summary))
    _write_csv(out_dir / "batch_actual_smoke_summary.csv", rows, SUMMARY_FIELDS)
    _write_json(out_dir / "buses_ready_for_smoke_quality_review.json", _quality_review_candidate_list(summary))
    _write_text(ROOT / "docs/ieee39_all_remaining_bus_fault_batch_actual_smoke.md", _doc_md(summary))
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=True))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--simulation-stop-time", type=float, default=0.8)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    run(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
