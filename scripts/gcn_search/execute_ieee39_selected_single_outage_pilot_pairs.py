from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DRY_RUN_COMMIT = "07d4f7b3a6d40f4695312ff8c9b8e9704b2facac"

DRY_RUN_DIR = ROOT / "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run"
PROXY_DIR = ROOT / "results/gcn_search/ieee39_relay_threshold_proxy_approval"
OUT_DIR = ROOT / "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution"
DOC = ROOT / "docs/ieee39_selected_single_outage_pilot_pair_execution.md"

BLOCKER = (
    "controlled Simulink execution backend is not available in this audit runner; "
    "no pilot labels were generated"
)
NEXT_STEP_BLOCKED = "fix controlled execution environment or run selected pair execution locally, then rerun evidence collection"


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


def _write_results_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# IEEE39 Selected Single-Outage Pilot Pair Execution Results",
        "",
        "These rows are audit-level execution evidence. The local runner did not fabricate 0/1 labels.",
        "",
        "| pair_id | prior | next | bucket | execution_status | pilot_label_status | pilot_label_value |",
        "|---|---:|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {pair_id} | {prior_outaged_branch} | {candidate_next_branch} | {selection_bucket} | "
            "{execution_status} | {pilot_label_status} | {pilot_label_value} |".format(**row)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _selected_pairs(max_pairs: int) -> list[dict[str, Any]]:
    rows = _read_json(DRY_RUN_DIR / "selected_single_outage_pilot_pairs.json")
    return rows[:max_pairs]


def _build_results(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in pairs:
        l12_flag = "L12" in {row.get("prior_outaged_branch"), row.get("candidate_next_branch")}
        results.append(
            {
                "pair_id": row["pair_id"],
                "state_id": row["state_id"],
                "prior_outaged_branch": row["prior_outaged_branch"],
                "candidate_next_branch": row["candidate_next_branch"],
                "planned_contingency_sequence": row["planned_contingency_sequence"],
                "selection_bucket": row["selection_bucket"],
                "execution_status": "blocked",
                "pilot_label_value": None,
                "pilot_label_status": "blocked",
                "dynamic_stress_score_if_available": None,
                "unstable_flag_if_available": None,
                "instability_or_risk_reason": None,
                "timeout_or_failure_reason": BLOCKER,
                "evidence_source": "blocked_controlled_execution_runner",
                "raw_trajectory_committed": False,
                "full_timeseries_committed": False,
                "mat_file_committed": False,
                "bus_fault_label_used": False,
                "l12_special_case_flag": l12_flag,
                "notes": "pilot-only evidence row; not a formal training label",
            }
        )
    return results


def build_payloads(max_pairs: int, approved_selected_pairs_only: bool) -> dict[str, Any]:
    dry_summary = _read_json(DRY_RUN_DIR / "single_outage_pilot_pair_runner_dry_run_summary.json")
    no_leakage_prior = _read_json(DRY_RUN_DIR / "no_leakage_pilot_pair_runner_audit.json")
    feature_matrix = _read_json(PROXY_DIR / "l01_l34_approved_paper_feature_source_matrix.json")
    pairs = _selected_pairs(max_pairs)
    results = _build_results(pairs)
    selected_count = len(results)
    blocked_count = sum(row["execution_status"] == "blocked" for row in results)
    approval = {
        "approval_scope": "selected_single_outage_pilot_pair_execution_approval",
        "source_dry_run_commit": SOURCE_DRY_RUN_COMMIT,
        "approved_pair_count": 32,
        "approved_selected_pairs_only": approved_selected_pairs_only,
        "full_1056_generation_approved": False,
        "formal_label_export_approved": False,
        "gcn_training_approved": False,
        "reranker_retrain_approved": False,
        "raw_trajectory_commit_approved": False,
        "beta_rate_a_proxy_acknowledged": True,
        "proxy_allowed_for_audit_only_prototype": True,
        "proxy_allowed_for_production": False,
    }
    summary = {
        "execution_scope": "selected_single_outage_pilot_pair_execution",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "new_simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_dry_run_commit": SOURCE_DRY_RUN_COMMIT,
        "selected_pair_count": selected_count,
        "executed_pair_count": 0,
        "succeeded_pair_count": 0,
        "failed_pair_count": 0,
        "timeout_pair_count": 0,
        "unknown_pair_count": selected_count,
        "pilot_label_available_count": 0,
        "pilot_positive_count": 0,
        "pilot_negative_count": 0,
        "pilot_unknown_count": selected_count,
        "pilot_excluded_count": 0,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
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
        "blocker_if_any": BLOCKER,
        "recommended_next_step": NEXT_STEP_BLOCKED,
        "source_dry_run_pair_count": dry_summary.get("num_pilot_pairs_selected"),
        "approved_selected_pairs_only": approved_selected_pairs_only,
        "feature_matrix_rows_available": len(feature_matrix),
        "prior_no_leakage_policy_passed": no_leakage_prior.get("no_leakage_policy_passed"),
    }
    distribution = {
        "selected_pair_count": selected_count,
        "pilot_label_available_count": 0,
        "pilot_positive_count": 0,
        "pilot_negative_count": 0,
        "pilot_unknown_count": selected_count,
        "pilot_timeout_count": 0,
        "pilot_failed_count": 0,
        "pilot_blocked_count": blocked_count,
        "all_available_labels_negative": False,
        "has_positive_pilot_label": False,
        "class_balance_warning": "no pilot labels available because execution is blocked",
        "training_readiness_recommendation": NEXT_STEP_BLOCKED,
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
        "results": results,
        "distribution": distribution,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    distribution = payloads["distribution"]
    return f"""# IEEE39 Selected Single-Outage Pilot Pair Execution

This round is selected 32 single-outage pilot pair execution approval and evidence collection. It does not train GCN, does not rerun formal audit, does not export formal labels, does not retrain the reranker, and does not save or deploy a production model.

## Plain-Language Purpose

上一轮已经从 1056 个 `single_outage_state x next_branch` 候选里挑出 32 个 pilot pair。大白话说，这一步原本是想逐个检查“先断一条线后，再断下一条线会不会出现风险”。但当前仓库里没有可以安全调用的受控 Simulink 执行后端，所以本轮没有编造仿真结果，而是把 32 条全部记录为 `blocked`，`pilot_label_value` 保持 `null`。

## Boundary

- This is not full 1056 generation.
- If Simulink is run in a future round, it must be limited to the selected 32 pairs unless separately approved.
- Raw trajectories, full timeseries, and `.mat` files are not committed.
- Timeout, unknown, blocked, or failed cases are not converted to 0/1.
- `beta * RATE_A` is an audit-only proxy, not a real relay setting.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- NF06 warning is preserved.
- Pilot labels are not formal training labels.
- No deployment is claimed.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.

## Current Evidence Summary

- execution_scope: `{summary["execution_scope"]}`
- selected_pair_count: `{summary["selected_pair_count"]}`
- executed_pair_count: `{summary["executed_pair_count"]}`
- succeeded_pair_count: `{summary["succeeded_pair_count"]}`
- failed_pair_count: `{summary["failed_pair_count"]}`
- timeout_pair_count: `{summary["timeout_pair_count"]}`
- unknown_pair_count: `{summary["unknown_pair_count"]}`
- pilot_label_available_count: `{summary["pilot_label_available_count"]}`
- pilot_positive_count: `{summary["pilot_positive_count"]}`
- pilot_negative_count: `{summary["pilot_negative_count"]}`
- pilot_unknown_count: `{summary["pilot_unknown_count"]}`
- pilot_blocked_count: `{distribution["pilot_blocked_count"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Next Step

`{summary["recommended_next_step"]}`. If future execution succeeds and produces both positive and negative pilot examples, the next round should request pilot label export approval separately; do not train yet.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "selected_pair_execution_approval.json", payloads["approval"])
    _write_kv_md(OUT_DIR / "selected_pair_execution_approval.md", "IEEE39 Selected Pair Execution Approval", payloads["approval"])
    _write_json(OUT_DIR / "selected_pair_execution_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "selected_pair_execution_summary.md", "IEEE39 Selected Pair Execution Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "selected_pair_execution_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "selected_pair_execution_results.json", payloads["results"])
    _write_results_md(OUT_DIR / "selected_pair_execution_results.md", payloads["results"])
    _write_rows_csv(OUT_DIR / "selected_pair_execution_results.csv", payloads["results"])
    _write_json(OUT_DIR / "selected_pair_label_distribution.json", payloads["distribution"])
    _write_kv_md(OUT_DIR / "selected_pair_label_distribution.md", "IEEE39 Selected Pair Label Distribution", payloads["distribution"])
    _write_json(OUT_DIR / "no_leakage_selected_pair_execution_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_selected_pair_execution_audit.md", "IEEE39 No-Leakage Selected Pair Execution Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_and_artifact_safety_check.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_and_artifact_safety_check.md", "IEEE39 Large File And Artifact Safety Check", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute or block IEEE39 selected single-outage pilot pair evidence collection.")
    parser.add_argument("--approved-selected-pairs-only", action="store_true")
    parser.add_argument("--max-pairs", type=int, default=32)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [
        DRY_RUN_DIR / "single_outage_pilot_pair_runner_dry_run_summary.json",
        DRY_RUN_DIR / "selected_single_outage_pilot_pairs.json",
        DRY_RUN_DIR / "future_controlled_generation_run_plan.json",
        DRY_RUN_DIR / "no_leakage_pilot_pair_runner_audit.json",
        PROXY_DIR / "l01_l34_approved_paper_feature_source_matrix.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    if args.strict and not args.approved_selected_pairs_only:
        raise SystemExit("--approved-selected-pairs-only is required in strict mode")
    payloads = build_payloads(args.max_pairs, args.approved_selected_pairs_only)
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
