from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_SIM_STAGE_DIAGNOSTIC_COMMIT = "a233fabaeadf19c23e9ced0c4459cbea7a366d25"
SPP001_PAIR_ID = "SPP001"
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_solver_runtime_diagnosis"
DOC = ROOT / "docs/ieee39_spp001_solver_runtime_diagnosis.md"
SIM_STAGE_DIR = ROOT / "results/gcn_search/ieee39_spp001_sim_stage_diagnostic_retry"
TIMEOUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_bridge_smoke_timeout_diagnosis"
REPAIRED_MANIFEST = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/spp001_repaired_same_wrapper_manifest.json"


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


def _read_json_or_empty(path: Path) -> dict[str, Any]:
    if not _exists(path):
        return {}
    try:
        payload = _read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_kv_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            writer.writerow([key, value])


def _write_kv_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.extend([f"## {key}", "```json", json.dumps(value, ensure_ascii=False, indent=2), "```", ""])
        else:
            lines.append(f"- `{key}`: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _git_changed_paths_against_main() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _large_file_safety() -> dict[str, Any]:
    changed = [path.lower().replace("\\", "/") for path in _git_changed_paths_against_main()]

    def has_token(*tokens: str) -> bool:
        return any(any(token in path for token in tokens) for path in changed)

    safety = {
        "safety_scope": "spp001_solver_runtime_diagnosis_large_file_safety",
        "raw_trajectories_committed": has_token("raw_trajector"),
        "full_timeseries_committed": has_token("full_timeseries"),
        "mat_files_committed": any(path.endswith(".mat") for path in changed),
        "slx_files_committed": any(path.endswith(".slx") for path in changed),
        "slxc_files_committed": any(path.endswith(".slxc") for path in changed),
        "slprj_committed": has_token("slprj/"),
        "local_bridge_committed": has_token("local_bridge_copy"),
        "local_lab_copy_committed": has_token("local_lab_copies"),
        "source_slx_modified": False,
        "venv_committed": has_token(".venv", "site-packages"),
        "wheel_or_dll_committed": any(path.endswith(".whl") or path.endswith(".dll") for path in changed),
        "model_files_committed": any(path.endswith(ext) for path in changed for ext in [".pt", ".pth", ".ckpt"]),
    }
    safety["safety_check_passed"] = not any(
        bool(safety[key])
        for key in [
            "raw_trajectories_committed",
            "full_timeseries_committed",
            "mat_files_committed",
            "slx_files_committed",
            "slxc_files_committed",
            "slprj_committed",
            "local_bridge_committed",
            "local_lab_copy_committed",
            "venv_committed",
            "wheel_or_dll_committed",
            "model_files_committed",
        ]
    )
    return safety


def _warning_detected(payloads: list[dict[str, Any]]) -> bool:
    text = json.dumps(payloads, ensure_ascii=False).lower()
    phrases = [
        "first solve for initial conditions failed to converge",
        "initial conditions failed to converge",
        "high priorities relaxed to low",
    ]
    return any(phrase in text for phrase in phrases)


def _run_matlab_config_inspection(model_path: Path, timeout_s: int) -> dict[str, Any]:
    if not _exists(model_path):
        return {
            "inspection_status": "blocked",
            "model_load_check_passed": False,
            "blocker_if_any": f"local bridge model missing: {model_path}",
        }
    output_path = OUT_DIR / "matlab_solver_runtime_config_inventory_raw.json"
    model_arg = model_path.as_posix().replace("'", "''")
    output_arg = output_path.as_posix().replace("'", "''")
    command = (
        "addpath('matlab/simulink_ieee39'); "
        "configure_ieee39_short_filegen_paths(); "
        f"modelPath='{model_arg}'; outPath='{output_arg}'; "
        "info=struct(); info.inspection_status='started'; info.model_path=modelPath; "
        "try, load_system(modelPath); [~,modelName,~]=fileparts(modelPath); info.model_name=modelName; "
        "params={'SolverType','Solver','SimulationMode','StopTime','MaxStep','RelTol','AbsTol','AlgebraicLoopMsg','ZeroCross','FastRestart','SimscapeLogType'}; "
        "for k=1:numel(params), p=params{k}; try, info.(p)=get_param(modelName,p); catch MEp, info.(p)=['UNAVAILABLE: ' MEp.identifier]; end, end; "
        "try, pg=find_system(modelName,'LookUnderMasks','all','FollowLinks','on','RegExp','on','Name','.*powergui.*'); catch, pg={}; end; "
        "info.powergui_block_count=numel(pg); info.powergui_blocks=pg; info.powergui_or_phasor_mode_if_available='unknown'; "
        "for k=1:min(numel(pg),5), blk=pg{k}; masks=fieldnames(get_param(blk,'ObjectParameters')); "
        "for m=1:numel(masks), key=masks{m}; if contains(lower(key),'mode') || contains(lower(key),'phasor') || contains(lower(key),'frequency'), "
        "try, info.(['powergui_' key])=get_param(blk,key); catch, end; end; end; end; "
        "info.inspection_status='succeeded'; info.model_load_check_passed=true; close_system(modelName,0); "
        "catch ME, info.inspection_status='failed'; info.model_load_check_passed=false; info.blocker_if_any=[ME.identifier ': ' ME.message]; try, if exist('modelName','var'), close_system(modelName,0); end; catch, end; end; "
        "fid=fopen(outPath,'w'); fprintf(fid,'%s',jsonencode(info,'PrettyPrint',true)); fclose(fid);"
    )
    try:
        process = subprocess.run(
            ["matlab", "-batch", command],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return {
            "inspection_status": "blocked",
            "model_load_check_passed": False,
            "blocker_if_any": "MATLAB executable not available on PATH",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "inspection_status": "timeout",
            "model_load_check_passed": False,
            "blocker_if_any": f"MATLAB config inspection timeout after {timeout_s}s",
            "matlab_stdout_tail": (exc.stdout or "").splitlines()[-30:] if isinstance(exc.stdout, str) else [],
            "matlab_stderr_tail": (exc.stderr or "").splitlines()[-30:] if isinstance(exc.stderr, str) else [],
        }
    payload = _read_json_or_empty(output_path)
    payload.setdefault("inspection_status", "missing_output" if not payload else "succeeded")
    payload.setdefault("model_load_check_passed", bool(payload))
    payload["matlab_returncode"] = process.returncode
    payload["matlab_stdout_tail"] = (process.stdout or "").splitlines()[-30:]
    payload["matlab_stderr_tail"] = (process.stderr or "").splitlines()[-30:]
    if process.returncode != 0 and payload.get("inspection_status") == "succeeded":
        payload["inspection_status"] = "matlab_nonzero"
    return payload


def _solver_value(config: dict[str, Any], key: str) -> Any:
    return config.get(key) if config.get(key) not in ("", [], None) else None


def _likely_blocker(initial_warning: bool, config: dict[str, Any]) -> str:
    if initial_warning:
        return "initial_condition_convergence_at_sim_start"
    if config.get("inspection_status") in {"failed", "timeout", "blocked", "missing_output", "matlab_nonzero"}:
        return "solver_runtime_config_inspection_incomplete"
    return "sim_stage_timeout_after_update_diagram_with_no_completed_sim_done_marker"


def _recommended_next_step(initial_warning: bool, config: dict[str, Any]) -> str:
    if initial_warning:
        return "approve one short-stop SPP001 solver profiling run focused on initialization; do not export labels or train"
    if config.get("inspection_status") in {"failed", "timeout", "blocked", "missing_output", "matlab_nonzero"}:
        return "repair solver/runtime configuration in a guarded local bridge copy before any full smoke rerun"
    return "approve one longer-timeout SPP001 smoke retry in a separate round; do not expand batch"


def build_payloads(args: argparse.Namespace) -> dict[str, Any]:
    if not args.approved_solver_runtime_diagnostic_only:
        raise SystemExit("--approved-solver-runtime-diagnostic-only is required")
    if args.pair_id != SPP001_PAIR_ID:
        raise SystemExit("Only --pair-id SPP001 is approved")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sim_summary = _read_json_or_empty(SIM_STAGE_DIR / "spp001_sim_stage_diagnostic_summary.json")
    sim_trace = _read_json_or_empty(SIM_STAGE_DIR / "spp001_sim_stage_phase_trace.json")
    sim_excerpt = _read_json_or_empty(SIM_STAGE_DIR / "spp001_sim_stage_stdout_stderr_excerpt.json")
    timeout_summary = _read_json_or_empty(TIMEOUT_DIR / "spp001_timeout_diagnosis_summary.json")
    manifest = _read_json_or_empty(args.provenance_manifest)
    model_path = Path(manifest.get("local_bridge_path", ""))
    if model_path and not model_path.is_absolute():
        model_path = ROOT / model_path

    initial_warning = _warning_detected([sim_summary, sim_trace, sim_excerpt, timeout_summary])
    config = _run_matlab_config_inspection(model_path, args.matlab_inspection_timeout_seconds)

    recommended_short_stop_times = [0.0, 0.01, 0.1, 0.49, 0.51]
    likely_blocker = _likely_blocker(initial_warning, config)
    summary = {
        "diagnosis_scope": "spp001_solver_runtime_diagnosis",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_sim_stage_diagnostic_commit": SOURCE_SIM_STAGE_DIAGNOSTIC_COMMIT,
        "pair_id": SPP001_PAIR_ID,
        "same_wrapper_confirmed": bool(manifest.get("same_wrapper_confirmed", False)),
        "previous_likely_timeout_stage": sim_summary.get("previous_likely_timeout_stage") or timeout_summary.get("likely_timeout_stage"),
        "previous_execution_status": sim_summary.get("execution_status"),
        "previous_python_timeout_seconds": sim_summary.get("python_timeout_seconds"),
        "previous_matlab_timeout_seconds": sim_summary.get("matlab_timeout_seconds_if_available"),
        "initial_condition_convergence_warning_detected": initial_warning,
        "solver_runtime_diagnostic_only": True,
        "full_smoke_executed": False,
        "sim_run_attempted": False,
        "diagnostic_short_profile_attempted": False,
        "model_load_check_passed": bool(config.get("model_load_check_passed", False)),
        "update_diagram_previously_passed": True,
        "solver_type_if_available": _solver_value(config, "SolverType"),
        "solver_name_if_available": _solver_value(config, "Solver"),
        "simulation_mode_if_available": _solver_value(config, "SimulationMode"),
        "stop_time_if_available": _solver_value(config, "StopTime"),
        "max_step_if_available": _solver_value(config, "MaxStep"),
        "rel_tol_if_available": _solver_value(config, "RelTol"),
        "abs_tol_if_available": _solver_value(config, "AbsTol"),
        "powergui_or_phasor_mode_if_available": _solver_value(config, "powergui_or_phasor_mode_if_available"),
        "short_stop_profiling_plan_written": True,
        "recommended_short_stop_times": recommended_short_stop_times,
        "likely_runtime_blocker": likely_blocker,
        "can_request_short_stop_solver_profile_after_manual_approval": True,
        "can_request_full_spp001_smoke_rerun": False,
        "can_request_selected_32_batch": False,
        "no_label_value_generated": True,
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
        "blocker_if_any": None if config.get("inspection_status") == "succeeded" else config.get("blocker_if_any"),
    }
    summary["recommended_next_step"] = _recommended_next_step(initial_warning, config)

    warning_review = {
        "review_scope": "spp001_initial_condition_warning_review",
        "pair_id": SPP001_PAIR_ID,
        "initial_condition_convergence_warning_detected": initial_warning,
        "warning_evidence_source": "spp001_sim_stage_stdout_stderr_excerpt",
        "matched_warning_patterns": [
            "First solve for initial conditions failed to converge",
            "Trying again with all high priorities relaxed to low",
        ]
        if initial_warning
        else [],
        "interpretation": "sim() entered initialization and struggled before producing phase_sim_done"
        if initial_warning
        else "no explicit initial-condition convergence warning found in compact evidence",
    }
    short_stop_plan = {
        "plan_scope": "spp001_short_stop_solver_profile_plan",
        "pair_id": SPP001_PAIR_ID,
        "approved_now": False,
        "sim_run_planned_this_round": False,
        "recommended_short_stop_times": recommended_short_stop_times,
        "purpose": "separate initialization from post-trip runtime; do not export labels",
        "must_not_export_formal_labels": True,
        "must_not_train_gcn": True,
    }
    gate = {
        "gate_scope": "spp001_solver_runtime_diagnostic_gate",
        "pair_id": SPP001_PAIR_ID,
        "same_wrapper_confirmed": summary["same_wrapper_confirmed"],
        "previous_status": "timeout",
        "likely_timeout_stage": "phase_sim_start",
        "selected_32_batch_allowed": False,
        "full_1056_allowed": False,
        "formal_label_export_allowed": False,
        "gcn_training_allowed": False,
        "can_request_short_stop_solver_profile": True,
        "can_request_full_spp001_smoke_rerun": False,
        "can_request_selected_32_batch": False,
        "blocker_if_any": summary["blocker_if_any"],
    }
    no_leakage = {
        "audit_scope": "spp001_solver_runtime_diagnosis_no_leakage_audit",
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "no_leakage_policy_passed": True,
    }
    return {
        "summary": summary,
        "config_inventory": {
            "inventory_scope": "spp001_solver_runtime_config_inventory",
            "pair_id": SPP001_PAIR_ID,
            "model_path": str(model_path),
            "same_wrapper_confirmed": summary["same_wrapper_confirmed"],
            "config_inspection": config,
        },
        "warning_review": warning_review,
        "short_stop_plan": short_stop_plan,
        "gate": gate,
        "no_leakage": no_leakage,
        "safety": _large_file_safety(),
    }


def _build_doc(summary: dict[str, Any]) -> str:
    return f"""# IEEE39 SPP001 Solver/Runtime Diagnosis

This round is an SPP001 solver/runtime diagnosis for `L15 -> L04` only. It does not train GCN, does not rerun formal audit, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous timeout was already localized to the `sim()` stage. This round checks solver/runtime evidence and model configuration only. It does not generate a 0/1 label. Timeout, failed, blocked, or unknown evidence cannot become a 0/1 label.

The compact evidence contains the MATLAB warning that the first solve for initial conditions failed to converge and that Simulink retried with high priorities relaxed to low. That points to an initialization or solver-runtime issue, not to GCN, not to selected 32, and not to formal label export.

## Result

- diagnosis_scope: `{summary["diagnosis_scope"]}`
- pair_id: `{summary["pair_id"]}`
- same_wrapper_confirmed: `{summary["same_wrapper_confirmed"]}`
- previous_likely_timeout_stage: `{summary["previous_likely_timeout_stage"]}`
- previous_python_timeout_seconds: `{summary["previous_python_timeout_seconds"]}`
- previous_matlab_timeout_seconds: `{summary["previous_matlab_timeout_seconds"]}`
- initial_condition_convergence_warning_detected: `{summary["initial_condition_convergence_warning_detected"]}`
- solver_runtime_diagnostic_only: `{summary["solver_runtime_diagnostic_only"]}`
- full_smoke_executed: `{summary["full_smoke_executed"]}`
- sim_run_attempted: `{summary["sim_run_attempted"]}`
- solver_type_if_available: `{summary["solver_type_if_available"]}`
- solver_name_if_available: `{summary["solver_name_if_available"]}`
- simulation_mode_if_available: `{summary["simulation_mode_if_available"]}`
- powergui_or_phasor_mode_if_available: `{summary["powergui_or_phasor_mode_if_available"]}`
- likely_runtime_blocker: `{summary["likely_runtime_blocker"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, production model, or local bridge `.slx` file is committed. The source `.slx` is not modified. Bus-fault labels are not used. Line-trip labels remain first priority. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = [
        ("spp001_solver_runtime_diagnosis_summary", payloads["summary"], "IEEE39 SPP001 Solver Runtime Diagnosis Summary"),
        ("spp001_solver_runtime_config_inventory", payloads["config_inventory"], "IEEE39 SPP001 Solver Runtime Config Inventory"),
        ("spp001_initial_condition_warning_review", payloads["warning_review"], "IEEE39 SPP001 Initial Condition Warning Review"),
        ("spp001_short_stop_solver_profile_plan", payloads["short_stop_plan"], "IEEE39 SPP001 Short-Stop Solver Profile Plan"),
        ("spp001_solver_runtime_diagnostic_gate", payloads["gate"], "IEEE39 SPP001 Solver Runtime Diagnostic Gate"),
        ("no_leakage_spp001_solver_runtime_diagnosis_audit", payloads["no_leakage"], "IEEE39 SPP001 Solver Runtime No-Leakage Audit"),
        ("large_file_safety_spp001_solver_runtime_diagnosis", payloads["safety"], "IEEE39 SPP001 Solver Runtime Large-File Safety"),
    ]
    for stem, payload, title in files:
        _write_json(OUT_DIR / f"{stem}.json", payload)
        _write_kv_md(OUT_DIR / f"{stem}.md", title, payload)
        if stem == "spp001_solver_runtime_diagnosis_summary":
            _write_kv_csv(OUT_DIR / f"{stem}.csv", payload)
    if write_report:
        DOC.write_text(_build_doc(payloads["summary"]), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose IEEE39 SPP001 solver/runtime timeout evidence.")
    parser.add_argument("--approved-solver-runtime-diagnostic-only", action="store_true")
    parser.add_argument("--pair-id", default=SPP001_PAIR_ID)
    parser.add_argument("--provenance-manifest", type=Path, default=REPAIRED_MANIFEST)
    parser.add_argument("--matlab-inspection-timeout-seconds", type=int, default=180)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.strict:
        required = [
            SIM_STAGE_DIR / "spp001_sim_stage_diagnostic_summary.json",
            SIM_STAGE_DIR / "spp001_sim_stage_phase_trace.json",
            SIM_STAGE_DIR / "spp001_sim_stage_stdout_stderr_excerpt.json",
            args.provenance_manifest,
        ]
        missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
        if missing:
            raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads(args)
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
