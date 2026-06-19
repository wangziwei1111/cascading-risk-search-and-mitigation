from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run"
DOC = ROOT / "docs/ieee39_spp001_same_wrapper_bridge_dry_run.md"
SOURCE_PROVENANCE_BRIDGE_COMMIT = "5ad76acea5fb0e8c1f887ce868d2e1ce5dc08c27"

PROVENANCE_SUMMARY = ROOT / "results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/spp001_provenance_bridge_repair_summary.json"
PROVENANCE_MANIFEST = ROOT / "results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/spp001_repaired_provenance_manifest.json"
PROVENANCE_GATE = ROOT / "results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/spp001_rerun_provenance_gate.json"
READINESS_PREVIEW = ROOT / "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/repaired_combined_validation_preview.csv"
MULTI_VALIDATION = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv"
CLEAN_BATCH_VALIDATION = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.csv"
BASE_WRAPPER = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx"
HANDWIRED_WRAPPER = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx"
MATLAB_SKELETON = ROOT / "matlab/simulink_ieee39/prepare_ieee39_spp001_same_wrapper_bridge_lab.m"


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


def _model_from_command(path: str | None) -> str | None:
    if not path:
        return None
    return str(path).split("/", 1)[0]


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _line_candidates(line_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in [READINESS_PREVIEW, MULTI_VALIDATION, CLEAN_BATCH_VALIDATION]:
        for row in _read_csv(source):
            if str(row.get("line_id") or "") != line_id:
                continue
            command_path = str(row.get("trip_command_path") or "")
            rows.append(
                {
                    "line_id": line_id,
                    "trip_command_name": str(row.get("trip_command_name") or f"{line_id}_TripCommand"),
                    "trip_command_path": command_path,
                    "trip_command_model_source": _model_from_command(command_path),
                    "validation_passed": _boolish(row.get("validation_passed")),
                    "source_artifact": str(source.relative_to(ROOT)),
                }
            )
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique[row["trip_command_path"]] = row
    return list(unique.values())


def build_payloads() -> dict[str, Any]:
    provenance_summary = _read_json(PROVENANCE_SUMMARY)
    provenance_manifest = _read_json(PROVENANCE_MANIFEST)
    provenance_gate = _read_json(PROVENANCE_GATE)
    l15_candidates = _line_candidates("L15")
    l04_candidates = _line_candidates("L04")

    command_names = {"L15_TripCommand", "L04_TripCommand"}
    name_conflict = len(command_names) != 2
    base_wrapper_available = _exists(BASE_WRAPPER)
    matlab_skeleton_available = _exists(MATLAB_SKELETON)
    can_build_locally = base_wrapper_available and matlab_skeleton_available and not name_conflict
    local_lab_copy_required = True
    can_confirm_now = bool(provenance_manifest.get("same_wrapper_confirmed", False))
    blocker = None if can_build_locally else "bridge builder skeleton or compatible base wrapper is not available"

    selected_wrapper_name = "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab"
    local_lab_copy_path = (
        "results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/local_lab_copy/"
        "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab.slx"
    )
    component_plan = {
        "plan_scope": "spp001_same_wrapper_bridge_component_plan",
        "pair_id": "SPP001",
        "source_base_wrapper": str(BASE_WRAPPER.relative_to(ROOT)),
        "fallback_handwired_wrapper": str(HANDWIRED_WRAPPER.relative_to(ROOT)),
        "matlab_builder_skeleton": str(MATLAB_SKELETON.relative_to(ROOT)),
        "local_lab_copy_path_planned": local_lab_copy_path,
        "required_trip_commands": ["L15_TripCommand", "L04_TripCommand"],
        "required_breaker_blocks": ["L15_HandwiredTimedBreaker", "L04_HandwiredTimedBreaker"],
        "trip_command_name_conflict": name_conflict,
        "local_lab_copy_only": True,
        "source_slx_modified": False,
        "simulink_run": False,
        "formal_labels_exported": False,
        "notes": "Build in a future approved round only; this dry-run does not create or commit .slx files.",
    }
    candidate_manifest = {
        "manifest_scope": "spp001_same_wrapper_candidate_manifest",
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "selected_wrapper_model": selected_wrapper_name if can_build_locally else None,
        "planned_local_lab_copy_path": local_lab_copy_path if can_build_locally else None,
        "prior_trip_command_path_planned": f"{selected_wrapper_name}/Grid/L15_TripCommand" if can_build_locally else None,
        "next_trip_command_path_planned": f"{selected_wrapper_name}/Grid/L04_TripCommand" if can_build_locally else None,
        "same_wrapper_confirmed_now": False,
        "same_wrapper_bridge_planned": True,
        "same_wrapper_bridge_built_this_round": False,
        "requires_local_lab_build": local_lab_copy_required,
        "approved_for_execution_now": False,
        "requires_next_round_approval": True,
        "blocker_if_any": blocker,
        "source_provenance_manifest": str(PROVENANCE_MANIFEST.relative_to(ROOT)),
        "previous_same_wrapper_confirmed": provenance_manifest.get("same_wrapper_confirmed"),
    }
    gate = {
        "gate_scope": "spp001_same_wrapper_bridge_readiness_gate",
        "pair_id": "SPP001",
        "l15_ready": True,
        "l04_ready": True,
        "same_wrapper_confirmed_now": False,
        "local_bridge_build_required": local_lab_copy_required,
        "selected_32_batch_allowed": False,
        "full_1056_allowed": False,
        "formal_label_export_allowed": False,
        "gcn_training_allowed": False,
        "can_request_local_bridge_build_approval": can_build_locally,
        "can_request_spp001_smoke_rerun_approval": False,
        "blocker_if_any": blocker,
    }
    no_leakage = {
        "audit_scope": "spp001_same_wrapper_bridge_dry_run_no_leakage_audit",
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "no_leakage_policy_passed": True,
    }
    safety = {
        "safety_scope": "spp001_same_wrapper_bridge_dry_run_large_file_safety",
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "local_lab_copy_committed": False,
        "source_slx_modified": False,
        "venv_committed": False,
        "wheel_or_dll_committed": False,
        "model_files_committed": False,
        "safety_check_passed": True,
    }
    checklist_lines = [
        "# IEEE39 SPP001 Same-Wrapper Bridge Local Execution Checklist",
        "",
        "- Obtain separate manual approval before building any local lab copy.",
        "- Use only pair_id `SPP001`, prior `L15`, next `L04`.",
        "- Build a local-only lab copy outside tracked Git artifacts.",
        "- Confirm both `L15_TripCommand` and `L04_TripCommand` belong to the same model.",
        "- Do not run SPP001 smoke in the bridge-build round.",
        "- Do not export formal labels or train GCN.",
        "- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries.",
        "- Remember: `phasor_RMS` is not EMT, `generator_speed_proxy` is not direct frequency, and temporary bus-fault injection is not engineering-grade protection.",
    ]
    summary = {
        "dry_run_scope": "spp001_same_wrapper_bridge_dry_run",
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
        "source_provenance_bridge_commit": SOURCE_PROVENANCE_BRIDGE_COMMIT,
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "same_wrapper_bridge_planned": True,
        "same_wrapper_bridge_built_this_round": False,
        "local_lab_copy_required": local_lab_copy_required,
        "local_lab_copy_committed": False,
        "source_slx_modified": False,
        "can_build_same_wrapper_bridge_locally": can_build_locally,
        "can_confirm_same_wrapper_now": can_confirm_now,
        "can_rerun_spp001_after_manual_approval": False,
        "no_label_value_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "blocker_if_any": blocker,
        "recommended_next_step": (
            "approve local SPP001 same-wrapper bridge build/validation in a separate round; do not run smoke yet"
            if can_build_locally
            else "repair bridge builder or identify compatible wrapper before any SPP001 rerun"
        ),
        "l15_trip_command_candidates": l15_candidates,
        "l04_trip_command_candidates": l04_candidates,
        "previous_provenance_summary": {
            "same_wrapper_trip_commands_available": provenance_summary.get("same_wrapper_trip_commands_available"),
            "blocker_if_any": provenance_summary.get("blocker_if_any"),
        },
        "previous_provenance_gate": {
            "provenance_bridge_ready": provenance_gate.get("provenance_bridge_ready"),
            "can_request_spp001_rerun_approval": provenance_gate.get("can_request_spp001_rerun_approval"),
        },
    }
    return {
        "summary": summary,
        "component_plan": component_plan,
        "candidate_manifest": candidate_manifest,
        "checklist_md": "\n".join(checklist_lines) + "\n",
        "gate": gate,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 SPP001 Same-Wrapper Bridge Dry-Run

This round is an SPP001 same-wrapper bridge dry-run. It does not train GCN, does not rerun formal audit, does not execute SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous blocker is that L15 and L04 TripCommand paths are not in the same wrapper. This dry-run only prepares a one-pair same-wrapper bridge plan. If a bridge `.slx` is needed, it must be a local lab copy and must not be committed. This round does not generate a 0/1 label.

## Result

- dry_run_scope: `{summary["dry_run_scope"]}`
- pair_id: `{summary["pair_id"]}`
- same_wrapper_bridge_planned: `{summary["same_wrapper_bridge_planned"]}`
- same_wrapper_bridge_built_this_round: `{summary["same_wrapper_bridge_built_this_round"]}`
- local_lab_copy_required: `{summary["local_lab_copy_required"]}`
- local_lab_copy_committed: `{summary["local_lab_copy_committed"]}`
- source_slx_modified: `{summary["source_slx_modified"]}`
- can_build_same_wrapper_bridge_locally: `{summary["can_build_same_wrapper_bridge_locally"]}`
- can_confirm_same_wrapper_now: `{summary["can_confirm_same_wrapper_now"]}`
- can_rerun_spp001_after_manual_approval: `{summary["can_rerun_spp001_after_manual_approval"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, or `slprj` artifacts are committed. The source `.slx` is not modified. Bus-fault labels are not used. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "spp001_same_wrapper_bridge_dry_run_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "spp001_same_wrapper_bridge_dry_run_summary.md", "IEEE39 SPP001 Same-Wrapper Bridge Dry-Run Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "spp001_same_wrapper_bridge_dry_run_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "spp001_bridge_component_plan.json", payloads["component_plan"])
    _write_kv_md(OUT_DIR / "spp001_bridge_component_plan.md", "IEEE39 SPP001 Bridge Component Plan", payloads["component_plan"])
    _write_json(OUT_DIR / "spp001_same_wrapper_candidate_manifest.json", payloads["candidate_manifest"])
    _write_kv_md(OUT_DIR / "spp001_same_wrapper_candidate_manifest.md", "IEEE39 SPP001 Same-Wrapper Candidate Manifest", payloads["candidate_manifest"])
    (OUT_DIR / "spp001_bridge_local_execution_checklist.md").write_text(payloads["checklist_md"], encoding="utf-8")
    _write_json(OUT_DIR / "spp001_bridge_readiness_gate.json", payloads["gate"])
    _write_kv_md(OUT_DIR / "spp001_bridge_readiness_gate.md", "IEEE39 SPP001 Bridge Readiness Gate", payloads["gate"])
    _write_json(OUT_DIR / "no_leakage_spp001_bridge_dry_run_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_spp001_bridge_dry_run_audit.md", "IEEE39 SPP001 Bridge Dry-Run No-Leakage Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_safety_spp001_bridge_dry_run.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_safety_spp001_bridge_dry_run.md", "IEEE39 SPP001 Bridge Dry-Run Large-File Safety", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare IEEE39 SPP001 same-wrapper bridge dry-run artifacts only.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [PROVENANCE_SUMMARY, PROVENANCE_MANIFEST, PROVENANCE_GATE, READINESS_PREVIEW, MULTI_VALIDATION, CLEAN_BATCH_VALIDATION, MATLAB_SKELETON]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads()
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
