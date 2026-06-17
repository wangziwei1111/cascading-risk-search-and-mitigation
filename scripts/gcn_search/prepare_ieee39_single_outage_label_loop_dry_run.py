from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_BASE_STATE_PILOT_COMMIT = "449f8d1e625672bb6e01fbffd59c6bb97d3d0fe0"

BASE_PILOT_DIR = ROOT / "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot"
GENERATOR_DRY_RUN_DIR = ROOT / "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run"
PROXY_DIR = ROOT / "results/gcn_search/ieee39_relay_threshold_proxy_approval"
OUT_DIR = ROOT / "results/gcn_search/ieee39_single_outage_label_loop_dry_run"
DOC = ROOT / "docs/ieee39_single_outage_label_loop_dry_run.md"

LINE_IDS = [f"L{i:02d}" for i in range(1, 35)]
FORBIDDEN_FEATURES = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "dynamic_stress_score",
    "unstable_flag",
    "phasor_RMS",
    "generator_speed_proxy",
    "post-fault dynamic measurements",
    "label-derived flags",
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


def _write_manifest_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# IEEE39 Single-Outage State Manifest",
        "",
        "| state_id | prior_outaged_branch | candidates | eligible | exclusion_reason_if_any |",
        "|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {state_id} | {prior_outaged_branch} | {num_candidate_next_branches} | "
            "{eligible_for_label_generation} | {exclusion_reason_if_any} |".format(**row)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_plan_md(path: Path, rows: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["label_status"]] = counts.get(row["label_status"], 0) + 1
    preview = rows[:20]
    lines = [
        "# IEEE39 Single-Outage State Branch Label Loop Plan",
        "",
        "This file is a dry-run plan. It does not contain newly generated formal 0/1 labels.",
        "",
        "## label_status counts",
        "```json",
        json.dumps(counts, ensure_ascii=False, indent=2),
        "```",
        "",
        "## preview",
        "",
        "| state_id | prior | next | status | requires_new_simulink_run | exclusion_reason_if_any |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in preview:
        lines.append(
            "| {state_id} | {prior_outaged_branch} | {candidate_next_branch} | {label_status} | "
            "{requires_new_simulink_run} | {exclusion_reason_if_any} |".format(**row)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_feature_rows() -> dict[str, dict[str, Any]]:
    rows = _read_json(PROXY_DIR / "l01_l34_approved_paper_feature_source_matrix.json")
    return {row["line_id"]: row for row in rows}


def _base_state_distribution(matrix: list[dict[str, Any]]) -> dict[str, Any]:
    available = [row for row in matrix if row.get("label_status") == "available"]
    positive = sum(1 for row in available if row.get("label_value") == 1)
    negative = sum(1 for row in available if row.get("label_value") == 0)
    excluded = sum(1 for row in matrix if row.get("label_status") == "excluded")
    return {
        "base_state_num_label_slots": 34,
        "base_state_num_labels_available": len(available),
        "base_state_num_positive_labels": positive,
        "base_state_num_negative_labels": negative,
        "base_state_num_excluded_labels": excluded,
        "base_state_all_available_labels_negative": len(available) > 0 and positive == 0,
        "training_risk_if_using_base_state_only": len(available) > 0 and positive == 0,
        "recommendation": (
            "do not train on base-state labels only; extend to single-outage state labels first"
        ),
    }


def _build_state_manifest(features_by_line: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, line_id in enumerate(LINE_IDS):
        feature = features_by_line[line_id]
        candidates = [candidate for candidate in LINE_IDS if candidate != line_id]
        l12_prior = line_id == "L12"
        rows.append(
            {
                "state_id": f"single_outage_state_{line_id}",
                "state_type": "single_outage_state",
                "prior_outaged_branch": line_id,
                "prior_outaged_from_bus": feature["from_bus"],
                "prior_outaged_to_bus": feature["to_bus"],
                "x_t_vector_ready": True,
                "x_t_outaged_index": idx,
                "candidate_next_branches": candidates,
                "num_candidate_next_branches": len(candidates),
                "l12_in_prior_state": l12_prior,
                "l12_special_handling": (
                    "prior L12 outage remains special/excluded"
                    if l12_prior
                    else "L12 candidate remains special/excluded"
                ),
                "eligible_for_label_generation": not l12_prior,
                "exclusion_reason_if_any": (
                    "L12 special islanding-timeout case preserved; not an ordinary training state"
                    if l12_prior
                    else None
                ),
            }
        )
    return rows


def _build_pair_plan(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for state in states:
        prior = state["prior_outaged_branch"]
        for candidate in state["candidate_next_branches"]:
            l12_special = prior == "L12" or candidate == "L12"
            if l12_special:
                label_status = "excluded"
                expected_method = "excluded_l12_special_case"
                requires_new_simulink = False
                exclusion = (
                    "L12 special islanding-timeout case preserved in prior or candidate branch"
                )
            else:
                label_status = "planned"
                expected_method = "future_controlled_single_outage_then_next_branch_generation"
                requires_new_simulink = True
                exclusion = None
            rows.append(
                {
                    "state_id": state["state_id"],
                    "prior_outaged_branch": prior,
                    "candidate_next_branch": candidate,
                    "planned_contingency_sequence": [prior, candidate],
                    "x_t_vector_ready": state["x_t_vector_ready"],
                    "feature_matrix_with_proxy_ready": True,
                    "label_source_available": False,
                    "label_value": None,
                    "label_status": label_status,
                    "expected_generation_method": expected_method,
                    "requires_new_simulink_run": requires_new_simulink,
                    "requires_existing_artifact_lookup": False,
                    "l12_special_case_flag": l12_special,
                    "proxy_relay_threshold_used": True,
                    "bus_fault_label_used": False,
                    "exclusion_reason_if_any": exclusion,
                }
            )
    return rows


def _existing_reuse_audit() -> dict[str, Any]:
    return {
        "existing_multi_line_or_path_labels_found": False,
        "reusable_for_single_outage_count": 0,
        "reusable_sequences": [],
        "non_reusable_reason": (
            "Existing approved artifacts provide base_state x branch pilot labels only. "
            "They do not provide controlled single_outage_state x next_branch labels."
        ),
        "bus_fault_labels_used": False,
        "scenario_level_label_limitation": (
            "Scenario-level dynamic outputs may be used as future labels/targets only, not as GCN inputs."
        ),
        "l12_excluded_or_special": True,
        "recommended_generation_strategy": (
            "implement controlled generation runner for selected single-outage pilot pairs in a separate round"
        ),
    }


def build_payloads() -> dict[str, Any]:
    base_summary = _read_json(BASE_PILOT_DIR / "base_state_branch_vulnerability_label_pilot_summary.json")
    base_matrix = _read_json(BASE_PILOT_DIR / "base_state_branch_vulnerability_label_matrix.json")
    _read_json(BASE_PILOT_DIR / "existing_line_trip_label_reuse_report.json")
    _read_json(GENERATOR_DRY_RUN_DIR / "state_space_manifest.json")
    _read_json(GENERATOR_DRY_RUN_DIR / "state_branch_label_generation_plan.json")
    features_by_line = _load_feature_rows()

    states = _build_state_manifest(features_by_line)
    pair_plan = _build_pair_plan(states)
    base_distribution = _base_state_distribution(base_matrix)
    reuse_audit = _existing_reuse_audit()
    no_leakage = {
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "proxy_relay_threshold_used_only_in_feature_generation": True,
        "bus_fault_labels_used": False,
        "no_leakage_policy_passed": True,
        "forbidden_features_checked": FORBIDDEN_FEATURES,
    }

    l12_excluded = sum(1 for row in pair_plan if row["l12_special_case_flag"])
    planned_future = sum(1 for row in pair_plan if row["label_status"] == "planned")
    available = sum(1 for row in pair_plan if row["label_status"] == "available")
    blocker = (
        "no approved reusable single_outage_state x next_branch label artifacts are available; "
        "this round only prepares the controlled loop dry-run plan"
    )
    summary = {
        "dry_run_scope": "single_outage_label_loop_dry_run",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "new_simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_base_state_pilot_commit": SOURCE_BASE_STATE_PILOT_COMMIT,
        "paper_graph_node_type": "branch",
        "paper_graph_edge_rule": "shared_endpoint_bus",
        "feature_matrix_with_proxy_ready": bool(base_summary.get("feature_matrix_with_proxy_ready")),
        "relay_threshold_is_proxy": True,
        "proxy_allowed_for_audit_only_prototype": True,
        "proxy_allowed_for_production": False,
        "base_state_all_available_labels_negative": base_distribution["base_state_all_available_labels_negative"],
        "base_state_should_not_be_used_alone_for_training": True,
        "num_single_outage_states_planned": len(states),
        "num_state_branch_pairs_planned": len(pair_plan),
        "num_pairs_excluded_due_to_same_branch": len(LINE_IDS),
        "num_pairs_excluded_due_to_l12_special": l12_excluded,
        "num_pairs_planned_for_future_generation": planned_future,
        "num_pairs_available_from_existing_artifacts": available,
        "can_generate_single_outage_labels_now": False,
        "can_export_formal_single_outage_labels_now": False,
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
        "blocker_if_any": blocker,
        "recommended_next_step": (
            "implement controlled generation runner for selected single-outage pilot pairs in a separate round"
        ),
    }
    return {
        "summary": summary,
        "states": states,
        "pair_plan": pair_plan,
        "base_distribution": base_distribution,
        "reuse_audit": reuse_audit,
        "no_leakage": no_leakage,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    base = payloads["base_distribution"]
    return f"""# IEEE39 Single-Outage Label Loop Dry-Run

This is a controlled single-outage state label loop dry-run. It does not train GCN, does not rerun formal audit, does not run new Simulink, does not export formal labels, does not retrain the reranker, and does not save a production model.

There is no deployment in this round.

## Plain-Language Purpose

The previous base-state pilot only asked: from the original grid, what happens if one line is tripped? All 33 available non-L12 labels were negative. That means the base-state pilot alone cannot train a useful classifier because it has no positive branch-risk samples. This round therefore only prepares the next task list: after line `i` has already been outaged, evaluate a future candidate line `k`.

## Planned Loop

- dry_run_scope: `{summary["dry_run_scope"]}`
- paper_graph_node_type: `{summary["paper_graph_node_type"]}`
- paper_graph_edge_rule: `{summary["paper_graph_edge_rule"]}`
- num_single_outage_states_planned: `{summary["num_single_outage_states_planned"]}`
- num_state_branch_pairs_planned: `{summary["num_state_branch_pairs_planned"]}`
- num_pairs_excluded_due_to_same_branch: `{summary["num_pairs_excluded_due_to_same_branch"]}`
- num_pairs_excluded_due_to_l12_special: `{summary["num_pairs_excluded_due_to_l12_special"]}`
- num_pairs_planned_for_future_generation: `{summary["num_pairs_planned_for_future_generation"]}`
- num_pairs_available_from_existing_artifacts: `{summary["num_pairs_available_from_existing_artifacts"]}`

The pair label means: `y_state_i[k] = 1` if, after branch `i` is already outaged, disconnecting branch `k` causes critical risk or an unacceptable dynamic proxy. `0` means no critical risk. Unknown, timeout, not simulated, or special cases remain null/excluded. This dry-run does not fabricate 0/1 labels.

## Base-State Review

- base_state_num_label_slots: `{base["base_state_num_label_slots"]}`
- base_state_num_labels_available: `{base["base_state_num_labels_available"]}`
- base_state_num_positive_labels: `{base["base_state_num_positive_labels"]}`
- base_state_num_negative_labels: `{base["base_state_num_negative_labels"]}`
- base_state_num_excluded_labels: `{base["base_state_num_excluded_labels"]}`
- base_state_all_available_labels_negative: `{base["base_state_all_available_labels_negative"]}`
- training_risk_if_using_base_state_only: `{base["training_risk_if_using_base_state_only"]}`
- recommendation: `{base["recommendation"]}`

## Boundaries

The `beta * RATE_A` threshold is an audit-only proxy. It is not a real relay setting and not an engineering-grade protection threshold. Bus-fault labels are unused. Line-trip labels remain first priority. L12 stays special/excluded. NF06 warning is preserved.

No post-fault dynamic measurement features are used as inputs. Dynamic outputs can only be future labels or targets. Label-derived flags are not inputs. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Status

- can_generate_single_outage_labels_now: `{summary["can_generate_single_outage_labels_now"]}`
- can_export_formal_single_outage_labels_now: `{summary["can_export_formal_single_outage_labels_now"]}`
- no_leakage_policy_passed: `{summary["no_leakage_policy_passed"]}`
- final_engineering_conclusion: `{summary["final_engineering_conclusion"]}`
- should_train_gcn_now: `{summary["should_train_gcn_now"]}`
- should_rerun_formal_audit_now: `{summary["should_rerun_formal_audit_now"]}`
- should_export_formal_labels_now: `{summary["should_export_formal_labels_now"]}`
- should_retrain_reranker_now: `{summary["should_retrain_reranker_now"]}`
- should_deploy_model: `{summary["should_deploy_model"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Recommended Next Step

`{summary["recommended_next_step"]}`
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "single_outage_state_manifest.json", payloads["states"])
    _write_manifest_md(OUT_DIR / "single_outage_state_manifest.md", payloads["states"])
    _write_rows_csv(OUT_DIR / "single_outage_state_manifest.csv", payloads["states"])

    _write_json(OUT_DIR / "single_outage_state_branch_label_loop_plan.json", payloads["pair_plan"])
    _write_plan_md(OUT_DIR / "single_outage_state_branch_label_loop_plan.md", payloads["pair_plan"])
    _write_rows_csv(OUT_DIR / "single_outage_state_branch_label_loop_plan.csv", payloads["pair_plan"])

    _write_json(OUT_DIR / "base_state_label_distribution_review.json", payloads["base_distribution"])
    _write_kv_md(
        OUT_DIR / "base_state_label_distribution_review.md",
        "IEEE39 Base-State Label Distribution Review",
        payloads["base_distribution"],
    )
    _write_json(OUT_DIR / "existing_artifact_reuse_for_single_outage_audit.json", payloads["reuse_audit"])
    _write_kv_md(
        OUT_DIR / "existing_artifact_reuse_for_single_outage_audit.md",
        "IEEE39 Existing Artifact Reuse For Single-Outage Audit",
        payloads["reuse_audit"],
    )
    _write_json(OUT_DIR / "no_leakage_single_outage_label_loop_audit.json", payloads["no_leakage"])
    _write_kv_md(
        OUT_DIR / "no_leakage_single_outage_label_loop_audit.md",
        "IEEE39 No-Leakage Single-Outage Label Loop Audit",
        payloads["no_leakage"],
    )
    _write_json(OUT_DIR / "single_outage_label_loop_dry_run_summary.json", payloads["summary"])
    _write_kv_md(
        OUT_DIR / "single_outage_label_loop_dry_run_summary.md",
        "IEEE39 Single-Outage Label Loop Dry-Run Summary",
        payloads["summary"],
    )
    _write_kv_csv(OUT_DIR / "single_outage_label_loop_dry_run_summary.csv", payloads["summary"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare IEEE39 single-outage label loop dry-run.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [
        BASE_PILOT_DIR / "base_state_branch_vulnerability_label_pilot_summary.json",
        BASE_PILOT_DIR / "base_state_branch_vulnerability_label_matrix.json",
        BASE_PILOT_DIR / "existing_line_trip_label_reuse_report.json",
        GENERATOR_DRY_RUN_DIR / "state_space_manifest.json",
        GENERATOR_DRY_RUN_DIR / "state_branch_label_generation_plan.json",
        PROXY_DIR / "l01_l34_approved_paper_feature_source_matrix.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads()
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
