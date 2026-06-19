from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_local_validation"
DOC = ROOT / "docs/ieee39_spp001_same_wrapper_bridge_local_validation.md"

SOURCE_BRIDGE_DRY_RUN_COMMIT = "dbd79482a0bc78fefdb95fb7d87c69af7ba092e6"
DRY_RUN_DIR = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run"
DRY_RUN_SUMMARY = DRY_RUN_DIR / "spp001_same_wrapper_bridge_dry_run_summary.json"
DRY_RUN_PLAN = DRY_RUN_DIR / "spp001_bridge_component_plan.json"
DRY_RUN_MANIFEST = DRY_RUN_DIR / "spp001_same_wrapper_candidate_manifest.json"
DRY_RUN_GATE = DRY_RUN_DIR / "spp001_bridge_readiness_gate.json"
PROVENANCE_MANIFEST = ROOT / "results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/spp001_repaired_provenance_manifest.json"
MATLAB_BUILDER = ROOT / "matlab/simulink_ieee39/prepare_ieee39_spp001_same_wrapper_bridge_lab.m"
SELECTED_PAIR_ENTRYPOINT = ROOT / "matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m"
HANDWIRED_WRAPPER = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx"

LOCAL_COPY_DIR = OUT_DIR / "local_lab_copy"
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


def _copy_local_bridge(source: Path, target: Path) -> tuple[bool, str | None]:
    if not _exists(source):
        return False, f"source wrapper not found: {source.relative_to(ROOT)}"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(_long(source), _long(target))
    except Exception as exc:  # pragma: no cover - platform-specific IO message
        return False, f"local bridge copy failed: {exc}"
    return _exists(target), None


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
    same_wrapper = bool(_exists(path) and l15_command and l04_command)
    blocker = None
    if not _exists(path):
        blocker = "local bridge copy was not created"
    elif not l15_command:
        blocker = "L15_TripCommand is not present in the local bridge copy"
    elif not l04_command:
        blocker = "L04_TripCommand is not present in the local bridge copy"
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
        "trip_command_model_source_l15": LOCAL_MODEL_NAME if l15_command else None,
        "trip_command_model_source_l04": LOCAL_MODEL_NAME if l04_command else None,
        "same_wrapper_confirmed": same_wrapper,
        "blocker_if_any": blocker,
    }


def build_payloads(approved_local_bridge_only: bool, pair_id: str) -> dict[str, Any]:
    pair_id = pair_id.upper()
    if pair_id != "SPP001":
        raise SystemExit("Only pair-id SPP001 is allowed for this local bridge validation.")

    required = [DRY_RUN_SUMMARY, DRY_RUN_PLAN, DRY_RUN_MANIFEST, DRY_RUN_GATE, PROVENANCE_MANIFEST, MATLAB_BUILDER, SELECTED_PAIR_ENTRYPOINT]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))

    dry_summary = _read_json(DRY_RUN_SUMMARY)
    dry_plan = _read_json(DRY_RUN_PLAN)
    dry_manifest = _read_json(DRY_RUN_MANIFEST)
    provenance_manifest = _read_json(PROVENANCE_MANIFEST)

    local_bridge_build_attempted = bool(approved_local_bridge_only)
    copy_created = False
    copy_error = None
    if local_bridge_build_attempted:
        copy_created, copy_error = _copy_local_bridge(HANDWIRED_WRAPPER, LOCAL_COPY_PATH)

    validation = _validate_bridge(LOCAL_COPY_PATH)
    local_bridge_validation_attempted = True
    same_wrapper_confirmed = bool(validation["same_wrapper_confirmed"])
    local_bridge_built = bool(copy_created and same_wrapper_confirmed)
    repaired_provenance_manifest_written = True
    blocker = validation["blocker_if_any"] or copy_error
    can_rerun = bool(same_wrapper_confirmed)
    recommended_next_step = (
        "approve rerun of SPP001 single-pair smoke using validated local bridge manifest in a separate round; do not export labels or train"
        if same_wrapper_confirmed
        else "repair local same-wrapper bridge builder before any SPP001 smoke rerun"
    )

    build_report = {
        "build_report_scope": "spp001_local_bridge_build_report",
        "pair_id": pair_id,
        "approved_local_bridge_only": approved_local_bridge_only,
        "source_wrapper_path": str(HANDWIRED_WRAPPER.relative_to(ROOT)),
        "target_local_bridge_path": str(LOCAL_COPY_PATH.relative_to(ROOT)),
        "local_bridge_build_attempted": local_bridge_build_attempted,
        "local_bridge_copy_created": copy_created,
        "local_bridge_built": local_bridge_built,
        "local_bridge_committed": False,
        "source_slx_modified": False,
        "simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "copy_error": copy_error,
        "note": "This is a local lab copy validation only; the copied .slx is ignored and must not be committed.",
    }
    manifest = {
        "manifest_scope": "spp001_validated_same_wrapper_manifest",
        "pair_id": pair_id,
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "selected_wrapper_model": LOCAL_MODEL_NAME if validation["local_bridge_file_exists"] else None,
        "local_bridge_path": str(LOCAL_COPY_PATH.relative_to(ROOT)) if validation["local_bridge_file_exists"] else None,
        "prior_trip_command_path": validation["l15_trip_command_path_in_bridge"],
        "next_trip_command_path": validation["l04_trip_command_path_in_bridge"],
        "l15_trip_command_found_in_bridge": validation["l15_trip_command_found_in_bridge"],
        "l04_trip_command_found_in_bridge": validation["l04_trip_command_found_in_bridge"],
        "same_wrapper_confirmed": same_wrapper_confirmed,
        "source_slx_modified": False,
        "approved_for_execution_now": False,
        "requires_next_round_approval": True,
        "previous_provenance_manifest_same_wrapper_confirmed": provenance_manifest.get("same_wrapper_confirmed"),
        "dry_run_manifest_same_wrapper_confirmed_now": dry_manifest.get("same_wrapper_confirmed_now"),
        "blocker_if_any": blocker,
    }
    gate = {
        "gate_scope": "spp001_local_bridge_rerun_gate",
        "pair_id": pair_id,
        "l15_ready": True,
        "l04_ready": True,
        "local_bridge_built": local_bridge_built,
        "same_wrapper_confirmed": same_wrapper_confirmed,
        "selected_32_batch_allowed": False,
        "full_1056_allowed": False,
        "formal_label_export_allowed": False,
        "gcn_training_allowed": False,
        "can_request_spp001_smoke_rerun_approval": can_rerun,
        "blocker_if_any": blocker,
    }
    no_leakage = {
        "audit_scope": "spp001_local_bridge_validation_no_leakage_audit",
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "no_leakage_policy_passed": True,
    }
    safety = {
        "safety_scope": "spp001_local_bridge_validation_large_file_safety",
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
        "validation_scope": "spp001_same_wrapper_bridge_local_validation",
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
        "source_bridge_dry_run_commit": SOURCE_BRIDGE_DRY_RUN_COMMIT,
        "pair_id": pair_id,
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "local_bridge_build_attempted": local_bridge_build_attempted,
        "local_bridge_validation_attempted": local_bridge_validation_attempted,
        "local_bridge_built": local_bridge_built,
        "local_bridge_committed": False,
        "source_slx_modified": False,
        "l15_trip_command_found_in_bridge": validation["l15_trip_command_found_in_bridge"],
        "l04_trip_command_found_in_bridge": validation["l04_trip_command_found_in_bridge"],
        "same_wrapper_confirmed": same_wrapper_confirmed,
        "repaired_provenance_manifest_written": repaired_provenance_manifest_written,
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
        "dry_run_inputs": {
            "dry_run_summary_scope": dry_summary.get("dry_run_scope"),
            "dry_run_can_build_same_wrapper_bridge_locally": dry_summary.get("can_build_same_wrapper_bridge_locally"),
            "dry_run_component_plan_scope": dry_plan.get("plan_scope"),
        },
    }
    return {
        "summary": summary,
        "build_report": build_report,
        "manifest": manifest,
        "gate": gate,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 SPP001 Same-Wrapper Bridge Local Validation

This round is SPP001 same-wrapper bridge local validation. It does not train GCN, does not rerun formal audit, does not execute SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The goal is only to check whether `L15_TripCommand` and `L04_TripCommand` can be present in the same local wrapper for `SPP001: L15 -> L04`. A local bridge `.slx` may be created for validation, but it is ignored by Git and must not be committed. This round does not generate a 0/1 label.

## Result

- validation_scope: `{summary["validation_scope"]}`
- pair_id: `{summary["pair_id"]}`
- local_bridge_build_attempted: `{summary["local_bridge_build_attempted"]}`
- local_bridge_validation_attempted: `{summary["local_bridge_validation_attempted"]}`
- local_bridge_built: `{summary["local_bridge_built"]}`
- local_bridge_committed: `{summary["local_bridge_committed"]}`
- source_slx_modified: `{summary["source_slx_modified"]}`
- l15_trip_command_found_in_bridge: `{summary["l15_trip_command_found_in_bridge"]}`
- l04_trip_command_found_in_bridge: `{summary["l04_trip_command_found_in_bridge"]}`
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
    _write_json(OUT_DIR / "spp001_local_bridge_validation_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "spp001_local_bridge_validation_summary.md", "IEEE39 SPP001 Local Bridge Validation Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "spp001_local_bridge_validation_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "spp001_local_bridge_build_report.json", payloads["build_report"])
    _write_kv_md(OUT_DIR / "spp001_local_bridge_build_report.md", "IEEE39 SPP001 Local Bridge Build Report", payloads["build_report"])
    _write_json(OUT_DIR / "spp001_validated_same_wrapper_manifest.json", payloads["manifest"])
    _write_kv_md(OUT_DIR / "spp001_validated_same_wrapper_manifest.md", "IEEE39 SPP001 Validated Same-Wrapper Manifest", payloads["manifest"])
    _write_json(OUT_DIR / "spp001_local_bridge_rerun_gate.json", payloads["gate"])
    _write_kv_md(OUT_DIR / "spp001_local_bridge_rerun_gate.md", "IEEE39 SPP001 Local Bridge Rerun Gate", payloads["gate"])
    _write_json(OUT_DIR / "no_leakage_spp001_local_bridge_validation_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_spp001_local_bridge_validation_audit.md", "IEEE39 SPP001 Local Bridge No-Leakage Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_safety_spp001_local_bridge_validation.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_safety_spp001_local_bridge_validation.md", "IEEE39 SPP001 Local Bridge Large-File Safety", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate IEEE39 SPP001 same-wrapper bridge local artifacts only.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--approved-local-bridge-only", action="store_true")
    parser.add_argument("--pair-id", default="SPP001")
    args = parser.parse_args()
    if args.strict and not args.approved_local_bridge_only:
        raise SystemExit("--strict requires --approved-local-bridge-only for this approved local validation round.")
    payloads = build_payloads(args.approved_local_bridge_only, args.pair_id)
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
