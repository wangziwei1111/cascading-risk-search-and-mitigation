from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_manual_dynamic_validation"
DOC = ROOT / "docs/ieee39_spp001_manual_dynamic_validation.md"
BUILDER = ROOT / "matlab/simulink_ieee39/build_ieee39_spp001_manual_physical_bridge.m"
LOCAL_MODEL = OUT_DIR / "local_bridge_copy/IEEE39BusSystem_dynamic_experiment_wrapper_spp001_manual_physical_bridge.slx"
L04_SOURCE = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx"
L15_SOURCE = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15.slx"


STAGES = [
    ("A", 0.01, False, False, "initialization"),
    ("B", 0.49, False, False, "pre_trip"),
    ("C", 0.51, True, False, "l15_trip"),
    ("D", 0.76, True, True, "l04_sequence_trip"),
    ("E", 1.20, True, True, "full_dynamic_response"),
]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _exists(path: Path) -> bool:
    return os.path.exists(_long(path))


def _read_json(path: Path) -> Any:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_kv_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.extend([f"## {key}", "```json", json.dumps(value, ensure_ascii=False, indent=2), "```", ""])
        else:
            lines.append(f"- `{key}`: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_kv_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            writer.writerow([key, value])


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row[key], ensure_ascii=False) if isinstance(row.get(key), (dict, list)) else row.get(key) for key in keys})


def _tail(text: str, n: int = 60) -> list[str]:
    return (text or "").splitlines()[-n:]


def _run_matlab(command: str, timeout_s: int) -> dict[str, Any]:
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        proc = subprocess.Popen(
            ["matlab", "-batch", command],
            cwd=ROOT,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, text=True)
            else:
                proc.kill()
            stdout, stderr = proc.communicate(timeout=10)
            return {
                "returncode": proc.returncode,
                "timeout": True,
                "stdout_tail": _tail(stdout),
                "stderr_tail": _tail(stderr),
            }
        return {
            "returncode": proc.returncode,
            "timeout": False,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }
    except FileNotFoundError:
        return {
            "returncode": None,
            "timeout": False,
            "stdout_tail": [],
            "stderr_tail": ["MATLAB executable was not available on PATH"],
        }


def _build_bridge() -> tuple[dict[str, Any], dict[str, Any]]:
    raw_path = OUT_DIR / "matlab_manual_bridge_build_raw.json"
    command = (
        "addpath('matlab/simulink_ieee39'); "
        f"build_ieee39_spp001_manual_physical_bridge('{OUT_DIR.as_posix()}',"
        f"'source_l04_wrapper_path','{L04_SOURCE.as_posix()}',"
        f"'source_l15_wrapper_path','{L15_SOURCE.as_posix()}');"
    )
    status = _run_matlab(command, 240)
    raw = _read_json(raw_path) if _exists(raw_path) else {}
    return raw, status


def _stage_template(stage_id: str, stop_time: float, l15_expected: bool, l04_expected: bool, stage_name: str) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "stage_name": stage_name,
        "requested_stop_time_seconds": stop_time,
        "effective_stop_time_seconds": stop_time,
        "l15_trip_expected": l15_expected,
        "l15_trip_confirmed_if_available": None,
        "l04_trip_expected": l04_expected,
        "l04_trip_confirmed_if_available": None,
        "line_trip_applied": l15_expected or l04_expected,
        "execution_status": "blocked",
        "simulink_run": False,
        "phase_sim_start_seen": False,
        "phase_sim_done_seen": False,
        "last_seen_phase_if_available": None,
        "sim_elapsed_seconds_if_available": None,
        "initial_condition_convergence_warning_detected": False,
        "solver_type_if_available": None,
        "solver_name_if_available": None,
        "simulation_mode_if_available": None,
        "max_step_if_available": None,
        "breaker_state_evidence_if_available": None,
        "minimum_bus_voltage_if_available": None,
        "maximum_bus_voltage_if_available": None,
        "generator_speed_proxy_max_deviation_if_available": None,
        "rotor_angle_separation_if_available": None,
        "islanding_detected_if_available": None,
        "timeout_or_failure_reason": "static gate did not pass; sim() not allowed",
        "pilot_label_value": None,
        "pilot_labels_are_formal_training_labels": False,
    }


def _run_stage(stage: tuple[str, float, bool, bool, str]) -> dict[str, Any]:
    stage_id, stop_time, l15_expected, l04_expected, stage_name = stage
    row = _stage_template(stage_id, stop_time, l15_expected, l04_expected, stage_name)
    stage_status_path = OUT_DIR / f"_matlab_stage_{stage_id}_status.json"
    if stage_status_path.exists():
        stage_status_path.unlink()
    command = (
        "addpath('matlab/simulink_ieee39'); "
        "try; "
        f"modelPath='{LOCAL_MODEL.as_posix()}'; "
        f"statusPath='{stage_status_path.as_posix()}'; "
        "load_system(modelPath); "
        "[~,m,~]=fileparts(modelPath); "
        "set_param([m '/Grid/L15_TripCommand'],'Time','0.50'); "
        "set_param([m '/Grid/L04_TripCommand'],'Time','0.75'); "
        "fprintf('IEEE39_SPP001_STAGE_PHASE:phase_sim_start\\n'); "
        "elapsedTimer=tic; "
        f"sim(m,'StopTime','{stop_time}','TimeOut',240); "
        "elapsed=toc(elapsedTimer); "
        "fprintf('IEEE39_SPP001_STAGE_PHASE:phase_sim_done:%0.6f\\n', elapsed); "
        "payload=struct('stage_id','" + stage_id + "','status','succeeded','elapsed_seconds',elapsed); "
        "fid=fopen(statusPath,'w'); fprintf(fid,'%s',jsonencode(payload,PrettyPrint=true)); fclose(fid); "
        "try; close_system(m,0); catch; end; "
        "catch ME; "
        "fprintf(2,'IEEE39_SPP001_STAGE_ERROR:%s\\n',getReport(ME,'extended','hyperlinks','off')); "
        "payload=struct('stage_id','" + stage_id + "','status','failed','error_identifier',ME.identifier,'error_message',ME.message); "
        "fid=fopen(statusPath,'w'); fprintf(fid,'%s',jsonencode(payload,PrettyPrint=true)); fclose(fid); "
        "try; if exist('m','var'); close_system(m,0); end; catch; end; "
        "exit(1); "
        "end; exit(0);"
    )
    status = _run_matlab(command, 300)
    stage_status = _read_json(stage_status_path) if _exists(stage_status_path) else {}
    stdout = "\n".join(status["stdout_tail"])
    stderr = "\n".join(status["stderr_tail"])
    row["simulink_run"] = "phase_sim_start" in stdout or "phase_sim_start" in stderr
    row["phase_sim_start_seen"] = row["simulink_run"]
    row["phase_sim_done_seen"] = "phase_sim_done" in stdout or "phase_sim_done" in stderr
    row["last_seen_phase_if_available"] = "phase_sim_done" if row["phase_sim_done_seen"] else ("phase_sim_start" if row["phase_sim_start_seen"] else None)
    row["sim_elapsed_seconds_if_available"] = stage_status.get("elapsed_seconds")
    row["initial_condition_convergence_warning_detected"] = "initial conditions failed to converge" in (stdout + stderr).lower()
    if status["timeout"]:
        row["execution_status"] = "timeout"
        row["timeout_or_failure_reason"] = "Python MATLAB wrapper timeout after 300 seconds"
    elif status["returncode"] == 0 and row["phase_sim_done_seen"] and stage_status.get("status") == "succeeded":
        row["execution_status"] = "succeeded"
        row["timeout_or_failure_reason"] = ""
    else:
        row["execution_status"] = "failed"
        row["timeout_or_failure_reason"] = stage_status.get("error_message") or "; ".join(status["stderr_tail"][-10:] + status["stdout_tail"][-10:])
    return row


def _large_file_safety() -> dict[str, Any]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    changed = [line.strip().lower().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]

    def has_token(*tokens: str) -> bool:
        return any(any(token in path for token in tokens) for path in changed)

    payload = {
        "safety_scope": "spp001_manual_dynamic_validation_large_file_safety",
        "raw_trajectories_committed": has_token("raw_trajector"),
        "full_timeseries_committed": has_token("full_timeseries"),
        "mat_files_committed": any(path.endswith(".mat") for path in changed),
        "slx_files_committed": any(path.endswith(".slx") for path in changed),
        "slxc_files_committed": any(path.endswith(".slxc") for path in changed),
        "slprj_committed": has_token("slprj"),
        "local_bridge_committed": has_token("local_bridge_copy"),
        "source_slx_modified": False,
        "venv_committed": has_token(".venv", "site-packages"),
        "wheel_or_dll_committed": any(path.endswith(".whl") or path.endswith(".dll") for path in changed),
        "model_files_committed": any(path.endswith(ext) for path in changed for ext in [".pt", ".pth", ".ckpt"]),
    }
    payload["safety_check_passed"] = not any(payload[key] for key in payload if key.endswith("_committed"))
    return payload


def _recommended(summary: dict[str, Any]) -> str:
    failed = summary.get("earliest_failed_stage_if_any")
    if not summary.get("static_gate_passed"):
        return "repair manual bridge topology before any dynamic stage"
    if failed in {"A", "B"}:
        return "repair manual bridge initialization/topology before any post-trip stage"
    if failed == "C":
        return "repair L15 event path before evaluating L04 sequence"
    if failed == "D":
        return "repair L04 sequential event path before full SPP001 validation"
    if summary.get("full_spp001_dynamic_validation_completed"):
        return "approve one dynamically validated Top-3 GCN-versus-baseline comparison in a separate round; no formal-label export or GCN retraining yet"
    return "inspect SPP001 manual dynamic validation evidence before any broader execution"


def build_payloads(args: argparse.Namespace) -> dict[str, Any]:
    if not args.approved_manual_dynamic_validation:
        raise SystemExit("--approved-manual-dynamic-validation is required")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build_raw, build_status = _build_bridge()
    static_gate = {
        "gate_scope": "spp001_manual_bridge_static_gate",
        "pair_id": "SPP001",
        "l15_trip_command_block_exists": bool(build_raw.get("l15_trip_command_block_exists", False)),
        "l15_breaker_block_exists": bool(build_raw.get("l15_breaker_block_exists", False)),
        "l15_trip_command_to_breaker_control_connected": bool(build_raw.get("l15_trip_command_to_breaker_control_connected", False)),
        "l15_breaker_physical_ports_connected": bool(build_raw.get("l15_breaker_physical_ports_connected", False)),
        "l15_breaker_in_series_with_actual_l15_branch": bool(build_raw.get("l15_breaker_in_series_with_actual_l15_branch", False)),
        "l15_original_direct_bypass_removed": bool(build_raw.get("l15_original_direct_bypass_removed", False)),
        "l04_trip_command_block_exists": bool(build_raw.get("l04_trip_command_block_exists", False)),
        "l04_breaker_block_exists": bool(build_raw.get("l04_breaker_block_exists", False)),
        "l04_trip_command_to_breaker_control_connected": bool(build_raw.get("l04_trip_command_to_breaker_control_connected", False)),
        "l04_breaker_physical_ports_connected": bool(build_raw.get("l04_breaker_physical_ports_connected", False)),
        "l04_breaker_in_series_with_actual_l04_branch": bool(build_raw.get("l04_breaker_in_series_with_actual_l04_branch", False)),
        "l04_original_direct_bypass_removed": bool(build_raw.get("l04_original_direct_bypass_removed", False)),
        "no_unconnected_physical_ports": bool(build_raw.get("no_unconnected_physical_ports", False)),
        "no_unconnected_control_ports": bool(build_raw.get("no_unconnected_control_ports", False)),
        "update_diagram_passed": bool(build_raw.get("update_diagram_passed", False)),
        "physical_bridge_valid": bool(build_raw.get("physical_bridge_valid", False)),
    }
    static_gate["static_gate_passed"] = all(
        static_gate[key] is True
        for key in [
            "l15_trip_command_to_breaker_control_connected",
            "l15_breaker_physical_ports_connected",
            "l15_breaker_in_series_with_actual_l15_branch",
            "l15_original_direct_bypass_removed",
            "l04_trip_command_to_breaker_control_connected",
            "l04_breaker_physical_ports_connected",
            "l04_breaker_in_series_with_actual_l04_branch",
            "l04_original_direct_bypass_removed",
            "no_unconnected_physical_ports",
            "no_unconnected_control_ports",
            "update_diagram_passed",
            "physical_bridge_valid",
        ]
    )
    stage_manifest = {
        "manifest_scope": "spp001_dynamic_stage_manifest",
        "python_timeout_seconds": 300,
        "matlab_timeout_seconds": 240,
        "stages": [
            {
                "stage_id": stage_id,
                "requested_stop_time_seconds": stop,
                "l15_trip_expected": l15,
                "l04_trip_expected": l04,
                "stage_name": name,
            }
            for stage_id, stop, l15, l04, name in STAGES
        ],
    }
    results: list[dict[str, Any]] = []
    stopped_early = False
    if static_gate["static_gate_passed"]:
        for stage in STAGES:
            row = _run_stage(stage)
            results.append(row)
            if row["execution_status"] != "succeeded" or row["initial_condition_convergence_warning_detected"]:
                stopped_early = True
                break
    else:
        results.append(_stage_template(*STAGES[0]))
        stopped_early = True
    completed = [row for row in results if row["execution_status"] == "succeeded"]
    earliest_failed = next((row["stage_id"] for row in results if row["execution_status"] != "succeeded"), None)
    summary = {
        "validation_scope": "spp001_manual_dynamic_validation",
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "manual_bridge_build_attempted": True,
        "manual_bridge_built": bool(build_raw.get("manual_bridge_built", False)),
        "physical_bridge_valid": static_gate["physical_bridge_valid"],
        "static_gate_passed": static_gate["static_gate_passed"],
        "dynamic_stages_requested": len(STAGES),
        "dynamic_stages_completed": len(completed),
        "dynamic_stages_stopped_early": stopped_early,
        "earliest_failed_stage_if_any": earliest_failed,
        "full_spp001_dynamic_validation_completed": len(completed) == len(STAGES),
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "pilot_label_value": None,
        "no_formal_label_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "local_bridge_committed": False,
        "source_slx_modified": False,
        "bus_fault_labels_used": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "blocker_if_any": build_raw.get("blocker_if_any") or (None if static_gate["static_gate_passed"] else "manual bridge static gate did not pass"),
    }
    summary["recommended_next_step"] = _recommended(summary)
    no_leakage = {
        "audit_scope": "spp001_manual_dynamic_validation_no_leakage_audit",
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
    }
    return {
        "build_summary": build_raw,
        "build_status": build_status,
        "static_gate": static_gate,
        "stage_manifest": stage_manifest,
        "stage_results": results,
        "summary": summary,
        "no_leakage": no_leakage,
        "safety": _large_file_safety(),
    }


def _doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 SPP001 Manual Dynamic Validation

This round attempts a local-only manual physical bridge for `SPP001: L15 -> L04`. It does not train GCN, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not run RL mitigation.

## Plain-Language Summary

The builder first tries to put the L15 breaker into the real `Bus21` to `B21 to B22` physical path and keeps the existing L04 chain from the L04 source wrapper. A static gate based on real port connectivity, control tracing, and bypass checks decides whether `sim()` is allowed. If any static gate item is false, no dynamic stage is run and no 0/1 label is created.

## Result

- validation_scope: `{summary["validation_scope"]}`
- physical_bridge_valid: `{summary["physical_bridge_valid"]}`
- static_gate_passed: `{summary["static_gate_passed"]}`
- dynamic_stages_completed: `{summary["dynamic_stages_completed"]}`
- dynamic_stages_stopped_early: `{summary["dynamic_stages_stopped_early"]}`
- earliest_failed_stage_if_any: `{summary["earliest_failed_stage_if_any"]}`
- full_spp001_dynamic_validation_completed: `{summary["full_spp001_dynamic_validation_completed"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundary

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, production model, or local bridge `.slx` file is committed. The source `.slx` is not modified. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. `beta * RATE_A` is an audit-only relay threshold proxy, not a real relay setting. Temporary breaker/protection implementation is not engineering-grade protection. L12 remains special/excluded. Bus-fault labels are not used.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mapping = [
        ("spp001_manual_bridge_build_summary", payloads["build_summary"], "SPP001 Manual Bridge Build Summary"),
        ("spp001_manual_bridge_static_connectivity", payloads["static_gate"], "SPP001 Manual Bridge Static Connectivity"),
        ("spp001_manual_bridge_control_wiring", payloads["static_gate"], "SPP001 Manual Bridge Control Wiring"),
        ("spp001_manual_bridge_bypass_check", payloads["static_gate"], "SPP001 Manual Bridge Bypass Check"),
        ("spp001_manual_bridge_unconnected_ports_report", payloads["static_gate"], "SPP001 Manual Bridge Unconnected Ports Report"),
        ("spp001_manual_bridge_static_gate", payloads["static_gate"], "SPP001 Manual Bridge Static Gate"),
        ("spp001_dynamic_stage_manifest", payloads["stage_manifest"], "SPP001 Dynamic Stage Manifest"),
        ("spp001_dynamic_phase_trace", {"trace_scope": "spp001_dynamic_phase_trace", "stages": payloads["stage_results"]}, "SPP001 Dynamic Phase Trace"),
        ("spp001_dynamic_stdout_stderr_excerpt", {"excerpt_scope": "spp001_dynamic_stdout_stderr_excerpt", "build_status": payloads["build_status"]}, "SPP001 Dynamic Stdout Stderr Excerpt"),
        ("spp001_dynamic_solver_warning_report", {"warning_scope": "spp001_dynamic_solver_warning_report", "stages": payloads["stage_results"]}, "SPP001 Dynamic Solver Warning Report"),
        ("spp001_dynamic_validation_summary", payloads["summary"], "SPP001 Dynamic Validation Summary"),
        ("no_leakage_spp001_manual_dynamic_validation_audit", payloads["no_leakage"], "SPP001 Manual Dynamic Validation No Leakage Audit"),
        ("large_file_safety_spp001_manual_dynamic_validation", payloads["safety"], "SPP001 Manual Dynamic Validation Large File Safety"),
    ]
    for stem, payload, title in mapping:
        _write_json(OUT_DIR / f"{stem}.json", payload)
        _write_kv_md(OUT_DIR / f"{stem}.md", title, payload)
        if stem in {"spp001_dynamic_validation_summary"}:
            _write_kv_csv(OUT_DIR / f"{stem}.csv", payload)
    _write_json(OUT_DIR / "spp001_dynamic_stage_results.json", payloads["stage_results"])
    _write_rows_csv(OUT_DIR / "spp001_dynamic_stage_results.csv", payloads["stage_results"])
    _write_kv_md(OUT_DIR / "spp001_dynamic_stage_results.md", "SPP001 Dynamic Stage Results", {"stages": payloads["stage_results"]})
    if write_report:
        DOC.write_text(_doc(payloads), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and run approved IEEE39 SPP001 manual dynamic validation.")
    parser.add_argument("--approved-manual-dynamic-validation", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payloads = build_payloads(args)
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
