"""Prepare temp-lab bus-fault smoke only when readiness gates allow it."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs"
SUMMARY_FIELDS = [
    "scenario_id",
    "target_bus",
    "fault_start_s",
    "fault_clear_s",
    "duration_s",
    "temp_model_used",
    "source_slx_modified",
    "temporary_slx_committed",
    "simulation_success",
    "physical_fault_or_breaker_action_executed",
    "measurement_extraction_status",
    "training_ready_candidate_smoke",
    "timeout_or_error_message",
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "unstable_flag",
    "signal_source_summary",
    "note",
]


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _is_ignored_temp(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/").lower()
    return "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/" in normalized


def _write_outputs(out_dir: Path, row: dict[str, Any], report: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "ieee39_bus_fault_temp_lab_smoke_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    (out_dir / "ieee39_bus_fault_temp_lab_smoke_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=True) + "\n", encoding="utf-8"
    )
    md = [
        "# IEEE39 Bus-Fault Temp Lab Smoke Report",
        "",
        "This report is preview-only and not a final dynamic performance conclusion.",
        "",
        f"- target_bus: `{row['target_bus']}`",
        f"- smoke_executed: `{report['smoke_executed']}`",
        f"- simulation_success: `{row['simulation_success']}`",
        f"- measurement_extraction_status: `{row['measurement_extraction_status']}`",
        f"- training_ready_candidate_smoke: `{row['training_ready_candidate_smoke']}`",
        f"- safe_to_run_smoke: `{report['safe_to_run_smoke']}`",
        f"- smoke_not_run_reason: `{report.get('smoke_not_run_reason', '')}`",
        f"- recommended_next_step: `{report.get('recommended_next_step', '')}`",
        "- no labels exported",
        "- no training run",
    ]
    (out_dir / "ieee39_bus_fault_temp_lab_smoke_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _write_bus_readiness_outputs(out_dir: Path, report: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    bus_lower = str(report["target_bus"]).lower()
    json_path = out_dir / f"ieee39_{bus_lower}_temp_smoke_dry_run_readiness.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        f"# IEEE39 {report['target_bus']} Temp Smoke Dry-Run Readiness",
        "",
        "This is a dry-run readiness report only. It does not run Simulink smoke,",
        "does not modify or commit any `.slx`, does not export labels, does not",
        "train GCN, and does not retrain the reranker.",
        "",
        f"- target_bus: `{report['target_bus']}`",
        f"- dry_run: `{report['dry_run']}`",
        f"- readiness_status: `{report['readiness_status']}`",
        f"- would_run_smoke_next_round: `{report['would_run_smoke_next_round']}`",
        f"- actual_simulink_run: `{report['actual_simulink_run']}`",
        f"- selected_injection_block_path: `{report['selected_injection_block_path']}`",
        f"- selected_fault_block_path: `{report['selected_fault_block_path']}`",
        f"- fault window: `{report['fault_start_s']}` s to `{report['fault_clear_s']}` s",
        f"- formal_label_gate: `{report['formal_label_gate']}`",
        f"- v2_candidate_count: `{report['v2_candidate_count']}`",
        f"- v2_plus_b39_count: `{report.get('v2_plus_b39_count', '')}`",
        "",
        f"Boundary: {report['target_bus']} is ready for a separate next-round temporary smoke attempt,",
        f"but {report['target_bus']} is still not smoke success and is not a new candidate label.",
    ]
    (out_dir / f"ieee39_{bus_lower}_temp_smoke_dry_run_readiness.md").write_text(
        "\n".join(md) + "\n", encoding="utf-8"
    )


def _matlab_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _float_or_nan(value: Any) -> float:
    try:
        if value is None or str(value).strip() == "":
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _write_actual_matlab_script(
    out_dir: Path,
    temp_model: Path,
    fault_start_s: float,
    duration_s: float,
    simulation_stop_time: float,
) -> Path:
    script_path = out_dir / "run_BF_B39_TEMP_SMOKE.m"
    matlab_dir = ROOT / "matlab/simulink_ieee39"
    model_text = _matlab_path(temp_model)
    out_text = _matlab_path(out_dir)
    script = f"""
cd('{_matlab_path(matlab_dir)}');
addpath('{_matlab_path(matlab_dir)}');
configure_ieee39_short_filegen_paths();
if ~exist('{out_text}', "dir")
    mkdir('{out_text}');
end
success = false;
physicalExecuted = false;
note = "";
simOut = [];
try
    load_system('{model_text}');
    [~, modelName, ~] = fileparts('{model_text}');
    faultBlock = string(modelName) + "/Grid/Fault_B39_TEMP";
    set_param(faultBlock, "enable_temporal_fault", "1");
    set_param(faultBlock, "fault_start_time", "{fault_start_s:.6f}");
    set_param(faultBlock, "fault_duration", "{duration_s:.6f}");
    simOut = sim(modelName, "StopTime", "{simulation_stop_time:.6f}");
    success = true;
    physicalExecuted = true;
    note = "B39 temporary local-copy bus-fault smoke executed";
    close_system(modelName, 0);
catch ME
    note = "simulation failed: " + string(ME.message);
    try
        [~, modelName, ~] = fileparts('{model_text}');
        close_system(modelName, 0);
    catch
    end
end
if success
    signalSummary = extract_ieee39_signal_summary(simOut, "BF_B39_TEMP_SMOKE", '{out_text}');
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
summaryTable = table( ...
    string("BF_B39_TEMP_SMOKE"), string("B39"), {fault_start_s:.6f}, {fault_start_s + duration_s:.6f}, {duration_s:.6f}, ...
    success, physicalExecuted, string(signalSummary.measurement_extraction_status), ...
    success && physicalExecuted && string(signalSummary.measurement_extraction_status) == "voltage_speed_angle", string(ternary(~success, note, "")), ...
    signalSummary.min_voltage_pu, signalSummary.max_voltage_pu, signalSummary.min_frequency_hz, signalSummary.max_frequency_hz, ...
    signalSummary.max_speed_deviation, signalSummary.max_rotor_angle_separation_deg, unstable, string(signalSummary.signal_source_summary), string(note), ...
    'VariableNames', {{'scenario_id','target_bus','fault_start_s','fault_clear_s','duration_s','simulation_success','physical_fault_or_breaker_action_executed','measurement_extraction_status','training_ready_candidate_smoke','timeout_or_error_message','min_voltage_pu','max_voltage_pu','min_frequency_hz','max_frequency_hz','max_speed_deviation','max_rotor_angle_separation_deg','unstable_flag','signal_source_summary','note'}} ...
);
writetable(summaryTable, fullfile('{out_text}', "ieee39_b39_temp_smoke_matlab_summary.csv"));

function value = ternary(condition, trueValue, falseValue)
if condition
    value = trueValue;
else
    value = falseValue;
end
end
"""
    script_path.write_text(script.strip() + "\n", encoding="utf-8")
    return script_path


def _run_matlab(script_path: Path, timeout_seconds: int) -> tuple[str, bool, str]:
    command = ["matlab", "-batch", f"run('{_matlab_path(script_path)}')"]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
        return completed.stdout or "", False, "" if completed.returncode == 0 else f"MATLAB exited with code {completed.returncode}"
    except subprocess.TimeoutExpired as exc:
        return exc.stdout or "", True, f"MATLAB run timed out after {timeout_seconds} seconds"
    except FileNotFoundError:
        return "", False, "MATLAB executable not found on PATH"


def _read_matlab_summary(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else None


def _human_readiness_ready(readiness: dict[str, Any]) -> tuple[bool, str]:
    target_bus = str(readiness.get("target_bus", ""))
    if target_bus == "B39":
        required_exact = {
            "target_bus": "B39",
            "selected_injection_block_path": "Grid/Bus39",
            "selected_fault_block_path": "Grid/Fault_B39_TEMP",
            "formal_label_gate": "35 / 33 / 33",
            "v2_candidate_count": 40,
            "b26_status": "unverified",
        }
    elif target_bus == "B26":
        required_exact = {
            "target_bus": "B26",
            "selected_injection_block_path": "Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node",
            "selected_fault_block_path": "Grid/Fault_B26_TEMP",
            "formal_label_gate": "35 / 33 / 33",
            "v2_plus_b39_count": 41,
            "b39_status": "candidate_label_not_formal",
            "recommended_next_step": "run B26 temporary smoke in a separate round",
        }
    else:
        return False, f"human readiness target_bus={target_bus!r} is not supported"
    for key, expected in required_exact.items():
        if readiness.get(key) != expected:
            return False, f"human readiness {key}={readiness.get(key)!r}, expected {expected!r}"
    for key in [
        "human_verified_injection_point",
        "safe_to_run_smoke_recommendation",
        "update_diagram_success",
    ]:
        if readiness.get(key) is not True:
            return False, f"human readiness {key} must be true"
    for key in [
        "source_model_saved",
        "temporary_model_committed",
        "source_slx_modified",
        "temporary_slx_committed",
        "simulink_smoke_run",
        "smoke_success",
        "labels_exported",
        "gcn_trained",
        "reranker_retrained",
        "l12_touched",
    ]:
        if readiness.get(key) is not False:
            return False, f"human readiness {key} must be false"
    return True, ""


def run(args: argparse.Namespace) -> dict[str, Any]:
    plan = _read(args.temp_lab_plan)
    inventory = _read(args.matlab_inventory) if args.matlab_inventory else {}
    manual_summary = _read(args.manual_review_summary) if args.manual_review_summary else {}
    human_readiness = _read(args.human_readiness_json) if args.human_readiness_json else {}
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    target_bus = str(args.target_bus or plan["target_bus"])
    temp_model = str(plan["temporary_model_path"])
    reason = ""
    safe = bool(inventory.get("safe_to_run_smoke", False))
    human_ready = False
    if human_readiness:
        human_ready, reason = _human_readiness_ready(human_readiness)
        safe = human_ready
    actual_run_allowed = False
    if target_bus not in {"B39", "B26"}:
        reason = "target_bus is not allowed in this round"
        safe = False
    elif target_bus != str(plan["target_bus"]):
        reason = "target_bus does not match temp lab plan"
        safe = False
    elif human_readiness and str(human_readiness.get("target_bus")) != target_bus:
        reason = "human readiness target_bus does not match requested target_bus"
        safe = False
    elif human_readiness and manual_summary.get("recommendation") != "manual_review_supports_next_round_inventory_update":
        reason = "manual review summary does not support next-round inventory update"
        safe = False
    elif plan.get("source_slx_modified") is True or inventory.get("source_model_modified") is True:
        reason = "source_slx_modified=true is forbidden"
        safe = False
    elif not _is_ignored_temp(temp_model):
        reason = "temporary model is not under ignored local_lab_copies directory"
        safe = False
    elif not safe:
        reason = "safe_to_run_smoke=false; refusing execution"
    elif args.dry_run:
        reason = "ready_for_next_round_temp_smoke" if human_readiness else "dry-run only"
    else:
        if human_readiness and human_ready and safe and target_bus == "B39":
            actual_run_allowed = True
            reason = ""
        else:
            reason = "actual Simulink execution requires B39 human readiness; B26 is dry-run only in this round"
            safe = False

    matlab_summary: dict[str, str] | None = None
    matlab_stdout = ""
    matlab_timed_out = False
    matlab_error = ""
    if actual_run_allowed:
        temp_model_path = ROOT / temp_model if not Path(temp_model).is_absolute() else Path(temp_model)
        script_path = _write_actual_matlab_script(
            out_dir,
            temp_model_path,
            float(human_readiness.get("fault_start_s", plan["fault_start_s"])),
            float(human_readiness.get("duration_s", plan["duration_s"])),
            float(args.simulation_stop_time),
        )
        matlab_stdout, matlab_timed_out, matlab_error = _run_matlab(script_path, args.timeout_seconds)
        (out_dir / "matlab_stdout.log").write_text(matlab_stdout, encoding="utf-8", errors="ignore")
        matlab_summary = _read_matlab_summary(out_dir / "ieee39_b39_temp_smoke_matlab_summary.csv")
        if matlab_timed_out:
            reason = matlab_error
        elif matlab_error:
            reason = matlab_error
        elif matlab_summary is None:
            reason = "MATLAB completed but no B39 smoke summary CSV was written"
        else:
            reason = str(matlab_summary.get("timeout_or_error_message", ""))

    simulation_success = bool(matlab_summary and _boolish(matlab_summary.get("simulation_success")))
    measurement_status = (
        str(matlab_summary.get("measurement_extraction_status", "")) if matlab_summary else
        ("simulation_timeout" if matlab_timed_out else ("simulation_failed" if actual_run_allowed else "smoke_not_run"))
    )
    signal_source_summary = str(matlab_summary.get("signal_source_summary", "")) if matlab_summary else ""
    training_ready = bool(
        simulation_success
        and measurement_status == "voltage_speed_angle"
        and "frequency=generator_speed_proxy" in signal_source_summary
    )
    scenario_id = "BF_B39_TEMP_SMOKE" if actual_run_allowed else f"TEMP_{target_bus}"

    row = {
        "scenario_id": scenario_id,
        "target_bus": target_bus,
        "fault_start_s": float(plan["fault_start_s"]),
        "fault_clear_s": float(plan["fault_clear_s"]),
        "duration_s": float(plan["duration_s"]),
        "temp_model_used": temp_model,
        "source_slx_modified": False,
        "temporary_slx_committed": False,
        "simulation_success": simulation_success,
        "physical_fault_or_breaker_action_executed": bool(
            matlab_summary and _boolish(matlab_summary.get("physical_fault_or_breaker_action_executed"))
        ),
        "measurement_extraction_status": measurement_status,
        "training_ready_candidate_smoke": training_ready,
        "timeout_or_error_message": "" if simulation_success else reason,
        "min_voltage_pu": _float_or_nan(matlab_summary.get("min_voltage_pu")) if matlab_summary else math.nan,
        "max_voltage_pu": _float_or_nan(matlab_summary.get("max_voltage_pu")) if matlab_summary else math.nan,
        "min_frequency_hz": _float_or_nan(matlab_summary.get("min_frequency_hz")) if matlab_summary else math.nan,
        "max_frequency_hz": _float_or_nan(matlab_summary.get("max_frequency_hz")) if matlab_summary else math.nan,
        "max_speed_deviation": _float_or_nan(matlab_summary.get("max_speed_deviation")) if matlab_summary else math.nan,
        "max_rotor_angle_separation_deg": _float_or_nan(matlab_summary.get("max_rotor_angle_separation_deg")) if matlab_summary else math.nan,
        "unstable_flag": bool(matlab_summary and _boolish(matlab_summary.get("unstable_flag"))),
        "signal_source_summary": signal_source_summary,
        "note": (
            "B39 temporary smoke candidate only; no labels exported and no training run"
            if actual_run_allowed
            else "temporary lab smoke not run; no labels exported and no training run"
        ),
    }
    requested = [scenario_id]
    successful = [scenario_id] if training_ready else []
    timeout = [scenario_id] if measurement_status == "simulation_timeout" else []
    failed = [] if training_ready else [scenario_id]
    report = {
        "preview_only": True,
        "target_bus": target_bus,
        "safe_to_run_smoke": bool(safe),
        "human_readiness_used": bool(human_readiness),
        "human_readiness_ready": bool(human_ready),
        "smoke_executed": bool(actual_run_allowed),
        "simulation_success": simulation_success,
        "scenario_ids_requested": requested,
        "scenario_ids_successful": successful,
        "scenario_ids_failed": failed,
        "scenario_ids_timeout": timeout,
        "smoke_not_run_reason": reason,
        "whether_source_slx_modified": False,
        "whether_temporary_slx_committed": False,
        "whether_formal_label_gate_changed": False,
        "whether_v2_candidate_count_changed": False,
        "whether_labels_exported": False,
        "whether_gcn_trained": False,
        "whether_reranker_retrained": False,
        "whether_l12_touched": False,
        "source_slx_modified": False,
        "temporary_slx_committed": False,
        "formal_label_gate_changed": False,
        "v2_candidate_count_changed": False,
        "reranker_retrained": False,
        "gcn_trained": False,
        "labels_exported": False,
        "l12_touched": False,
        "recommended_next_step": (
            "review B39 smoke output, then export B39 bus-fault candidate label in separate round"
            if training_ready
            else "inspect temporary B39 injection / MATLAB error"
            if actual_run_allowed
            else f"run actual {target_bus} temporary smoke in a separate round"
        ),
        "summary_csv": _rel(out_dir / "ieee39_bus_fault_temp_lab_smoke_summary.csv"),
    }
    if not (human_readiness and args.dry_run):
        _write_outputs(out_dir, row, report)
    if human_readiness and args.dry_run:
        readiness_report = {
            "target_bus": target_bus,
            "dry_run": bool(args.dry_run),
            "would_run_smoke_next_round": bool(args.dry_run and human_ready and safe),
            "actual_simulink_run": False,
            "source_slx_modified": False,
            "temporary_slx_committed": False,
            "labels_exported": False,
            "gcn_trained": False,
            "reranker_retrained": False,
            "formal_label_gate": human_readiness.get("formal_label_gate", "35 / 33 / 33"),
            "v2_candidate_count": human_readiness.get("v2_candidate_count", 40),
            "v2_plus_b39_count": human_readiness.get("v2_plus_b39_count", human_readiness.get("v2_candidate_count", 40)),
            "b39_status": human_readiness.get("b39_status", ""),
            "selected_fault_block_path": human_readiness.get("selected_fault_block_path", ""),
            "selected_injection_block_path": human_readiness.get("selected_injection_block_path", ""),
            "fault_start_s": human_readiness.get("fault_start_s"),
            "fault_clear_s": human_readiness.get("fault_clear_s"),
            "duration_s": human_readiness.get("duration_s"),
            "readiness_status": "ready_for_next_round_temp_smoke"
            if args.dry_run and human_ready and safe
            else "not_ready_for_next_round_temp_smoke",
            "recommended_next_step": f"run actual {target_bus} temporary smoke in a separate round"
            if args.dry_run and human_ready and safe
            else "fix readiness inputs before smoke",
            "manual_review_recommendation": manual_summary.get("recommendation", ""),
            "simulink_smoke_run": False,
            "smoke_success": False,
            "source_model_saved": False,
            "temporary_model_committed": False,
            "source_model_path": plan.get("source_model_path", ""),
            "temporary_model_path": temp_model,
            "note": "dry-run readiness only; no Simulink execution in this round",
        }
        _write_bus_readiness_outputs(out_dir, readiness_report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-lab-plan", type=Path, required=True)
    parser.add_argument("--matlab-inventory", type=Path)
    parser.add_argument("--manual-review-summary", type=Path)
    parser.add_argument("--human-readiness-json", type=Path)
    parser.add_argument("--target-bus", choices=["B39", "B26"])
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--simulation-stop-time", type=float, default=0.8)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    run(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
