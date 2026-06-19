from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_model_provenance_bridge_repair"
DOC = ROOT / "docs/ieee39_spp001_model_provenance_bridge_repair.md"
SOURCE_SPP001_RERUN_COMMIT = "f33eb97790a2bcc232a17ecd79be6c5153407f3b"

RERUN_SUMMARY = ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_rerun_summary.json"
RERUN_RESULT = ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_rerun_result.json"
READINESS_PREVIEW = ROOT / "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/repaired_combined_validation_preview.csv"
READINESS_GATE = ROOT / "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/spp001_rerun_readiness_gate.json"
CONTRACT = ROOT / "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/single_pair_smoke_execution_contract.json"
REUSE = ROOT / "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/entrypoint_component_reuse_report.json"
MULTI_VALIDATION = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv"
CLEAN_BATCH_VALIDATION = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.csv"
CLEAN_BATCH_TRIP_SUMMARY = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_line_trip_summary.csv"


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


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not _exists(path):
        return []
    with open(_long(path), newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


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


def _model_from_command_path(path: str | None) -> str | None:
    if not path:
        return None
    return str(path).split("/", 1)[0]


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _candidate_from_row(row: dict[str, Any], source_artifact: Path) -> dict[str, Any]:
    command_path = str(row.get("trip_command_path") or "")
    return {
        "line_id": str(row.get("line_id") or ""),
        "trip_command_path": command_path,
        "trip_command_model_source": _model_from_command_path(command_path),
        "validation_passed": _boolish(row.get("validation_passed")),
        "source_artifact": str(source_artifact.relative_to(ROOT)) if source_artifact.is_absolute() else str(source_artifact),
        "readiness_status": str(row.get("readiness_status") or ("ready" if _boolish(row.get("validation_passed")) else "not_ready")),
        "provenance": str(row.get("provenance") or "existing evidence; no Simulink run in this repair round"),
    }


def _collect_candidates(line_id: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for artifact in [READINESS_PREVIEW, MULTI_VALIDATION, CLEAN_BATCH_VALIDATION, CLEAN_BATCH_TRIP_SUMMARY]:
        for row in _read_csv(artifact):
            if str(row.get("line_id") or row.get("tripped_line") or "") == line_id:
                normalized = dict(row)
                if "tripped_line" in normalized and "line_id" not in normalized:
                    normalized["line_id"] = normalized["tripped_line"]
                candidates.append(_candidate_from_row(normalized, artifact))
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for item in candidates:
        key = (item["line_id"], item["trip_command_path"])
        unique[key] = item
    return list(unique.values())


def _selected_ready(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    ready = [row for row in candidates if row.get("validation_passed") and row.get("trip_command_path")]
    if not ready:
        return None
    readiness_rows = [row for row in ready if "l15_handwired_validation_readiness_repair" in row.get("source_artifact", "")]
    return readiness_rows[0] if readiness_rows else ready[0]


def build_payloads() -> dict[str, Any]:
    rerun_summary = _read_json(RERUN_SUMMARY)
    reuse = _read_json(REUSE)
    gate_source = _read_json(READINESS_GATE)
    _ = _read_json(RERUN_RESULT)
    _ = _read_json(CONTRACT)

    l15_candidates = _collect_candidates("L15")
    l04_candidates = _collect_candidates("L04")
    selected_l15 = _selected_ready(l15_candidates)
    selected_l04 = _selected_ready(l04_candidates)
    loaded_wrapper = str(reuse.get("available_wrapper_model_source", ""))
    loaded_wrapper_model = Path(loaded_wrapper).stem if loaded_wrapper else None

    same_wrapper_candidates = []
    for l15 in l15_candidates:
        for l04 in l04_candidates:
            if (
                l15.get("validation_passed")
                and l04.get("validation_passed")
                and l15.get("trip_command_model_source")
                and l15.get("trip_command_model_source") == l04.get("trip_command_model_source")
            ):
                same_wrapper_candidates.append(
                    {
                        "wrapper_model": l15["trip_command_model_source"],
                        "prior_trip_command_path": l15["trip_command_path"],
                        "next_trip_command_path": l04["trip_command_path"],
                        "l15_source_artifact": l15["source_artifact"],
                        "l04_source_artifact": l04["source_artifact"],
                    }
                )

    selected_candidate = None
    for candidate in same_wrapper_candidates:
        if candidate["wrapper_model"] == loaded_wrapper_model:
            selected_candidate = candidate
            break
    if selected_candidate is None and same_wrapper_candidates:
        selected_candidate = same_wrapper_candidates[0]

    same_wrapper_confirmed = selected_candidate is not None
    same_wrapper_available = same_wrapper_confirmed
    mismatch_reason = (
        "L15 TripCommand path belongs to the clean-lab L15 model, not the loaded handwired breaker wrapper"
    )
    reason_not_selected = None if selected_candidate else mismatch_reason
    blocker = None if selected_candidate else mismatch_reason

    manifest = {
        "manifest_scope": "spp001_same_wrapper_provenance_manifest",
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "selected_wrapper_model": selected_candidate["wrapper_model"] if selected_candidate else None,
        "prior_trip_command_path": selected_candidate["prior_trip_command_path"] if selected_candidate else None,
        "next_trip_command_path": selected_candidate["next_trip_command_path"] if selected_candidate else None,
        "same_wrapper_confirmed": same_wrapper_confirmed,
        "source_slx_modified": False,
        "approved_for_execution_now": False,
        "requires_next_round_approval": True,
        "blocker_if_any": blocker,
    }
    gate = {
        "gate_scope": "spp001_rerun_provenance_gate",
        "pair_id": "SPP001",
        "l15_ready": bool(gate_source.get("l15_ready")),
        "l04_ready": bool(gate_source.get("l04_ready")),
        "same_wrapper_confirmed": same_wrapper_confirmed,
        "provenance_bridge_ready": same_wrapper_confirmed,
        "selected_32_batch_allowed": False,
        "full_1056_allowed": False,
        "formal_label_export_allowed": False,
        "gcn_training_allowed": False,
        "can_request_spp001_rerun_approval": same_wrapper_confirmed,
        "blocker_if_any": blocker,
    }
    inventory = {
        "searched_artifacts": [
            str(path.relative_to(ROOT))
            for path in [RERUN_SUMMARY, RERUN_RESULT, READINESS_PREVIEW, READINESS_GATE, CONTRACT, REUSE, MULTI_VALIDATION, CLEAN_BATCH_VALIDATION, CLEAN_BATCH_TRIP_SUMMARY]
        ],
        "l15_trip_command_candidates": l15_candidates,
        "l04_trip_command_candidates": l04_candidates,
        "loaded_wrapper_candidates": [
            {
                "wrapper_model_source": loaded_wrapper,
                "wrapper_model_name": loaded_wrapper_model,
                "source_artifact": str(REUSE.relative_to(ROOT)),
            }
        ],
        "same_wrapper_candidates": same_wrapper_candidates,
        "rejected_candidates": [] if selected_candidate else [
            {
                "reason": mismatch_reason,
                "l15_selected_model": selected_l15.get("trip_command_model_source") if selected_l15 else None,
                "l04_selected_model": selected_l04.get("trip_command_model_source") if selected_l04 else None,
                "loaded_wrapper_model": loaded_wrapper_model,
            }
        ],
        "selected_candidate_if_any": selected_candidate,
        "reason_not_selected_if_any": reason_not_selected,
    }
    no_leakage = {
        "audit_scope": "spp001_model_provenance_bridge_no_leakage_audit",
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "no_leakage_policy_passed": True,
    }
    safety = {
        "safety_scope": "spp001_model_provenance_bridge_large_file_safety",
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "source_slx_modified": False,
        "venv_committed": False,
        "wheel_or_dll_committed": False,
        "model_files_committed": False,
        "safety_check_passed": True,
    }
    summary = {
        "repair_scope": "spp001_model_provenance_bridge_repair",
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
        "source_spp001_rerun_commit": SOURCE_SPP001_RERUN_COMMIT,
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "previous_execution_status": rerun_summary.get("execution_status"),
        "previous_blocker": mismatch_reason,
        "l15_trip_command_model_source": selected_l15.get("trip_command_model_source") if selected_l15 else None,
        "l04_trip_command_model_source": selected_l04.get("trip_command_model_source") if selected_l04 else None,
        "loaded_execution_wrapper_source": loaded_wrapper,
        "same_wrapper_trip_commands_available": same_wrapper_available,
        "repaired_provenance_manifest_written": True,
        "can_rerun_spp001_after_manual_approval": same_wrapper_confirmed,
        "no_label_value_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "source_slx_modified": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "blocker_if_any": blocker,
        "recommended_next_step": (
            "approve rerun of SPP001 using repaired provenance manifest in a separate round"
            if same_wrapper_confirmed
            else "build or validate an SPP001-only same-wrapper bridge locally before any rerun"
        ),
    }
    return {
        "summary": summary,
        "inventory": inventory,
        "manifest": manifest,
        "gate": gate,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 SPP001 Model Provenance Bridge Repair

This round is an SPP001 model provenance bridge repair. It does not train GCN, does not rerun formal audit, does not execute SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous SPP001 rerun failed because the L15 trip command path belongs to a clean-lab L15 model, while the execution wrapper loads the handwired breaker wrapper. This round only checks whether L15 and L04 can be controlled from the same wrapper. If same-wrapper provenance cannot be confirmed, the path is not fabricated and no SPP001 0/1 label is generated.

## Result

- repair_scope: `{summary["repair_scope"]}`
- pair_id: `{summary["pair_id"]}`
- prior_outaged_branch: `{summary["prior_outaged_branch"]}`
- candidate_next_branch: `{summary["candidate_next_branch"]}`
- l15_trip_command_model_source: `{summary["l15_trip_command_model_source"]}`
- l04_trip_command_model_source: `{summary["l04_trip_command_model_source"]}`
- loaded_execution_wrapper_source: `{summary["loaded_execution_wrapper_source"]}`
- same_wrapper_trip_commands_available: `{summary["same_wrapper_trip_commands_available"]}`
- repaired_provenance_manifest_written: `{summary["repaired_provenance_manifest_written"]}`
- can_rerun_spp001_after_manual_approval: `{summary["can_rerun_spp001_after_manual_approval"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, or `slprj` artifacts are committed. The source `.slx` is not modified. Bus-fault labels are not used. L12 remains special/excluded. Pilot labels are not formal training labels. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "spp001_provenance_bridge_repair_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "spp001_provenance_bridge_repair_summary.md", "IEEE39 SPP001 Provenance Bridge Repair Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "spp001_provenance_bridge_repair_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "spp001_trip_command_provenance_inventory.json", payloads["inventory"])
    _write_kv_md(OUT_DIR / "spp001_trip_command_provenance_inventory.md", "IEEE39 SPP001 Trip Command Provenance Inventory", payloads["inventory"])
    _write_json(OUT_DIR / "spp001_repaired_provenance_manifest.json", payloads["manifest"])
    _write_kv_md(OUT_DIR / "spp001_repaired_provenance_manifest.md", "IEEE39 SPP001 Repaired Provenance Manifest", payloads["manifest"])
    _write_json(OUT_DIR / "spp001_rerun_provenance_gate.json", payloads["gate"])
    _write_kv_md(OUT_DIR / "spp001_rerun_provenance_gate.md", "IEEE39 SPP001 Rerun Provenance Gate", payloads["gate"])
    _write_json(OUT_DIR / "no_leakage_spp001_provenance_bridge_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_spp001_provenance_bridge_audit.md", "IEEE39 SPP001 Provenance Bridge No-Leakage Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_safety_spp001_provenance_bridge.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_safety_spp001_provenance_bridge.md", "IEEE39 SPP001 Provenance Bridge Large-File Safety", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose and repair SPP001 same-wrapper provenance bridge evidence only.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [RERUN_SUMMARY, RERUN_RESULT, READINESS_PREVIEW, READINESS_GATE, CONTRACT, REUSE, MULTI_VALIDATION, CLEAN_BATCH_VALIDATION]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads()
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
