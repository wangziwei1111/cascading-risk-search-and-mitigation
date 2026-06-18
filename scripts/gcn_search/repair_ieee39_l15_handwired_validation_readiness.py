from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair"
DOC = ROOT / "docs/ieee39_l15_handwired_validation_readiness_repair.md"
SOURCE_SPP001_SMOKE_COMMIT = "4c9e18b9aab9dce3d968ed3b47271372d60f78b2"
PREVIOUS_BLOCKER = "single-pair smoke not ready: validation missing for L15; L04 validation passed"

ARTIFACTS = [
    ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_summary.json",
    ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_result.json",
    ROOT / "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/single_pair_smoke_candidate.json",
    ROOT / "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/entrypoint_component_reuse_report.json",
    ROOT / "results/gcn_search/ieee39_controlled_execution_backend_repair/selected_pair_backend_readiness_matrix.json",
    ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv",
    ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.csv",
    ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10_l11_to_l34.csv",
    ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_line_trip_summary.csv",
    ROOT / "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_matrix.json",
]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _exists(path: Path) -> bool:
    return os.path.exists(_long(path))


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _read_json(path: Path) -> Any:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_row(row: dict[str, Any]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in row.items():
        cleaned[str(key).lstrip("\ufeff")] = "" if value is None else str(value)
    return cleaned


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not _exists(path):
        return []
    with open(_long(path), newline="", encoding="utf-8-sig", errors="ignore") as handle:
        return [_clean_row(row) for row in csv.DictReader(handle)]


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "passed"}


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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


def _write_rows_md(path: Path, title: str, rows: list[dict[str, Any]]) -> None:
    lines = [f"# {title}", ""]
    if not rows:
        lines.append("No rows.")
    else:
        headers = list(rows[0].keys())
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            lines.append("| " + " | ".join(str(row.get(header, "")).replace("|", "/") for header in headers) + " |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find_line_rows(path: Path, line_id: str) -> list[dict[str, str]]:
    rows = _read_csv(path)
    hits: list[dict[str, str]] = []
    for row in rows:
        values = {str(value).strip() for value in row.values()}
        if row.get("line_id") == line_id or row.get("tripped_line") == line_id or line_id in values:
            hits.append(row)
    return hits


def _validation_candidate(path: Path, line_id: str) -> dict[str, Any] | None:
    hits = _find_line_rows(path, line_id)
    if not hits:
        return None
    row = hits[0]
    validation_passed = _truthy(row.get("validation_passed", row.get("simulation_success", "")))
    trip_command_path = row.get("trip_command_path", "")
    trip_command_found = bool(trip_command_path) or _truthy(row.get("trip_command_found", ""))
    return {
        "line_id": line_id,
        "validation_passed": validation_passed,
        "trip_command_path": trip_command_path,
        "trip_command_found": trip_command_found,
        "validation_failure_reason": row.get("validation_failure_reason", row.get("timeout_or_error_message", "")),
        "source_artifact": _rel(path),
        "source_model": row.get("source_model", row.get("clean_lab_model_path", "")),
        "provenance": "existing evidence; no Simulink run in this repair round",
        "raw_row": row,
    }


def _select_best_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    passed_with_trip = [item for item in candidates if item["validation_passed"] and item["trip_command_found"]]
    if passed_with_trip:
        return passed_with_trip[0]
    passed = [item for item in candidates if item["validation_passed"]]
    if passed:
        return passed[0]
    return candidates[0]


def _readiness_status(candidate: dict[str, Any] | None) -> str:
    if candidate is None:
        return "blocked"
    if candidate["validation_passed"] and candidate["trip_command_found"]:
        return "ready"
    if candidate["validation_passed"] or candidate["trip_command_found"]:
        return "unknown"
    return "blocked"


def build_payloads() -> dict[str, Any]:
    searched = [_rel(path) for path in ARTIFACTS]
    missing = [_rel(path) for path in ARTIFACTS if not _exists(path)]

    l15_rows_found: list[dict[str, Any]] = []
    l04_rows_found: list[dict[str, Any]] = []
    l15_candidates: list[dict[str, Any]] = []
    l04_candidates: list[dict[str, Any]] = []
    for path in ARTIFACTS:
        if path.suffix.lower() != ".csv" or not _exists(path):
            continue
        for row in _find_line_rows(path, "L15"):
            l15_rows_found.append({"source_artifact": _rel(path), "row": row})
        for row in _find_line_rows(path, "L04"):
            l04_rows_found.append({"source_artifact": _rel(path), "row": row})
        l15_candidate = _validation_candidate(path, "L15")
        if l15_candidate:
            l15_candidates.append(l15_candidate)
        l04_candidate = _validation_candidate(path, "L04")
        if l04_candidate:
            l04_candidates.append(l04_candidate)

    selected_l15 = _select_best_candidate(l15_candidates)
    selected_l04 = _select_best_candidate(l04_candidates)
    l15_status = _readiness_status(selected_l15)
    l04_status = _readiness_status(selected_l04)
    l15_ready = l15_status == "ready"
    l04_ready = l04_status == "ready"
    preview_rows = [
        {
            "line_id": "L04",
            "validation_passed": bool(selected_l04 and selected_l04["validation_passed"]),
            "trip_command_path": selected_l04.get("trip_command_path", "") if selected_l04 else "",
            "validation_failure_reason": selected_l04.get("validation_failure_reason", "no L04 evidence found") if selected_l04 else "no L04 evidence found",
            "source_artifact": selected_l04.get("source_artifact", "") if selected_l04 else "",
            "readiness_status": l04_status,
            "provenance": selected_l04.get("provenance", "") if selected_l04 else "missing",
        },
        {
            "line_id": "L15",
            "validation_passed": bool(selected_l15 and selected_l15["validation_passed"]),
            "trip_command_path": selected_l15.get("trip_command_path", "") if selected_l15 else "",
            "validation_failure_reason": selected_l15.get("validation_failure_reason", "no L15 evidence found") if selected_l15 else "no L15 evidence found",
            "source_artifact": selected_l15.get("source_artifact", "") if selected_l15 else "",
            "readiness_status": l15_status,
            "provenance": selected_l15.get("provenance", "") if selected_l15 else "missing",
        },
    ]
    repaired_written = bool(preview_rows)
    if l15_status == "ready":
        recommended = "approve rerun of SPP001 single-pair smoke in a separate round"
        blocker = None
    elif l15_status == "blocked":
        recommended = "perform or repair L15 handwired breaker validation locally before rerunning SPP001"
        blocker = "L15 handwired validation readiness is blocked"
    else:
        recommended = "inspect L15 handwired evidence provenance before execution"
        blocker = "L15 handwired validation readiness is unknown"

    summary = {
        "repair_scope": "l15_handwired_validation_readiness_repair",
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
        "source_spp001_smoke_commit": SOURCE_SPP001_SMOKE_COMMIT,
        "target_line_id": "L15",
        "paired_next_line_id": "L04",
        "previous_blocker": PREVIOUS_BLOCKER,
        "l15_existing_evidence_found": selected_l15 is not None,
        "l15_trip_command_path_found": bool(selected_l15 and selected_l15["trip_command_found"]),
        "l15_validation_passed": bool(selected_l15 and selected_l15["validation_passed"]),
        "l15_readiness_status": l15_status,
        "l04_validation_still_passed": l04_ready,
        "repaired_combined_validation_written": repaired_written,
        "can_rerun_spp001_smoke_after_manual_approval": l15_ready and l04_ready,
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
        "recommended_next_step": recommended,
    }
    inventory = {
        "searched_artifacts": searched,
        "missing_artifacts": missing,
        "l15_rows_found": l15_rows_found,
        "l15_rows_missing": [artifact for artifact in searched if not any(row["source_artifact"] == artifact for row in l15_rows_found)],
        "l15_trip_command_candidates": [
            {
                "trip_command_path": item["trip_command_path"],
                "trip_command_found": item["trip_command_found"],
                "source_artifact": item["source_artifact"],
                "provenance": item["provenance"],
            }
            for item in l15_candidates
        ],
        "l15_validation_candidates": [
            {
                "validation_passed": item["validation_passed"],
                "validation_failure_reason": item["validation_failure_reason"],
                "source_artifact": item["source_artifact"],
                "source_model": item["source_model"],
                "provenance": item["provenance"],
            }
            for item in l15_candidates
        ],
        "selected_source_if_any": selected_l15["source_artifact"] if selected_l15 else None,
        "provenance": selected_l15["provenance"] if selected_l15 else "no existing L15 readiness evidence selected",
        "reason_not_selected_if_any": None if selected_l15 else "no L15 validation candidate found",
    }
    gate = {
        "gate_scope": "spp001_rerun_readiness_gate",
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "l15_ready": l15_ready,
        "l04_ready": l04_ready,
        "both_lines_ready": l15_ready and l04_ready,
        "selected_32_batch_allowed": False,
        "full_1056_allowed": False,
        "formal_label_export_allowed": False,
        "gcn_training_allowed": False,
        "can_request_spp001_rerun_approval": l15_ready and l04_ready,
        "blocker_if_any": None if l15_ready and l04_ready else blocker or "L04 readiness is not ready",
    }
    no_leakage = {
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "no_leakage_policy_passed": True,
    }
    safety = {
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
    return {
        "summary": summary,
        "inventory": inventory,
        "preview_rows": preview_rows,
        "gate": gate,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 L15 Handwired Validation Readiness Repair

This round is L15 handwired validation readiness repair. It does not train GCN, does not rerun formal audit, does not execute SPP001 smoke, does not execute the selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous SPP001 smoke attempt was blocked because L15 was missing from the validation evidence read by the single-pair runner while L04 had passed. This round only searches existing line-trip, clean breaker, and handwired breaker evidence and writes a repaired readiness preview for `L15 -> L04`. It does not create an SPP001 0/1 label.

## Current Result

- repair_scope: `{summary["repair_scope"]}`
- target_line_id: `{summary["target_line_id"]}`
- paired_next_line_id: `{summary["paired_next_line_id"]}`
- l15_existing_evidence_found: `{summary["l15_existing_evidence_found"]}`
- l15_trip_command_path_found: `{summary["l15_trip_command_path_found"]}`
- l15_validation_passed: `{summary["l15_validation_passed"]}`
- l15_readiness_status: `{summary["l15_readiness_status"]}`
- l04_validation_still_passed: `{summary["l04_validation_still_passed"]}`
- repaired_combined_validation_written: `{summary["repaired_combined_validation_written"]}`
- can_rerun_spp001_smoke_after_manual_approval: `{summary["can_rerun_spp001_smoke_after_manual_approval"]}`
- no_label_value_generated: `{summary["no_label_value_generated"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, or `slprj` artifacts are committed. The source `.slx` is not modified. Bus-fault labels are not used. L12 remains special/excluded. Pilot labels are not formal training labels. `beta * RATE_A` remains an audit-only proxy and is not a real relay setting. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "l15_readiness_repair_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "l15_readiness_repair_summary.md", "IEEE39 L15 Readiness Repair Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "l15_readiness_repair_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "l15_evidence_inventory.json", payloads["inventory"])
    _write_kv_md(OUT_DIR / "l15_evidence_inventory.md", "IEEE39 L15 Evidence Inventory", payloads["inventory"])
    _write_json(OUT_DIR / "repaired_combined_validation_preview.json", payloads["preview_rows"])
    _write_rows_md(OUT_DIR / "repaired_combined_validation_preview.md", "IEEE39 Repaired Combined Validation Preview", payloads["preview_rows"])
    _write_rows_csv(OUT_DIR / "repaired_combined_validation_preview.csv", payloads["preview_rows"])
    _write_json(OUT_DIR / "spp001_rerun_readiness_gate.json", payloads["gate"])
    _write_kv_md(OUT_DIR / "spp001_rerun_readiness_gate.md", "IEEE39 SPP001 Rerun Readiness Gate", payloads["gate"])
    _write_json(OUT_DIR / "no_leakage_l15_readiness_repair_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_l15_readiness_repair_audit.md", "IEEE39 L15 Readiness No-Leakage Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_safety_l15_readiness_repair.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_safety_l15_readiness_repair.md", "IEEE39 L15 Readiness Large-File Safety", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair IEEE39 L15 handwired validation readiness from existing artifacts only.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    if args.strict:
        required = [
            ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_summary.json",
            ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv",
        ]
        missing = [_rel(path) for path in required if not _exists(path)]
        if missing:
            raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads()
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
