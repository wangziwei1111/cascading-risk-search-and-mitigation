"""Run small IEEE39 non-line-trip fault smoke tests.

The runner executes only manifest-selected, non-manual scenarios. Each scenario
gets its own output folder and its own MATLAB process with a timeout. Results
are written as smoke candidates only; this script never updates the formal
dynamic-label gate.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_scenario_manifest.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/smoke_outputs"
SUMMARY_CSV = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_summary.csv"
SUMMARY_JSON = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_summary.json"
REPORT_JSON = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_report.json"
REPORT_MD = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_report.md"
WRAPPER_MODEL = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx"

SUMMARY_FIELDS = [
    "scenario_id",
    "fault_type",
    "target_bus_or_component",
    "fault_start_s",
    "fault_clear_s",
    "duration_s",
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
    "output_summary_path",
    "output_event_log_path",
    "note",
]


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _float_or_nan(value: Any) -> float:
    try:
        if value is None or str(value).strip() == "":
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {row["scenario_id"]: row for row in rows}


def _safe_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _validate_selected(rows: dict[str, dict[str, str]], scenario_ids: list[str]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for scenario_id in scenario_ids:
        if scenario_id not in rows:
            raise ValueError(f"Unknown scenario_id: {scenario_id}")
        row = rows[scenario_id]
        text = json.dumps(row).lower()
        if "l12" in text:
            raise ValueError(f"{scenario_id} is rejected because it contains L12.")
        if "handwired_timed_breaker" in text or "single_line_trip" in text or "timed_breaker" in text:
            raise ValueError(f"{scenario_id} is rejected because it looks like a handwired line-trip scenario.")
        if _boolish(row.get("requires_slx_modification")) or not _boolish(row.get("runnable_with_existing_scripts")):
            raise ValueError(f"{scenario_id} is manual_required or not runnable with existing scripts.")
        selected.append(row)
    return selected


def _matlab_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _write_matlab_script(row: dict[str, str], scenario_dir: Path, simulation_stop_time: float) -> Path:
    scenario_id = row["scenario_id"]
    script_path = scenario_dir / f"run_{scenario_id}_smoke.m"
    scenario_dir.mkdir(parents=True, exist_ok=True)
    matlab_dir = ROOT / "matlab/simulink_ieee39"
    wrapper = _matlab_path(WRAPPER_MODEL)
    out_dir = _matlab_path(scenario_dir)
    fault_start = _float_or_nan(row["fault_start_s"])
    fault_clear = _float_or_nan(row["fault_clear_s"])
    duration = max(0.05, fault_clear - fault_start)
    if row["fault_type"] == "three_phase_bus_fault_clear":
        selected_case = "three_phase_fault_clear"
        script = f"""
cd('{_matlab_path(matlab_dir)}');
addpath('{_matlab_path(matlab_dir)}');
run_ieee39_fault_test_suite('{wrapper}', '{out_dir}', true, ["{selected_case}"], {simulation_stop_time}, false);
"""
    elif row["fault_type"] == "relay_proxy_fault":
        script = f"""
cd('{_matlab_path(matlab_dir)}');
addpath('{_matlab_path(matlab_dir)}');
run_ieee39_fault_test_suite('{wrapper}', '{out_dir}', true, ["relay_trip_test"], {simulation_stop_time}, false);
"""
    elif row["fault_type"] == "fault_duration_sweep":
        test_case = f"{scenario_id}_fault_duration_sweep"
        script = f"""
cd('{_matlab_path(matlab_dir)}');
addpath('{_matlab_path(matlab_dir)}');
configure_ieee39_short_filegen_paths();
if ~exist('{out_dir}', "dir")
    mkdir('{out_dir}');
end
success = false;
physicalExecuted = false;
note = "";
simOut = [];
try
    load_system('{wrapper}');
    [~, modelName, ~] = fileparts('{wrapper}');
    faultBlocks = find_system(modelName, "LookUnderMasks", "all", "FollowLinks", "on", "MaskType", "Fault (Three-Phase)");
    if isempty(faultBlocks)
        error("No Fault (Three-Phase) block found in wrapper.");
    end
    faultBlock = string(faultBlocks{{1}});
    set_param(faultBlock, "enable_temporal_fault", "1");
    set_param(faultBlock, "fault_start_time", "{fault_start:.6f}");
    set_param(faultBlock, "fault_duration", "{duration:.6f}");
    simOut = sim(modelName, "StopTime", "{simulation_stop_time:.6f}");
    success = true;
    physicalExecuted = true;
    note = "duration-aware smoke run on existing Fault (Three-Phase) block";
    close_system(modelName, 0);
catch ME
    note = "simulation failed: " + string(ME.message);
    try
        [~, modelName, ~] = fileparts('{wrapper}');
        close_system(modelName, 0);
    catch
    end
end
if success
    signalSummary = extract_ieee39_signal_summary(simOut, "{test_case}", '{out_dir}');
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
    string("{test_case}"), success, physicalExecuted, false, "graphical_simulink_phasor_RMS", "existing_three_phase_fault_block", ...
    "configured", string(signalSummary.measurement_extraction_status), success && physicalExecuted && string(signalSummary.measurement_extraction_status) == "voltage_speed_angle", string(ternary(~success, note, "")), ...
    "fault_duration_sweep", {fault_start:.6f}, {fault_clear:.6f}, "", false, false, ...
    signalSummary.min_voltage_pu, signalSummary.max_voltage_pu, signalSummary.min_frequency_hz, signalSummary.max_frequency_hz, ...
    signalSummary.max_speed_deviation, signalSummary.max_rotor_angle_separation_deg, string(signalSummary.signal_source_summary), unstable, NaN, string(note), ...
    'VariableNames', {{'test_case','simulation_success','physical_fault_or_breaker_action_executed','schema_only','simulation_mode','trip_implementation','fault_configuration_status','measurement_extraction_status','training_ready_candidate','timeout_or_error_message','fault_type','fault_start_s','fault_clear_s','tripped_line','relay_operated','breaker_opened','min_voltage_pu','max_voltage_pu','min_frequency_hz','max_frequency_hz','max_speed_deviation','max_rotor_angle_separation_deg','signal_source_summary','unstable_flag','trip_time_s','note'}} ...
);
eventTable = table(string("{test_case}"), {fault_start:.6f}, "fault_duration_sweep", physicalExecuted, string(note), ...
    'VariableNames', {{'test_case','event_time_s','event_type','physical_executed','event_note'}});
writetable(summaryTable, fullfile('{out_dir}', "ieee39_fault_test_summary.csv"));
writetable(eventTable, fullfile('{out_dir}', "ieee39_event_log.csv"));

function value = ternary(condition, trueValue, falseValue)
if condition
    value = trueValue;
else
    value = falseValue;
end
end
"""
    else:
        raise ValueError(f"Unsupported runnable fault type: {row['fault_type']}")
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


def _read_first_summary_row(summary_path: Path) -> dict[str, str] | None:
    if not summary_path.exists():
        return None
    with summary_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[0] if rows else None


def _result_from_summary(row: dict[str, str], scenario: dict[str, str], scenario_dir: Path) -> dict[str, Any]:
    success = _boolish(row.get("simulation_success"))
    measurement = str(row.get("measurement_extraction_status", ""))
    signal_source = str(row.get("signal_source_summary", ""))
    smoke_ready = bool(success and measurement == "voltage_speed_angle" and "frequency=generator_speed_proxy" in signal_source)
    return {
        "scenario_id": scenario["scenario_id"],
        "fault_type": _smoke_fault_type(scenario),
        "target_bus_or_component": scenario["target_bus_or_component"],
        "fault_start_s": _float_or_nan(scenario["fault_start_s"]),
        "fault_clear_s": _float_or_nan(scenario["fault_clear_s"]),
        "duration_s": _float_or_nan(scenario["duration_s"]),
        "simulation_success": success,
        "physical_fault_or_breaker_action_executed": _boolish(row.get("physical_fault_or_breaker_action_executed")),
        "measurement_extraction_status": measurement,
        "training_ready_candidate_smoke": smoke_ready,
        "timeout_or_error_message": "" if success else str(row.get("timeout_or_error_message", "")),
        "min_voltage_pu": _float_or_nan(row.get("min_voltage_pu")),
        "max_voltage_pu": _float_or_nan(row.get("max_voltage_pu")),
        "min_frequency_hz": _float_or_nan(row.get("min_frequency_hz")),
        "max_frequency_hz": _float_or_nan(row.get("max_frequency_hz")),
        "max_speed_deviation": _float_or_nan(row.get("max_speed_deviation")),
        "max_rotor_angle_separation_deg": _float_or_nan(row.get("max_rotor_angle_separation_deg")),
        "unstable_flag": _boolish(row.get("unstable_flag")),
        "signal_source_summary": signal_source,
        "output_summary_path": _safe_rel(scenario_dir / "ieee39_fault_test_summary.csv"),
        "output_event_log_path": _safe_rel(scenario_dir / "ieee39_event_log.csv"),
        "note": _scenario_note(scenario, row.get("note", "")),
    }


def _smoke_fault_type(scenario: dict[str, str]) -> str:
    if scenario["fault_type"] == "three_phase_bus_fault_clear":
        return "three_phase_fault_clear_smoke"
    if scenario["fault_type"] == "fault_duration_sweep":
        return "fault_duration_sweep_smoke"
    if scenario["fault_type"] == "relay_proxy_fault":
        return "relay_proxy_fault_smoke"
    return scenario["fault_type"] + "_smoke"


def _scenario_note(scenario: dict[str, str], source_note: Any) -> str:
    base = str(source_note or "")
    if scenario["fault_type"] == "relay_proxy_fault":
        return (base + "; basic relay proxy, not engineering-grade protection").strip("; ")
    if scenario["fault_type"] == "fault_duration_sweep":
        return (base + "; duration sweep smoke candidate only, not suite-grade formal label").strip("; ")
    return (base + "; non-line-trip smoke candidate only, not line-trip label").strip("; ")


def _failure_result(scenario: dict[str, str], scenario_dir: Path, message: str, timed_out: bool) -> dict[str, Any]:
    return {
        "scenario_id": scenario["scenario_id"],
        "fault_type": _smoke_fault_type(scenario),
        "target_bus_or_component": scenario["target_bus_or_component"],
        "fault_start_s": _float_or_nan(scenario["fault_start_s"]),
        "fault_clear_s": _float_or_nan(scenario["fault_clear_s"]),
        "duration_s": _float_or_nan(scenario["duration_s"]),
        "simulation_success": False,
        "physical_fault_or_breaker_action_executed": False,
        "measurement_extraction_status": "simulation_timeout" if timed_out else "simulation_failed",
        "training_ready_candidate_smoke": False,
        "timeout_or_error_message": message,
        "min_voltage_pu": math.nan,
        "max_voltage_pu": math.nan,
        "min_frequency_hz": math.nan,
        "max_frequency_hz": math.nan,
        "max_speed_deviation": math.nan,
        "max_rotor_angle_separation_deg": math.nan,
        "unstable_flag": False,
        "signal_source_summary": "",
        "output_summary_path": _safe_rel(scenario_dir / "ieee39_fault_test_summary.csv"),
        "output_event_log_path": _safe_rel(scenario_dir / "ieee39_event_log.csv"),
        "note": "failed smoke candidate only; not merged into formal dynamic labels",
    }


def _write_summary(rows: list[dict[str, Any]]) -> None:
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    SUMMARY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False, allow_nan=True) + "\n", encoding="utf-8")


def _write_report(requested: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [str(row["scenario_id"]) for row in rows if row["training_ready_candidate_smoke"] is True]
    failed = [str(row["scenario_id"]) for row in rows if row["training_ready_candidate_smoke"] is not True]
    timeout = [str(row["scenario_id"]) for row in rows if row["measurement_extraction_status"] == "simulation_timeout"]
    report = {
        "scenario_ids_requested": requested,
        "scenario_ids_completed": [str(row["scenario_id"]) for row in rows],
        "scenario_ids_successful": successful,
        "scenario_ids_failed": failed,
        "scenario_ids_timeout": timeout,
        "num_successful_smoke_candidates": len(successful),
        "whether_formal_label_gate_changed": False,
        "whether_reranker_retrained": False,
        "whether_slx_modified": False,
        "whether_l12_touched": False,
        "recommended_next_step": (
            "Create a separate merge/export round for non-line-trip candidate labels, keeping them separate from handwired line-trip labels."
            if len(successful) == len(requested)
            else "Inspect failed smoke scenarios first; only successful smoke rows can be considered for a later non-line-trip label export."
        ),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# IEEE39 Non-Line-Trip Fault Smoke-Test Report",
        "",
        f"- requested: {', '.join(requested)}",
        f"- completed: {', '.join(report['scenario_ids_completed'])}",
        f"- successful smoke candidates: {', '.join(successful) if successful else 'none'}",
        f"- failed: {', '.join(failed) if failed else 'none'}",
        f"- timeout: {', '.join(timeout) if timeout else 'none'}",
        f"- formal label gate changed: {report['whether_formal_label_gate_changed']}",
        f"- reranker retrained: {report['whether_reranker_retrained']}",
        f"- `.slx` modified: {report['whether_slx_modified']}",
        f"- L12 touched: {report['whether_l12_touched']}",
        "",
        "Smoke-test success is not a formal dynamic-label merge. The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct frequency. The relay proxy is not engineering-grade protection.",
        "",
        "Recommended next step:",
        "",
        report["recommended_next_step"],
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def _write_dry_run(selected: list[dict[str, str]], output_dir: Path) -> None:
    print("Dry-run only; no MATLAB/Simulink execution.")
    for row in selected:
        print(f"- {row['scenario_id']}: {row['fault_type']} -> {output_dir / row['scenario_id']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario-manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--scenario-ids", nargs="+", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--simulation-stop-time", type=float, default=0.8)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = _read_manifest(args.scenario_manifest)
    selected = _validate_selected(manifest, args.scenario_ids)
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        _write_dry_run(selected, output_dir)
        return 0

    rows: list[dict[str, Any]] = []
    for scenario in selected:
        scenario_dir = output_dir / scenario["scenario_id"]
        scenario_dir.mkdir(parents=True, exist_ok=True)
        script_path = _write_matlab_script(scenario, scenario_dir, args.simulation_stop_time)
        stdout, timed_out, error_message = _run_matlab(script_path, args.timeout_seconds)
        (scenario_dir / "matlab_stdout.log").write_text(stdout, encoding="utf-8", errors="ignore")
        summary_row = _read_first_summary_row(scenario_dir / "ieee39_fault_test_summary.csv")
        if timed_out or error_message:
            rows.append(_failure_result(scenario, scenario_dir, error_message, timed_out))
            continue
        if summary_row is None:
            rows.append(_failure_result(scenario, scenario_dir, "MATLAB completed but no summary CSV was written", False))
            continue
        rows.append(_result_from_summary(summary_row, scenario, scenario_dir))

    _write_summary(rows)
    report = _write_report(args.scenario_ids, rows)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
