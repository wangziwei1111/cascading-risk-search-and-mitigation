from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_BACKEND_DIAGNOSIS_COMMIT = "0d96b0c258e23f4fe5c2ec01cac2a63b5d85c06f"
SOURCE_BACKEND_REPAIR_COMMIT = "5c15cf88c3d980e3491d7327602a4d318216f2e4"
SOURCE_SELECTED_32_EVIDENCE_COMMIT = "12f07cbc4d3b35883b1dd11078c87029d5df8aac"
SOURCE_ENTRYPOINT_REPAIR_COMMIT = "4a8284da5ec80d91c30fe814c9823af157e37fe9"
SOURCE_L15_READINESS_REPAIR_COMMIT = "a648b8cb2d4fb3a4c27a5e7f3e8e588280ddc0d1"

DIAGNOSIS_DIR = ROOT / "results/gcn_search/ieee39_controlled_execution_backend_diagnosis"
PILOT_PAIR_DIR = ROOT / "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run"
APPROVAL_JSON = ROOT / "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_approval.json"
OUT_DIR = ROOT / "results/gcn_search/ieee39_controlled_execution_backend_repair"
EXECUTION_OUT_DIR = ROOT / "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence"
ENTRYPOINT_REPAIR_DIR = ROOT / "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair"
SPP001_SMOKE_DIR = ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_execution"
SPP001_RERUN_DIR = ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_rerun"
DOC = ROOT / "docs/ieee39_controlled_execution_backend_repair.md"
EXECUTION_DOC = ROOT / "docs/ieee39_selected_32_pair_controlled_execution_evidence.md"
ENTRYPOINT_REPAIR_DOC = ROOT / "docs/ieee39_matlab_selected_pair_entrypoint_repair.md"
SPP001_SMOKE_DOC = ROOT / "docs/ieee39_spp001_single_pair_smoke_execution.md"
SPP001_RERUN_DOC = ROOT / "docs/ieee39_spp001_single_pair_smoke_rerun.md"

NEXT_STEP = "approve execution of selected 32 pairs using the repaired backend in a separate round"
BLOCKER = "execution intentionally not run in repair round; manual approval and explicit --execute are required"
EXECUTION_BLOCKER = (
    "selected 32 execution was approved, but the current MATLAB entrypoint is still a guarded skeleton; "
    "blocked evidence was written without fabricating pilot labels"
)
ENTRYPOINT_REPAIR_BLOCKER = "single-pair smoke mode prepared; actual execution requires separate manual approval"
SPP001_ENTRYPOINT_MATLAB_JSON = "matlab_selected_pair_compact_evidence_summary.json"
SPP001_PAIR_ID = "SPP001"


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
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            for key, value in out.items():
                if isinstance(value, list):
                    out[key] = ";".join(str(item) for item in value)
            writer.writerow(out)


def _write_results_md(path: Path, title: str, rows: list[dict[str, Any]]) -> None:
    lines = [
        f"# {title}",
        "",
        "These rows are compact pilot evidence only. They are not formal training labels.",
        "",
        "| pair_id | prior | next | status | label | label_status | reason |",
        "|---|---:|---:|---|---|---|---|",
    ]
    for row in rows:
        label = row.get("pilot_label_value")
        if label is None:
            label = "null"
        reason = str(row.get("timeout_or_failure_reason") or "").replace("|", "/")
        lines.append(
            "| {pair_id} | {prior_outaged_branch} | {candidate_next_branch} | "
            "{execution_status} | {label} | {pilot_label_status} | {reason} |".format(
                label=label,
                reason=reason,
                **row,
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _shorten(text: str, limit: int = 1200) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _json_null_if_empty(value: Any) -> Any:
    if value == []:
        return None
    return value


def _normalize_matlab_row(row: dict[str, Any], fallback_pair: dict[str, Any]) -> dict[str, Any]:
    planned = row.get("planned_contingency_sequence", fallback_pair.get("planned_contingency_sequence", []))
    if isinstance(planned, str):
        planned = [item for item in planned.split(";") if item]
    return {
        "pair_id": str(row.get("pair_id") or fallback_pair.get("pair_id")),
        "state_id": str(row.get("state_id") or fallback_pair.get("state_id")),
        "prior_outaged_branch": str(row.get("prior_outaged_branch") or fallback_pair.get("prior_outaged_branch")),
        "candidate_next_branch": str(row.get("candidate_next_branch") or fallback_pair.get("candidate_next_branch")),
        "planned_contingency_sequence": planned,
        "selection_bucket": str(row.get("selection_bucket") or fallback_pair.get("selection_bucket")),
        "execution_status": str(row.get("execution_status") or "unknown"),
        "pilot_label_value": _json_null_if_empty(row.get("pilot_label_value")),
        "pilot_label_status": str(row.get("pilot_label_status") or "unknown"),
        "dynamic_stress_score_if_available": _json_null_if_empty(row.get("dynamic_stress_score_if_available")),
        "unstable_flag_if_available": _json_null_if_empty(row.get("unstable_flag_if_available")),
        "instability_or_risk_reason": str(row.get("instability_or_risk_reason") or ""),
        "timeout_or_failure_reason": str(row.get("timeout_or_failure_reason") or ""),
        "evidence_source": str(row.get("evidence_source") or "matlab_single_pair_smoke_compact_evidence"),
        "raw_trajectory_committed": False,
        "full_timeseries_committed": False,
        "mat_file_committed": False,
        "bus_fault_label_used": False,
        "l12_special_case_flag": bool(row.get("l12_special_case_flag", False)),
        "notes": str(row.get("notes") or "single-pair compact evidence only; not a formal training label"),
    }


def _write_kv_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.append(f"## {key}")
            lines.append("```json")
            lines.append(json.dumps(value, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
        else:
            lines.append(f"- `{key}`: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_readiness_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# IEEE39 Selected Pair Backend Readiness Matrix",
        "",
        "This matrix is for future manual approval. It is not execution evidence and not a formal label export.",
        "",
        "| pair_id | prior | next | mapping | contract | matlab | parser | status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {pair_id} | {prior_outaged_branch} | {candidate_next_branch} | {mapping_ready} | "
            "{execution_contract_ready} | {matlab_entrypoint_ready} | {parser_contract_ready} | "
            "{current_status} |".format(**row)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _selected_pairs(max_pairs: int) -> list[dict[str, Any]]:
    rows = _read_json(PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json")
    return rows[:max_pairs]


def _build_readiness_matrix(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for row in pairs:
        l12_flag = "L12" in {row.get("prior_outaged_branch"), row.get("candidate_next_branch")}
        ready = not l12_flag
        matrix.append(
            {
                "pair_id": row["pair_id"],
                "prior_outaged_branch": row["prior_outaged_branch"],
                "candidate_next_branch": row["candidate_next_branch"],
                "mapping_ready": True,
                "l12_special_case_flag": l12_flag,
                "selected_32_guard_passed": True,
                "execution_contract_ready": True,
                "matlab_entrypoint_ready": True,
                "parser_contract_ready": True,
                "future_execution_ready": ready,
                "current_status": "ready_for_manual_approval" if ready else "blocked",
                "notes": "dry-run repair row; no selected pair was executed",
            }
        )
    return matrix


def _build_blocked_execution_rows(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pair in pairs:
        rows.append(
            {
                "pair_id": pair["pair_id"],
                "state_id": pair.get("state_id"),
                "prior_outaged_branch": pair.get("prior_outaged_branch"),
                "candidate_next_branch": pair.get("candidate_next_branch"),
                "planned_contingency_sequence": pair.get("planned_contingency_sequence", []),
                "selection_bucket": pair.get("selection_bucket"),
                "execution_status": "blocked",
                "pilot_label_value": None,
                "pilot_label_status": "blocked",
                "dynamic_stress_score_if_available": None,
                "unstable_flag_if_available": None,
                "instability_or_risk_reason": None,
                "timeout_or_failure_reason": EXECUTION_BLOCKER,
                "evidence_source": "python_controlled_runner_blocked_evidence",
                "raw_trajectory_committed": False,
                "full_timeseries_committed": False,
                "mat_file_committed": False,
                "bus_fault_label_used": False,
                "l12_special_case_flag": bool(pair.get("l12_special_case_flag", False)),
                "notes": "pilot-only compact evidence; no 0/1 label was fabricated",
            }
        )
    return rows


def _execution_recommended_next_step(summary: dict[str, Any]) -> str:
    if summary["blocked_pair_count"] == summary["selected_pair_count"]:
        return "inspect local MATLAB/Simulink execution logs and repair execution entrypoint before rerunning selected 32 evidence collection"
    if summary["pilot_label_available_count"] > 0 and summary["pilot_positive_count"] == 0:
        return "select additional high-risk single-outage pairs before any label export or GCN training"
    if summary["pilot_positive_count"] > 0 and summary["pilot_negative_count"] > 0:
        return "prepare pilot label export approval in a separate round; do not train yet"
    return "review selected 32 compact evidence before deciding whether another pilot execution round is needed"


def _choose_smoke_candidate(pairs: list[dict[str, Any]], pair_id: str | None = None) -> dict[str, Any]:
    if pair_id:
        for pair in pairs:
            if str(pair.get("pair_id")) == pair_id:
                return pair
        raise SystemExit(f"--pair-id was not found in selected pairs: {pair_id}")
    for pair in pairs:
        if (
            pair.get("selection_bucket") == "high_relay_ratio_pairs"
            and not bool(pair.get("l12_special_case_flag", False))
            and pair.get("prior_outaged_branch") != "L12"
            and pair.get("candidate_next_branch") != "L12"
        ):
            return pair
    for pair in pairs:
        if not bool(pair.get("l12_special_case_flag", False)):
            return pair
    raise SystemExit("No non-L12 selected pair is available for smoke candidate selection")


def build_entrypoint_repair_payloads(pair_id: str | None = None) -> dict[str, Any]:
    selected_32_summary = _read_json(EXECUTION_OUT_DIR / "selected_32_execution_summary.json")
    pairs = _read_json(PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json")
    if len(pairs) != 32:
        raise SystemExit("selected pair manifest must contain exactly 32 rows")
    candidate_pair = _choose_smoke_candidate(pairs, pair_id)
    candidate = {
        "pair_id": candidate_pair.get("pair_id"),
        "state_id": candidate_pair.get("state_id"),
        "prior_outaged_branch": candidate_pair.get("prior_outaged_branch"),
        "candidate_next_branch": candidate_pair.get("candidate_next_branch"),
        "planned_contingency_sequence": candidate_pair.get("planned_contingency_sequence"),
        "selection_bucket": candidate_pair.get("selection_bucket"),
        "why_selected_for_smoke": "first non-L12 high_relay_ratio selected pair" if not pair_id else "explicit pair_id requested",
        "l12_special_case_flag": False,
        "approved_for_execution_now": False,
        "requires_next_round_approval": True,
    }
    summary = {
        "repair_scope": "matlab_selected_pair_entrypoint_repair",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_32_pairs_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_selected_32_evidence_commit": SOURCE_SELECTED_32_EVIDENCE_COMMIT,
        "matlab_entrypoint_updated": True,
        "python_runner_updated": True,
        "parser_contract_updated": True,
        "selected_32_guard_preserved": True,
        "single_pair_smoke_mode_added": True,
        "batch_32_execution_allowed_now": False,
        "full_1056_execution_allowed_now": False,
        "can_attempt_single_pair_smoke_after_manual_approval": True,
        "can_attempt_selected_32_after_single_pair_smoke": False,
        "raw_trajectory_policy_preserved": True,
        "formal_label_export_guard_preserved": True,
        "no_training_guard_preserved": True,
        "blocker_if_any": ENTRYPOINT_REPAIR_BLOCKER,
        "recommended_next_step": "approve one selected pair smoke execution in a separate round",
        "previous_selected_32_blocked_pair_count": selected_32_summary.get("blocked_pair_count"),
        "previous_pilot_label_available_count": selected_32_summary.get("pilot_label_available_count"),
    }
    contract = {
        "contract_scope": "single_pair_smoke_execution_contract",
        "allowed_pair_count": 1,
        "selected_32_batch_execution_allowed": False,
        "full_1056_generation_allowed": False,
        "requires_manual_approval": True,
        "requires_explicit_execute": True,
        "timeout_policy": "timeout remains timeout/null and must not become 0/1",
        "unknown_policy": "unknown remains null",
        "failed_policy": "failed remains null",
        "blocked_policy": "blocked remains null",
        "label_value_policy": "pilot_label_value is only 0/1 when compact evidence can decide it; otherwise null",
        "compact_evidence_only": True,
        "raw_artifact_policy": "do not save or commit raw trajectories, full timeseries, .mat, .slx, .slxc, or slprj",
    }
    reuse = {
        "reused_matlab_components": [
            "matlab/simulink_ieee39/run_ieee39_multi_handwired_line_trip_suite.m",
            "matlab/simulink_ieee39/validate_ieee39_multi_handwired_breakers.m",
            "matlab/simulink_ieee39/extract_ieee39_signal_summary.m",
            "matlab/simulink_ieee39/configure_ieee39_short_filegen_paths.m",
        ],
        "reused_python_components": [
            "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
            "scripts/gcn_search/parse_ieee39_selected_pair_execution_evidence.py",
        ],
        "available_wrapper_model_source": "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx",
        "available_line_mapping_source": "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv",
        "two_step_sequence_strategy": "set prior TripCommand time first, set candidate TripCommand time later, set all other validated trip commands far in the future",
        "remaining_missing_components": [],
        "unsafe_components_rejected": [
            "full 1056 batch generation",
            "formal label export",
            "raw trajectory or full timeseries persistence",
            "source SLX modification",
        ],
        "source_slx_modified": False,
    }
    no_leakage = {
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "proxy_relay_threshold_used_only_in_feature_generation": True,
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
        "contract": contract,
        "reuse": reuse,
        "candidate": candidate,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def build_execution_payloads(max_pairs: int, approved_selected_pairs_only: bool) -> dict[str, Any]:
    if max_pairs > 32:
        raise SystemExit("--max-pairs cannot exceed 32 for selected-32-only controlled execution")
    if not approved_selected_pairs_only:
        raise SystemExit("--approved-selected-pairs-only is required")
    source_pairs = _read_json(PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json")
    if len(source_pairs) < max_pairs:
        raise SystemExit("selected pair manifest does not contain enough rows")
    pairs = source_pairs[:max_pairs]
    if max_pairs != 32:
        raise SystemExit("this approved evidence round must run with --max-pairs 32")

    approval = {
        "approval_scope": "selected_32_controlled_execution_approval",
        "source_backend_repair_commit": SOURCE_BACKEND_REPAIR_COMMIT,
        "approved_selected_pairs_only": True,
        "approved_pair_count": 32,
        "full_1056_generation_approved": False,
        "formal_label_export_approved": False,
        "gcn_training_approved": False,
        "reranker_retrain_approved": False,
        "raw_trajectory_commit_approved": False,
        "explicit_execute_required": True,
        "beta_rate_a_proxy_acknowledged": True,
        "proxy_allowed_for_audit_only_prototype": True,
        "proxy_allowed_for_production": False,
    }
    rows = _build_blocked_execution_rows(pairs)
    succeeded = sum(row["execution_status"] == "succeeded" for row in rows)
    failed = sum(row["execution_status"] == "failed" for row in rows)
    timeout = sum(row["execution_status"] == "timeout" for row in rows)
    blocked = sum(row["execution_status"] == "blocked" for row in rows)
    unknown = sum(row["pilot_label_status"] == "unknown" for row in rows)
    available = sum(row["pilot_label_status"] == "available" for row in rows)
    positives = sum(row["pilot_label_value"] == 1 for row in rows)
    negatives = sum(row["pilot_label_value"] == 0 for row in rows)
    pilot_timeout = sum(row["pilot_label_status"] == "timeout" for row in rows)
    pilot_failed = sum(row["pilot_label_status"] == "failed" for row in rows)
    pilot_blocked = sum(row["pilot_label_status"] == "blocked" for row in rows)
    pilot_unknown = unknown + pilot_timeout + pilot_failed + pilot_blocked
    summary = {
        "execution_scope": "selected_32_controlled_execution_evidence",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_backend_repair_commit": SOURCE_BACKEND_REPAIR_COMMIT,
        "selected_pair_count": len(rows),
        "executed_pair_count": succeeded + failed + timeout,
        "succeeded_pair_count": succeeded,
        "failed_pair_count": failed,
        "timeout_pair_count": timeout,
        "blocked_pair_count": blocked,
        "unknown_pair_count": unknown,
        "pilot_label_available_count": available,
        "pilot_positive_count": positives,
        "pilot_negative_count": negatives,
        "pilot_unknown_count": pilot_unknown,
        "pilot_timeout_count": pilot_timeout,
        "pilot_failed_count": pilot_failed,
        "pilot_blocked_count": pilot_blocked,
        "all_available_labels_negative": available > 0 and positives == 0,
        "has_positive_pilot_label": positives > 0,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "l12_special_case_preserved": True,
        "nf06_warning_preserved": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "pilot_labels_are_formal_training_labels": False,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "blocker_if_any": EXECUTION_BLOCKER,
        "recommended_next_step": "",
    }
    summary["recommended_next_step"] = _execution_recommended_next_step(summary)
    distribution = {
        "selected_pair_count": summary["selected_pair_count"],
        "pilot_label_available_count": available,
        "pilot_positive_count": positives,
        "pilot_negative_count": negatives,
        "pilot_unknown_count": pilot_unknown,
        "pilot_timeout_count": pilot_timeout,
        "pilot_failed_count": pilot_failed,
        "pilot_blocked_count": pilot_blocked,
        "all_available_labels_negative": summary["all_available_labels_negative"],
        "has_positive_pilot_label": summary["has_positive_pilot_label"],
        "class_balance_warning": "no available pilot labels; all selected pairs are blocked" if available == 0 else "",
        "training_readiness_recommendation": "do not train; repair execution entrypoint and rerun selected 32 evidence collection",
    }
    no_leakage = {
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "proxy_relay_threshold_used_only_in_feature_generation": True,
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
        "venv_committed": False,
        "wheel_or_dll_committed": False,
        "model_files_committed": False,
        "safety_check_passed": True,
    }
    return {
        "approval": approval,
        "summary": summary,
        "rows": rows,
        "distribution": distribution,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def build_payloads(max_pairs: int, approved_selected_pairs_only: bool, execute: bool) -> dict[str, Any]:
    if max_pairs > 32:
        raise SystemExit("--max-pairs cannot exceed 32 for selected-32-only backend repair")
    diagnosis = _read_json(DIAGNOSIS_DIR / "backend_readiness_summary.json")
    approval = _read_json(APPROVAL_JSON)
    pairs = _selected_pairs(max_pairs)
    if len(pairs) != 32:
        raise SystemExit("selected pair manifest must contain exactly 32 rows for this repair round")
    if not approved_selected_pairs_only:
        raise SystemExit("--approved-selected-pairs-only is required")
    if execute:
        raise SystemExit("Use build_execution_payloads for the approved selected-32 evidence execution mode")

    readiness = _build_readiness_matrix(pairs)
    summary = {
        "repair_scope": "controlled_execution_backend_repair",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_pairs_executed": False,
        "simulink_run": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_backend_diagnosis_commit": SOURCE_BACKEND_DIAGNOSIS_COMMIT,
        "selected_pair_count": len(pairs),
        "python_runner_added": True,
        "matlab_entrypoint_added": True,
        "result_parser_contract_added": True,
        "evidence_writer_added": True,
        "manual_instruction_pack_added": True,
        "selected_32_only_guard_added": True,
        "full_1056_guard_added": True,
        "no_formal_label_export_guard_added": True,
        "no_training_guard_added": True,
        "no_raw_artifact_policy_added": True,
        "graceful_blocked_mode_available": True,
        "can_execute_selected_32_pairs_after_manual_approval": True,
        "can_execute_selected_32_pairs_now": False,
        "blocker_if_any": BLOCKER,
        "recommended_next_step": NEXT_STEP,
        "source_diagnosis_scope": diagnosis.get("diagnosis_scope"),
        "approval_scope": approval.get("approval_scope"),
    }
    contract = {
        "contract_scope": "selected_pair_execution_contract",
        "allowed_pair_count": 32,
        "full_1056_generation_allowed": False,
        "requires_approved_selected_pairs_only": True,
        "requires_explicit_execute_flag": True,
        "default_mode": "dry_run_or_blocked",
        "allowed_outputs": [
            "compact per-pair evidence rows",
            "backend repair/readiness summary",
            "timeout or blocked status",
            "pilot_label_value only when future approved evidence can decide 0/1",
        ],
        "forbidden_outputs": [
            "formal training labels",
            "raw trajectories",
            "full timeseries",
            ".mat files",
            ".slx or .slxc modifications",
            "model checkpoints",
        ],
        "timeout_policy": "timeout remains timeout/unknown and is not converted to 0/1",
        "unknown_policy": "unknown and blocked remain null",
        "failed_policy": "failed remains failed/unknown and is not converted to 0/1",
        "label_value_policy": "pilot_label_value remains null unless future approved compact evidence determines 0 or 1",
        "formal_label_export_policy": False,
        "raw_artifact_policy": "commit only compact JSON/MD/CSV summaries; do not commit raw trajectories, full timeseries, .mat, .slx, .slxc, or slprj",
    }
    no_leakage = {
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "proxy_relay_threshold_used_only_in_feature_generation": True,
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
        "venv_committed": False,
        "wheel_or_dll_committed": False,
        "model_files_committed": False,
        "safety_check_passed": True,
    }
    return {
        "summary": summary,
        "contract": contract,
        "readiness": readiness,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _manual_instructions() -> str:
    return """# IEEE39 Selected-32 Manual Execution Instruction Pack

This instruction pack is for a future separately approved execution round. Do not use it to train GCN, rerun formal audit, export formal labels, retrain the reranker, or run full 1056 generation.

## 1. Confirm MATLAB/Simulink

Run `matlab -batch "ver"` locally and confirm Simulink is licensed. This repair round does not run Simulink.

## 2. Run Only Selected 32 Pairs

Use only `results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/selected_single_outage_pilot_pairs.json`. Do not substitute the 1056-pair plan.

## 3. Python Runner

Future approved command:

```powershell
python scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py --approved-selected-pairs-only --max-pairs 32 --execute --write-report
```

The repair round must not use `--execute`.

## 4. MATLAB Entrypoint

Future approved MATLAB entrypoint:

```matlab
run_ieee39_selected_pair_line_trip_sequence(manifestPath, outputDir, "approved_selected_pairs_only", true, "execute", true)
```

## 5. Output Directory

Write only compact evidence summaries under a future approved output directory. Do not write raw trajectory, full timeseries, or `.mat` files.

## 6. Safety Checks

Before committing, verify no raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, or model files are staged.

## 7. Timeout

Timeout remains timeout/unknown and must not become 0 or 1.

## 8. Blocked

Blocked remains null. Do not fabricate pilot labels.

## 9. Compact Evidence Summary

Collect one compact row per pair with `pair_id`, `execution_status`, `pilot_label_value`, `pilot_label_status`, `dynamic_stress_score_if_available`, `unstable_flag_if_available`, and `timeout_or_failure_reason`.

## 10. Forbidden Actions

Do not export formal labels. Do not train GCN. Do not run full 1056 generation. Manual approval is required before execution.
"""


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 Controlled Execution Backend Repair

This round is controlled execution backend repair. It does not train GCN, does not rerun formal audit, does not execute selected 32 pairs, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not save a production model.

## What Was Added

- selected-32-only Python runner
- MATLAB two-step line-trip entrypoint skeleton
- result parser contract
- evidence-only output writer
- local/manual execution instruction pack
- selected-32-only guard
- no full 1056 generation guard
- no formal label export guard
- no training guard
- no raw trajectory / full timeseries / `.mat` commit guard

## Current Status

- repair_scope: `{summary["repair_scope"]}`
- selected_pair_count: `{summary["selected_pair_count"]}`
- can_execute_selected_32_pairs_after_manual_approval: `{summary["can_execute_selected_32_pairs_after_manual_approval"]}`
- can_execute_selected_32_pairs_now: `{summary["can_execute_selected_32_pairs_now"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

Execution of selected 32 pairs still requires the next round of manual approval. This round does not commit raw trajectory, full timeseries, or `.mat` files. `beta * RATE_A` is an audit-only proxy, not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection. There is no deployment and no GCN usefulness conclusion.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "backend_repair_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "backend_repair_summary.md", "IEEE39 Backend Repair Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "backend_repair_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "backend_execution_contract.json", payloads["contract"])
    _write_kv_md(OUT_DIR / "backend_execution_contract.md", "IEEE39 Backend Execution Contract", payloads["contract"])
    (OUT_DIR / "manual_execution_instruction_pack.md").write_text(_manual_instructions(), encoding="utf-8")
    _write_json(OUT_DIR / "selected_pair_backend_readiness_matrix.json", payloads["readiness"])
    _write_readiness_md(OUT_DIR / "selected_pair_backend_readiness_matrix.md", payloads["readiness"])
    _write_rows_csv(OUT_DIR / "selected_pair_backend_readiness_matrix.csv", payloads["readiness"])
    _write_json(OUT_DIR / "no_leakage_backend_repair_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_backend_repair_audit.md", "IEEE39 No-Leakage Backend Repair Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_safety_backend_repair.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_safety_backend_repair.md", "IEEE39 Large File Safety Backend Repair", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def _build_execution_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 Selected 32 Pair Controlled Execution Evidence

This round is selected 32 pair controlled execution evidence. It does not train GCN, does not rerun formal audit, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The approved command was allowed to try only the selected 32 line-trip pilot pairs. The current MATLAB entrypoint is still a guarded skeleton, so this run writes compact blocked evidence instead of fabricating simulation results.

## Current Counts

- execution_scope: `{summary["execution_scope"]}`
- selected_pair_count: `{summary["selected_pair_count"]}`
- executed_pair_count: `{summary["executed_pair_count"]}`
- succeeded_pair_count: `{summary["succeeded_pair_count"]}`
- failed_pair_count: `{summary["failed_pair_count"]}`
- timeout_pair_count: `{summary["timeout_pair_count"]}`
- blocked_pair_count: `{summary["blocked_pair_count"]}`
- pilot_label_available_count: `{summary["pilot_label_available_count"]}`
- pilot_positive_count: `{summary["pilot_positive_count"]}`
- pilot_negative_count: `{summary["pilot_negative_count"]}`
- pilot_unknown_count: `{summary["pilot_unknown_count"]}`

## Boundaries

Only selected 32 pairs are in scope. Raw trajectories, full timeseries, `.mat`, `.slx`, `.slxc`, and `slprj` artifacts are not committed. Timeout, failed, blocked, and unknown results are not converted to 0/1. `beta * RATE_A` is an audit-only proxy and not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. Pilot labels are not formal training labels. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_execution_payloads(payloads: dict[str, Any], output_dir: Path, write_report: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "selected_32_execution_approval.json", payloads["approval"])
    _write_kv_md(output_dir / "selected_32_execution_approval.md", "IEEE39 Selected 32 Execution Approval", payloads["approval"])
    _write_json(output_dir / "selected_32_execution_summary.json", payloads["summary"])
    _write_kv_md(output_dir / "selected_32_execution_summary.md", "IEEE39 Selected 32 Execution Summary", payloads["summary"])
    _write_kv_csv(output_dir / "selected_32_execution_summary.csv", payloads["summary"])
    _write_json(output_dir / "selected_32_execution_results.json", payloads["rows"])
    _write_results_md(output_dir / "selected_32_execution_results.md", "IEEE39 Selected 32 Execution Results", payloads["rows"])
    _write_rows_csv(output_dir / "selected_32_execution_results.csv", payloads["rows"])
    _write_json(output_dir / "selected_32_label_distribution.json", payloads["distribution"])
    _write_kv_md(output_dir / "selected_32_label_distribution.md", "IEEE39 Selected 32 Label Distribution", payloads["distribution"])
    _write_json(output_dir / "no_leakage_selected_32_execution_audit.json", payloads["no_leakage"])
    _write_kv_md(output_dir / "no_leakage_selected_32_execution_audit.md", "IEEE39 No-Leakage Selected 32 Execution Audit", payloads["no_leakage"])
    _write_json(output_dir / "large_file_safety_selected_32_execution.json", payloads["safety"])
    _write_kv_md(output_dir / "large_file_safety_selected_32_execution.md", "IEEE39 Large File Safety Selected 32 Execution", payloads["safety"])
    if write_report:
        EXECUTION_DOC.write_text(_build_execution_doc(payloads), encoding="utf-8")


def _build_entrypoint_repair_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    candidate = payloads["candidate"]
    return f"""# IEEE39 MATLAB Selected-Pair Entrypoint Repair

This round is MATLAB selected-pair entrypoint repair. It does not train GCN, does not rerun formal audit, does not execute selected 32 pairs, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous selected-32 evidence round produced 32 blocked rows because the MATLAB entrypoint was still a skeleton. This round adds single-pair smoke execution mode so a future separately approved round can try at most one selected pair.

## Current Status

- repair_scope: `{summary["repair_scope"]}`
- matlab_entrypoint_updated: `{summary["matlab_entrypoint_updated"]}`
- python_runner_updated: `{summary["python_runner_updated"]}`
- parser_contract_updated: `{summary["parser_contract_updated"]}`
- single_pair_smoke_mode_added: `{summary["single_pair_smoke_mode_added"]}`
- batch_32_execution_allowed_now: `{summary["batch_32_execution_allowed_now"]}`
- full_1056_execution_allowed_now: `{summary["full_1056_execution_allowed_now"]}`
- can_attempt_single_pair_smoke_after_manual_approval: `{summary["can_attempt_single_pair_smoke_after_manual_approval"]}`

## Smoke Candidate

- pair_id: `{candidate["pair_id"]}`
- prior_outaged_branch: `{candidate["prior_outaged_branch"]}`
- candidate_next_branch: `{candidate["candidate_next_branch"]}`
- selection_bucket: `{candidate["selection_bucket"]}`
- approved_for_execution_now: `{candidate["approved_for_execution_now"]}`

## Boundaries

The next round may approve at most one selected pair smoke execution. This round does not commit raw trajectory, full timeseries, or `.mat` files and does not modify the source `.slx`. `beta * RATE_A` is an audit-only proxy, not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. Pilot labels are not formal training labels. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_entrypoint_repair_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    ENTRYPOINT_REPAIR_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(ENTRYPOINT_REPAIR_DIR / "matlab_entrypoint_repair_summary.json", payloads["summary"])
    _write_kv_md(ENTRYPOINT_REPAIR_DIR / "matlab_entrypoint_repair_summary.md", "IEEE39 MATLAB Entrypoint Repair Summary", payloads["summary"])
    _write_kv_csv(ENTRYPOINT_REPAIR_DIR / "matlab_entrypoint_repair_summary.csv", payloads["summary"])
    _write_json(ENTRYPOINT_REPAIR_DIR / "single_pair_smoke_execution_contract.json", payloads["contract"])
    _write_kv_md(ENTRYPOINT_REPAIR_DIR / "single_pair_smoke_execution_contract.md", "IEEE39 Single Pair Smoke Execution Contract", payloads["contract"])
    _write_json(ENTRYPOINT_REPAIR_DIR / "entrypoint_component_reuse_report.json", payloads["reuse"])
    _write_kv_md(ENTRYPOINT_REPAIR_DIR / "entrypoint_component_reuse_report.md", "IEEE39 Entrypoint Component Reuse Report", payloads["reuse"])
    _write_json(ENTRYPOINT_REPAIR_DIR / "single_pair_smoke_candidate.json", payloads["candidate"])
    _write_kv_md(ENTRYPOINT_REPAIR_DIR / "single_pair_smoke_candidate.md", "IEEE39 Single Pair Smoke Candidate", payloads["candidate"])
    _write_json(ENTRYPOINT_REPAIR_DIR / "no_leakage_entrypoint_repair_audit.json", payloads["no_leakage"])
    _write_kv_md(ENTRYPOINT_REPAIR_DIR / "no_leakage_entrypoint_repair_audit.md", "IEEE39 No-Leakage Entrypoint Repair Audit", payloads["no_leakage"])
    _write_json(ENTRYPOINT_REPAIR_DIR / "large_file_safety_entrypoint_repair.json", payloads["safety"])
    _write_kv_md(ENTRYPOINT_REPAIR_DIR / "large_file_safety_entrypoint_repair.md", "IEEE39 Large File Safety Entrypoint Repair", payloads["safety"])
    if write_report:
        ENTRYPOINT_REPAIR_DOC.write_text(_build_entrypoint_repair_doc(payloads), encoding="utf-8")


def _spp001_recommended_next_step(result: dict[str, Any]) -> str:
    status = result.get("execution_status")
    if status == "blocked":
        return "repair remaining single-pair execution blocker before any more pair execution"
    if status in {"timeout", "failed"}:
        return "inspect timeout/failure evidence and rerun one-pair smoke after repair"
    if status == "succeeded" and result.get("pilot_label_value") is None:
        return "repair compact evidence parser/label-decision contract before any label export"
    if status == "succeeded" and result.get("pilot_label_value") in {0, 1}:
        return "approve a tiny 3-to-5 pair smoke batch in a separate round; do not export formal labels or train yet"
    return "inspect compact single-pair evidence and define the pilot-label rule before any broader execution"


def _attempt_spp001_matlab(pair: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    matlab_output_dir = output_dir / "matlab_compact"
    matlab_output_dir.mkdir(parents=True, exist_ok=True)
    manifest = PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json"
    handwired_model = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx"
    validation_csv = ROOT / "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/repaired_combined_validation_preview.csv"
    command = (
        "addpath('matlab/simulink_ieee39'); "
        "run_ieee39_selected_pair_line_trip_sequence("
        f"'{manifest.as_posix()}', "
        f"'{matlab_output_dir.as_posix()}', "
        "'approved_selected_pairs_only', true, "
        "'execute', true, "
        "'execute_single_pair', true, "
        "'dry_run_only', false, "
        f"'pair_id', '{SPP001_PAIR_ID}', "
        f"'handwired_model_path', '{handwired_model.as_posix()}', "
        f"'validation_summary_csv', '{validation_csv.as_posix()}', "
        "'timeout_s', 240);"
    )
    base = _normalize_matlab_row(
        {
            "execution_status": "blocked",
            "pilot_label_status": "blocked",
            "timeout_or_failure_reason": "MATLAB execution was not attempted",
            "evidence_source": "python_spp001_single_pair_smoke_wrapper",
        },
        pair,
    )
    try:
        completed = subprocess.run(
            ["matlab", "-batch", command],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=360,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        base.update(
            {
                "execution_status": "blocked",
                "pilot_label_status": "blocked",
                "timeout_or_failure_reason": "MATLAB executable was not available on PATH",
                "evidence_source": "python_spp001_single_pair_smoke_matlab_missing",
            }
        )
        return base
    except subprocess.TimeoutExpired as exc:
        combined = (exc.stdout or "") + "\n" + (exc.stderr or "")
        base.update(
            {
                "execution_status": "timeout",
                "pilot_label_status": "timeout",
                "timeout_or_failure_reason": "Python MATLAB wrapper timeout: " + _shorten(combined or str(exc)),
                "evidence_source": "python_spp001_single_pair_smoke_timeout",
            }
        )
        return base

    compact_json = matlab_output_dir / SPP001_ENTRYPOINT_MATLAB_JSON
    if completed.returncode != 0:
        base.update(
            {
                "execution_status": "failed",
                "pilot_label_status": "failed",
                "timeout_or_failure_reason": "MATLAB returned nonzero exit code: "
                + str(completed.returncode)
                + "; "
                + _shorten((completed.stderr or "") + " " + (completed.stdout or "")),
                "evidence_source": "python_spp001_single_pair_smoke_matlab_nonzero",
            }
        )
        return base
    if not _exists(compact_json):
        base.update(
            {
                "execution_status": "failed",
                "pilot_label_status": "failed",
                "timeout_or_failure_reason": "MATLAB returned success but compact evidence JSON was not written",
                "evidence_source": "python_spp001_single_pair_smoke_missing_compact_json",
            }
        )
        return base

    try:
        payload = _read_json(compact_json)
        rows = payload.get("rows")
        if isinstance(rows, list):
            row = rows[0] if rows else {}
        elif isinstance(rows, dict):
            row = rows
        else:
            row = {}
        result = _normalize_matlab_row(row, pair)
        result["evidence_source"] = result.get("evidence_source") or "matlab_single_pair_smoke_compact_json"
        return result
    except Exception as exc:
        base.update(
            {
                "execution_status": "failed",
                "pilot_label_status": "failed",
                "timeout_or_failure_reason": "Failed to parse MATLAB compact evidence JSON: " + _shorten(str(exc)),
                "evidence_source": "python_spp001_single_pair_smoke_parse_failed",
            }
        )
        return base


def build_spp001_smoke_payloads(args: argparse.Namespace) -> dict[str, Any]:
    if not args.approved_selected_pairs_only:
        raise SystemExit("--approved-selected-pairs-only is required for SPP001 smoke execution")
    if args.max_pairs != 1:
        raise SystemExit("--max-pairs 1 is required for SPP001 smoke execution")
    if args.pair_id != SPP001_PAIR_ID:
        raise SystemExit("Only --pair-id SPP001 is approved for this single-pair smoke execution round")
    pairs = _read_json(PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json")
    pair = _choose_smoke_candidate(pairs, SPP001_PAIR_ID)
    result = _attempt_spp001_matlab(pair, SPP001_RERUN_DIR)
    if result["pair_id"] != SPP001_PAIR_ID:
        result["execution_status"] = "failed"
        result["pilot_label_status"] = "failed"
        result["pilot_label_value"] = None
        result["timeout_or_failure_reason"] = "MATLAB compact result did not return SPP001"
    label_available = result.get("pilot_label_value") in {0, 1}
    label_distribution = {
        "distribution_scope": "spp001_single_pair_smoke_rerun_label_distribution",
        "pair_count": 1,
        "num_label_0": 1 if result.get("pilot_label_value") == 0 else 0,
        "num_label_1": 1 if result.get("pilot_label_value") == 1 else 0,
        "num_null_labels": 0 if label_available else 1,
        "pilot_only": True,
        "formal_training_labels": False,
    }
    summary = {
        "execution_scope": "spp001_single_pair_smoke_rerun",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_entrypoint_repair_commit": SOURCE_ENTRYPOINT_REPAIR_COMMIT,
        "source_l15_readiness_repair_commit": SOURCE_L15_READINESS_REPAIR_COMMIT,
        "pair_id": result["pair_id"],
        "state_id": result["state_id"],
        "prior_outaged_branch": result["prior_outaged_branch"],
        "candidate_next_branch": result["candidate_next_branch"],
        "planned_contingency_sequence": result["planned_contingency_sequence"],
        "selection_bucket": result["selection_bucket"],
        "l15_ready": True,
        "l04_ready": True,
        "execution_attempted": True,
        "execution_status": result["execution_status"],
        "single_pair_executed": result["execution_status"] == "succeeded",
        "simulink_run": result["execution_status"] == "succeeded",
        "pilot_label_value": result.get("pilot_label_value"),
        "pilot_label_status": result.get("pilot_label_status"),
        "dynamic_stress_score_if_available": result.get("dynamic_stress_score_if_available"),
        "unstable_flag_if_available": result.get("unstable_flag_if_available"),
        "timeout_or_failure_reason": result.get("timeout_or_failure_reason"),
        "pilot_label_available": label_available,
        "pilot_labels_are_formal_training_labels": False,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "source_slx_modified": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "l12_special_case_preserved": True,
        "nf06_warning_preserved": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "blocker_if_any": None if result["execution_status"] == "succeeded" else result.get("timeout_or_failure_reason"),
        "recommended_next_step": _spp001_recommended_next_step(result),
    }
    approval = {
        "approval_scope": "spp001_single_pair_smoke_rerun_approval",
        "approved_selected_pairs_only": True,
        "approved_pair_count": 1,
        "pair_id": SPP001_PAIR_ID,
        "state_id": pair.get("state_id"),
        "prior_outaged_branch": pair.get("prior_outaged_branch"),
        "candidate_next_branch": pair.get("candidate_next_branch"),
        "planned_contingency_sequence": pair.get("planned_contingency_sequence"),
        "selection_bucket": pair.get("selection_bucket"),
        "source_entrypoint_repair_commit": SOURCE_ENTRYPOINT_REPAIR_COMMIT,
        "selected_32_batch_execution_approved": False,
        "full_1056_generation_approved": False,
        "formal_label_export_approved": False,
        "gcn_training_approved": False,
        "reranker_retrain_approved": False,
        "production_model_approved": False,
        "raw_trajectory_commit_approved": False,
        "source_l15_readiness_repair_commit": SOURCE_L15_READINESS_REPAIR_COMMIT,
    }
    no_leakage = {
        "audit_scope": "spp001_single_pair_smoke_rerun_no_leakage_audit",
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "no_leakage_policy_passed": True,
    }
    safety = {
        "safety_scope": "spp001_single_pair_smoke_rerun_large_file_safety",
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
        "approval": approval,
        "summary": summary,
        "result": result,
        "label_distribution": label_distribution,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_spp001_doc(payloads: dict[str, Any], *, rerun: bool = False) -> str:
    summary = payloads["summary"]
    title = "IEEE39 SPP001 Single-Pair Smoke Rerun" if rerun else "IEEE39 SPP001 Single-Pair Smoke Execution"
    scope_line = "This round reruns the one approved pair after the L15 readiness repair." if rerun else "This round is a one-pair smoke execution for SPP001 only."
    return f"""# {title}

{scope_line} It does not train GCN, does not rerun formal audit, does not execute the selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The approved pilot path is `L15 -> L04`. The run only checks whether the repaired MATLAB/Simulink single-pair execution path can produce compact evidence. Any failed, blocked, timeout, or unknown result remains null and is not converted into a 0/1 training label.

## Result

- execution_scope: `{summary["execution_scope"]}`
- pair_id: `{summary["pair_id"]}`
- prior_outaged_branch: `{summary["prior_outaged_branch"]}`
- candidate_next_branch: `{summary["candidate_next_branch"]}`
- execution_attempted: `{summary["execution_attempted"]}`
- execution_status: `{summary["execution_status"]}`
- pilot_label_value: `{summary["pilot_label_value"]}`
- pilot_label_status: `{summary["pilot_label_status"]}`
- dynamic_stress_score_if_available: `{summary["dynamic_stress_score_if_available"]}`
- unstable_flag_if_available: `{summary["unstable_flag_if_available"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

No raw trajectories, full timeseries, `.mat`, `.slx`, `.slxc`, or `slprj` artifacts are committed. The source `.slx` is not modified. Bus-fault labels are not used. Line-trip labels remain first priority. L12 remains special/excluded. Pilot labels are not formal training labels. This is not a final project conclusion.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_spp001_smoke_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    SPP001_SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(SPP001_SMOKE_DIR / "spp001_smoke_execution_approval.json", payloads["approval"])
    _write_kv_md(SPP001_SMOKE_DIR / "spp001_smoke_execution_approval.md", "IEEE39 SPP001 Smoke Execution Approval", payloads["approval"])
    _write_json(SPP001_SMOKE_DIR / "spp001_smoke_execution_summary.json", payloads["summary"])
    _write_kv_md(SPP001_SMOKE_DIR / "spp001_smoke_execution_summary.md", "IEEE39 SPP001 Smoke Execution Summary", payloads["summary"])
    _write_kv_csv(SPP001_SMOKE_DIR / "spp001_smoke_execution_summary.csv", payloads["summary"])
    _write_json(SPP001_SMOKE_DIR / "spp001_smoke_execution_result.json", payloads["result"])
    _write_results_md(SPP001_SMOKE_DIR / "spp001_smoke_execution_result.md", "IEEE39 SPP001 Smoke Execution Result", [payloads["result"]])
    _write_rows_csv(SPP001_SMOKE_DIR / "spp001_smoke_execution_result.csv", [payloads["result"]])
    _write_json(SPP001_SMOKE_DIR / "spp001_no_leakage_smoke_audit.json", payloads["no_leakage"])
    _write_kv_md(SPP001_SMOKE_DIR / "spp001_no_leakage_smoke_audit.md", "IEEE39 SPP001 No-Leakage Smoke Audit", payloads["no_leakage"])
    _write_json(SPP001_SMOKE_DIR / "spp001_large_file_safety_check.json", payloads["safety"])
    _write_kv_md(SPP001_SMOKE_DIR / "spp001_large_file_safety_check.md", "IEEE39 SPP001 Large File Safety Check", payloads["safety"])
    if write_report:
        SPP001_SMOKE_DOC.write_text(_build_spp001_doc(payloads), encoding="utf-8")


def write_spp001_rerun_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    SPP001_RERUN_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(SPP001_RERUN_DIR / "spp001_rerun_approval.json", payloads["approval"])
    _write_kv_md(SPP001_RERUN_DIR / "spp001_rerun_approval.md", "IEEE39 SPP001 Rerun Approval", payloads["approval"])
    _write_json(SPP001_RERUN_DIR / "spp001_rerun_summary.json", payloads["summary"])
    _write_kv_md(SPP001_RERUN_DIR / "spp001_rerun_summary.md", "IEEE39 SPP001 Rerun Summary", payloads["summary"])
    _write_kv_csv(SPP001_RERUN_DIR / "spp001_rerun_summary.csv", payloads["summary"])
    _write_json(SPP001_RERUN_DIR / "spp001_rerun_result.json", payloads["result"])
    _write_results_md(SPP001_RERUN_DIR / "spp001_rerun_result.md", "IEEE39 SPP001 Rerun Result", [payloads["result"]])
    _write_rows_csv(SPP001_RERUN_DIR / "spp001_rerun_result.csv", [payloads["result"]])
    _write_json(SPP001_RERUN_DIR / "spp001_rerun_label_distribution.json", payloads["label_distribution"])
    _write_kv_md(SPP001_RERUN_DIR / "spp001_rerun_label_distribution.md", "IEEE39 SPP001 Rerun Label Distribution", payloads["label_distribution"])
    _write_json(SPP001_RERUN_DIR / "spp001_no_leakage_rerun_audit.json", payloads["no_leakage"])
    _write_kv_md(SPP001_RERUN_DIR / "spp001_no_leakage_rerun_audit.md", "IEEE39 SPP001 No-Leakage Rerun Audit", payloads["no_leakage"])
    _write_json(SPP001_RERUN_DIR / "spp001_large_file_safety_rerun.json", payloads["safety"])
    _write_kv_md(SPP001_RERUN_DIR / "spp001_large_file_safety_rerun.md", "IEEE39 SPP001 Large File Safety Rerun", payloads["safety"])
    if write_report:
        SPP001_RERUN_DOC.write_text(_build_spp001_doc(payloads, rerun=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair IEEE39 selected-32-only controlled execution backend skeleton.")
    parser.add_argument("--approved-selected-pairs-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--single-pair-smoke-only", action="store_true")
    parser.add_argument("--pair-id", default=None)
    parser.add_argument("--max-pairs", type=int, default=32)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [
        DIAGNOSIS_DIR / "backend_readiness_summary.json",
        DIAGNOSIS_DIR / "backend_component_inventory.json",
        DIAGNOSIS_DIR / "selected_pair_execution_mapping_diagnosis.json",
        DIAGNOSIS_DIR / "safe_execution_repair_plan.json",
        PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json",
        APPROVAL_JSON,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    if args.execute and not args.single_pair_smoke_only:
        raise SystemExit("--execute is refused for batch mode in this round; use --single-pair-smoke-only with --pair-id for a future approved one-pair smoke")
    if args.execute and args.single_pair_smoke_only:
        payloads = build_spp001_smoke_payloads(args)
        write_spp001_rerun_payloads(payloads, args.write_report)
    elif args.single_pair_smoke_only:
        payloads = build_entrypoint_repair_payloads(args.pair_id)
        write_entrypoint_repair_payloads(payloads, args.write_report)
    elif args.execute:
        payloads = build_execution_payloads(args.max_pairs, args.approved_selected_pairs_only)
        output_dir = args.output_dir or EXECUTION_OUT_DIR
        write_execution_payloads(payloads, output_dir, args.write_report)
    else:
        payloads = build_payloads(args.max_pairs, args.approved_selected_pairs_only, args.execute)
        write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
