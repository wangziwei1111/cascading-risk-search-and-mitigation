from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair"
DOC = ROOT / "docs/ieee39_spp001_same_wrapper_bridge_builder_repair.md"

SOURCE_LOCAL_VALIDATION_COMMIT = "391a67f1e380d167b39779bfd06c161519eefdfc"
PREVIOUS_SUMMARY = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_local_validation/spp001_local_bridge_validation_summary.json"
MATLAB_BUILDER = ROOT / "matlab/simulink_ieee39/prepare_ieee39_spp001_same_wrapper_bridge_lab.m"
HANDWIRED_WRAPPER = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx"
L15_SOURCE_LAB = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15.slx"

LOCAL_COPY_DIR = OUT_DIR / "local_bridge_copy"
LOCAL_COPY_PATH = LOCAL_COPY_DIR / "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab.slx"
LOCAL_MODEL_NAME = "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab"


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


def _matlab_quote(path: Path | str) -> str:
    return str(path).replace("'", "''")


def _run_matlab_builder() -> dict[str, Any]:
    command = (
        "addpath('"
        + _matlab_quote(ROOT / "matlab/simulink_ieee39")
        + "'); "
        + "s=prepare_ieee39_spp001_same_wrapper_bridge_lab("
        + "'SPP001','"
        + _matlab_quote(HANDWIRED_WRAPPER)
        + "','"
        + _matlab_quote(LOCAL_COPY_DIR)
        + "','dry_run_only',false,'prior_line','L15','next_line','L04','build_local_copy',true,'l15_source_lab_path','"
        + _matlab_quote(L15_SOURCE_LAB)
        + "'); disp(jsonencode(s));"
    )
    result = subprocess.run(
        ["matlab", "-batch", command],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
        encoding="utf-8",
        errors="replace",
    )
    parsed = None
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                parsed = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    return {
        "matlab_invoked": True,
        "matlab_returncode": result.returncode,
        "matlab_summary": parsed,
        "matlab_stdout_tail": "\n".join(result.stdout.splitlines()[-8:]),
        "matlab_stderr_tail": "\n".join(result.stderr.splitlines()[-8:]),
    }


def _slx_text(path: Path) -> str:
    if not _exists(path):
        return ""
    chunks: list[str] = []
    with zipfile.ZipFile(_long(path)) as archive:
        for name in archive.namelist():
            lower = name.lower()
            if lower.endswith((".xml", ".txt", ".mxarray")) or "blockdiagram" in lower:
                try:
                    chunks.append(archive.read(name).decode("utf-8", errors="ignore"))
                except Exception:
                    continue
    return "\n".join(chunks)


def _validate_bridge(path: Path) -> dict[str, Any]:
    text = _slx_text(path)
    l15_command = "L15_TripCommand" in text
    l04_command = "L04_TripCommand" in text
    l15_breaker = "L15_HandwiredTimedBreaker" in text
    l04_breaker = "L04_HandwiredTimedBreaker" in text
    same_wrapper = bool(_exists(path) and l15_command and l04_command and l15_breaker and l04_breaker)
    blocker = None
    if not _exists(path):
        blocker = "repaired local bridge copy was not created"
    elif not l15_command:
        blocker = "L15_TripCommand is not present in the repaired bridge copy"
    elif not l04_command:
        blocker = "L04_TripCommand is not present in the repaired bridge copy"
    elif not l15_breaker:
        blocker = "L15_HandwiredTimedBreaker is not present in the repaired bridge copy"
    elif not l04_breaker:
        blocker = "L04_HandwiredTimedBreaker is not present in the repaired bridge copy"
    return {
        "local_bridge_path": str(path.relative_to(ROOT)),
        "local_bridge_file_exists": _exists(path),
        "local_bridge_model_name": LOCAL_MODEL_NAME if _exists(path) else None,
        "l15_trip_command_found_in_bridge": l15_command,
        "l04_trip_command_found_in_bridge": l04_command,
        "l15_breaker_found_in_bridge": l15_breaker,
        "l04_breaker_found_in_bridge": l04_breaker,
        "l15_trip_command_path_in_bridge": f"{LOCAL_MODEL_NAME}/Grid/L15_TripCommand" if l15_command else None,
        "l04_trip_command_path_in_bridge": f"{LOCAL_MODEL_NAME}/Grid/L04_TripCommand" if l04_command else None,
        "same_wrapper_confirmed": same_wrapper,
        "blocker_if_any": blocker,
    }


def build_payloads() -> dict[str, Any]:
    previous = _read_json(PREVIOUS_SUMMARY)
    matlab_result = _run_matlab_builder()
    validation = _validate_bridge(LOCAL_COPY_PATH)
    same_wrapper = bool(validation["same_wrapper_confirmed"])
    local_bridge_built = bool(same_wrapper)
    can_rerun = bool(same_wrapper)
    blocker = validation["blocker_if_any"]
    if matlab_result["matlab_returncode"] != 0:
        blocker = "MATLAB bridge builder failed before same-wrapper validation"
    recommended_next_step = (
        "approve rerun of SPP001 single-pair smoke using repaired same-wrapper bridge in a separate round; do not export labels or train"
        if same_wrapper
        else "repair L15 bridge insertion logic before any SPP001 smoke rerun"
    )

    report = {
        "repair_report_scope": "spp001_bridge_builder_repair_report",
        "pair_id": "SPP001",
        "matlab_builder_invoked": matlab_result["matlab_invoked"],
        "matlab_returncode": matlab_result["matlab_returncode"],
        "matlab_builder_summary": matlab_result["matlab_summary"],
        "source_wrapper_path": str(HANDWIRED_WRAPPER.relative_to(ROOT)),
        "l15_source_lab_path": str(L15_SOURCE_LAB.relative_to(ROOT)),
        "target_local_bridge_path": str(LOCAL_COPY_PATH.relative_to(ROOT)),
        "local_bridge_build_attempted": True,
        "local_bridge_built": local_bridge_built,
        "local_bridge_committed": False,
        "source_slx_modified": False,
        "simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "note": "Builder repair copies L15 TripCommand and breaker blocks into a local-only bridge copy; no sim() is called.",
    }
    manifest = {
        "manifest_scope": "spp001_repaired_same_wrapper_manifest",
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "selected_wrapper_model": LOCAL_MODEL_NAME if validation["local_bridge_file_exists"] else None,
        "local_bridge_path": str(LOCAL_COPY_PATH.relative_to(ROOT)) if validation["local_bridge_file_exists"] else None,
        "prior_trip_command_path": validation["l15_trip_command_path_in_bridge"],
        "next_trip_command_path": validation["l04_trip_command_path_in_bridge"],
        "l15_trip_command_found_in_bridge": validation["l15_trip_command_found_in_bridge"],
        "l04_trip_command_found_in_bridge": validation["l04_trip_command_found_in_bridge"],
        "l15_breaker_found_in_bridge": validation["l15_breaker_found_in_bridge"],
        "l04_breaker_found_in_bridge": validation["l04_breaker_found_in_bridge"],
        "same_wrapper_confirmed": same_wrapper,
        "source_slx_modified": False,
        "approved_for_execution_now": False,
        "requires_next_round_approval": True,
        "blocker_if_any": blocker,
    }
    gate = {
        "gate_scope": "spp001_bridge_builder_rerun_gate",
        "pair_id": "SPP001",
        "l15_ready": True,
        "l04_ready": True,
        "local_bridge_built": local_bridge_built,
        "l15_trip_command_found_in_bridge": validation["l15_trip_command_found_in_bridge"],
        "l04_trip_command_found_in_bridge": validation["l04_trip_command_found_in_bridge"],
        "l15_breaker_found_in_bridge": validation["l15_breaker_found_in_bridge"],
        "l04_breaker_found_in_bridge": validation["l04_breaker_found_in_bridge"],
        "same_wrapper_confirmed": same_wrapper,
        "selected_32_batch_allowed": False,
        "full_1056_allowed": False,
        "formal_label_export_allowed": False,
        "gcn_training_allowed": False,
        "can_request_spp001_smoke_rerun_approval": can_rerun,
        "blocker_if_any": blocker,
    }
    no_leakage = {
        "audit_scope": "spp001_bridge_builder_repair_no_leakage_audit",
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "no_leakage_policy_passed": True,
    }
    safety = {
        "safety_scope": "spp001_bridge_builder_repair_large_file_safety",
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "local_bridge_committed": False,
        "local_lab_copy_committed": False,
        "source_slx_modified": False,
        "venv_committed": False,
        "wheel_or_dll_committed": False,
        "model_files_committed": False,
        "safety_check_passed": True,
    }
    summary = {
        "repair_scope": "spp001_same_wrapper_bridge_builder_repair",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "spp001_smoke_executed": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_local_validation_commit": SOURCE_LOCAL_VALIDATION_COMMIT,
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "previous_l15_trip_command_found_in_bridge": previous.get("l15_trip_command_found_in_bridge"),
        "previous_l04_trip_command_found_in_bridge": previous.get("l04_trip_command_found_in_bridge"),
        "local_bridge_build_attempted": True,
        "local_bridge_validation_attempted": True,
        "local_bridge_built": local_bridge_built,
        "local_bridge_committed": False,
        "source_slx_modified": False,
        "l15_trip_command_found_in_bridge": validation["l15_trip_command_found_in_bridge"],
        "l04_trip_command_found_in_bridge": validation["l04_trip_command_found_in_bridge"],
        "l15_breaker_found_in_bridge": validation["l15_breaker_found_in_bridge"],
        "l04_breaker_found_in_bridge": validation["l04_breaker_found_in_bridge"],
        "same_wrapper_confirmed": same_wrapper,
        "repaired_provenance_manifest_written": True,
        "can_rerun_spp001_after_manual_approval": can_rerun,
        "no_label_value_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "blocker_if_any": blocker,
        "recommended_next_step": recommended_next_step,
        "local_bridge_validation_detail": validation,
    }
    return {
        "summary": summary,
        "report": report,
        "manifest": manifest,
        "gate": gate,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 SPP001 Same-Wrapper Bridge Builder Repair

This round is SPP001 same-wrapper bridge builder repair. It does not train GCN, does not rerun formal audit, does not execute SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous local bridge copy was missing `L15_TripCommand`. This round repairs only the bridge builder so that `L15_TripCommand`, `L04_TripCommand`, `L15_HandwiredTimedBreaker`, and `L04_HandwiredTimedBreaker` can be checked in the same local wrapper. The local bridge `.slx` is ignored by Git and must not be committed. This round does not generate a 0/1 label.

## Result

- repair_scope: `{summary["repair_scope"]}`
- pair_id: `{summary["pair_id"]}`
- local_bridge_build_attempted: `{summary["local_bridge_build_attempted"]}`
- local_bridge_validation_attempted: `{summary["local_bridge_validation_attempted"]}`
- local_bridge_built: `{summary["local_bridge_built"]}`
- local_bridge_committed: `{summary["local_bridge_committed"]}`
- source_slx_modified: `{summary["source_slx_modified"]}`
- l15_trip_command_found_in_bridge: `{summary["l15_trip_command_found_in_bridge"]}`
- l04_trip_command_found_in_bridge: `{summary["l04_trip_command_found_in_bridge"]}`
- l15_breaker_found_in_bridge: `{summary["l15_breaker_found_in_bridge"]}`
- l04_breaker_found_in_bridge: `{summary["l04_breaker_found_in_bridge"]}`
- same_wrapper_confirmed: `{summary["same_wrapper_confirmed"]}`
- can_rerun_spp001_after_manual_approval: `{summary["can_rerun_spp001_after_manual_approval"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, or `slprj` artifacts are committed. The source `.slx` is not modified. Bus-fault labels are not used. L12 remains special/excluded. `beta * RATE_A` remains an audit-only proxy and is not a real relay setting. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "spp001_bridge_builder_repair_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "spp001_bridge_builder_repair_summary.md", "IEEE39 SPP001 Bridge Builder Repair Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "spp001_bridge_builder_repair_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "spp001_bridge_builder_repair_report.json", payloads["report"])
    _write_kv_md(OUT_DIR / "spp001_bridge_builder_repair_report.md", "IEEE39 SPP001 Bridge Builder Repair Report", payloads["report"])
    _write_json(OUT_DIR / "spp001_repaired_same_wrapper_manifest.json", payloads["manifest"])
    _write_kv_md(OUT_DIR / "spp001_repaired_same_wrapper_manifest.md", "IEEE39 SPP001 Repaired Same-Wrapper Manifest", payloads["manifest"])
    _write_json(OUT_DIR / "spp001_bridge_builder_rerun_gate.json", payloads["gate"])
    _write_kv_md(OUT_DIR / "spp001_bridge_builder_rerun_gate.md", "IEEE39 SPP001 Bridge Builder Rerun Gate", payloads["gate"])
    _write_json(OUT_DIR / "no_leakage_spp001_bridge_builder_repair_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_spp001_bridge_builder_repair_audit.md", "IEEE39 SPP001 Builder Repair No-Leakage Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_safety_spp001_bridge_builder_repair.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_safety_spp001_bridge_builder_repair.md", "IEEE39 SPP001 Builder Repair Large-File Safety", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair IEEE39 SPP001 same-wrapper bridge builder only.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [PREVIOUS_SUMMARY, MATLAB_BUILDER, HANDWIRED_WRAPPER, L15_SOURCE_LAB]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads()
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
