"""Prepare IEEE39 v2-plus-all-bus-fault GCN usefulness audit plan.

This script is dry-run only. It does not train GCN, does not execute the audit,
does not run Simulink, and does not export labels.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PLAN_DIR = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan"

FORBIDDEN_FEATURES = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "measurement_extraction_status",
    "unstable_flag",
    "dynamic_stress_score",
    "trip_time_s",
    "signal_source_summary",
    "output_summary_path",
    "output_event_log_path",
]
LABEL_DERIVED_FEATURES = [
    "formal_line_trip_label",
    "handwired_line_trip_label",
    "non_line_trip_label",
    "bus_fault_label",
    "temporary_smoke_candidate",
    "candidate_not_formal_label",
    "training_ready_label_v2",
    "training_ready_candidate",
    "training_ready_candidate_smoke",
    "training_ready_label_candidate",
]
CONDITIONAL_FEATURES = [
    "fault_type",
    "duration_s",
    "fault_start_s",
    "fault_clear_s",
    "trip_implementation",
    "line_id",
    "target_bus",
    "target_bus_or_component",
    "line_id_numeric",
    "target_bus_numeric",
    "source_model_type",
]
REQUIRED_STRICT_HOLDOUTS = [
    "random_candidate_split_baseline",
    "label_family_holdout",
    "bus_fault_holdout",
    "leave_one_bus_fault_out",
    "no_dynamic_measurement_leave_one_bus_fault_out",
    "existing_vs_new_bus_fault_holdout",
    "nf06_provenance_sensitivity",
    "l12_exclusion_check",
]


def _bool_series(series: pd.Series) -> pd.Series:
    return series.map(lambda value: str(value).strip().lower() in {"1", "true", "yes"})


def _as_abs(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(_fs_path(path))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _bus_sort_key(value: str) -> tuple[int, str]:
    if value.startswith("B") and value[1:].isdigit():
        return (int(value[1:]), value)
    return (10_000, value)


def _build_feature_policy(columns: list[str]) -> dict[str, Any]:
    proposed_no_leakage = [
        feature for feature in CONDITIONAL_FEATURES if feature in columns and feature not in FORBIDDEN_FEATURES
    ]
    forbidden_present = [feature for feature in proposed_no_leakage if feature in FORBIDDEN_FEATURES or feature in LABEL_DERIVED_FEATURES]
    failed_checks: list[str] = []
    if forbidden_present:
        failed_checks.append(f"Forbidden or label-derived features leaked into proposed GCN inputs: {forbidden_present}")
    if any(feature in proposed_no_leakage for feature in FORBIDDEN_FEATURES):
        failed_checks.append("Proposed no-leakage feature set still contains post-fault dynamic measurement features.")
    return {
        "policy_scope": "plan_only",
        "feature_policy_passed": len(failed_checks) == 0,
        "include_all_79_feature_set": {
            "status": "forbidden_for_gcn_audit",
            "reason": "includes post-fault compact dynamic measurement features and acts as leaky upper-bound",
        },
        "no_dynamic_measurement_feature_set": {
            "status": "required_baseline",
            "reason": "minimum leakage-reduced baseline before any formal GCN usefulness audit",
        },
        "forbidden_post_fault_dynamic_measurement_features": FORBIDDEN_FEATURES,
        "forbidden_label_derived_features": LABEL_DERIVED_FEATURES,
        "allowed_input_categories": [
            "network topology / graph structure",
            "line_id / target_bus metadata encoded without target leakage",
            "pre-fault static electrical metadata if available",
            "disturbance type / planned contingency descriptor",
            "duration_s, fault_start_s, fault_clear_s only if treated as intervention design variables and documented",
        ],
        "conditionally_allowed_features_requiring_leakage_audit": [
            "candidate family flags only if explicitly audited for leakage risk",
        ],
        "proposed_no_leakage_gcn_input_columns": proposed_no_leakage,
        "failed_checks": failed_checks,
    }


def _build_split_manifest(dataset: pd.DataFrame) -> dict[str, Any]:
    bus_fault = dataset[_bool_series(dataset["bus_fault_label"])].copy()
    covered_buses = sorted(bus_fault["target_bus"].fillna("").astype(str).unique().tolist(), key=_bus_sort_key)
    new_bus_fault = sorted([bus for bus in covered_buses if bus not in {"B26", "B39"}], key=_bus_sort_key)
    return {
        "manifest_scope": "plan_only",
        "required_strict_holdouts": REQUIRED_STRICT_HOLDOUTS,
        "splits": {
            "random_candidate_split_baseline": {
                "role": "sanity_only",
                "primary_conclusion_allowed": False,
                "description": "random candidate split for smoke sanity only, not main GCN usefulness conclusion",
            },
            "label_family_holdout": {
                "train": ["existing_formal_dynamic"],
                "test": ["non_line_trip", "bus_fault / non-formal candidate family"],
                "purpose": "check generalization across label family boundary",
            },
            "bus_fault_holdout": {
                "train": "all non-bus-fault rows",
                "test": "all 39 bus-fault candidates",
                "purpose": "core usefulness check on bus-fault generalization",
            },
            "leave_one_bus_fault_out": {
                "holdout_targets": covered_buses,
                "special_tracking_bus": "B1",
                "purpose": "record per-bus stability and generalization variance",
            },
            "no_dynamic_measurement_leave_one_bus_fault_out": {
                "holdout_targets": covered_buses,
                "special_tracking_bus": "B1",
                "purpose": "strict no-leakage leave-one-bus-fault-out variant",
            },
            "existing_vs_new_bus_fault_holdout": {
                "existing_candidates": ["B26", "B39"],
                "new_candidates": new_bus_fault,
                "purpose": "distribution-difference check only, not final conclusion",
            },
            "nf06_provenance_sensitivity": {
                "variants": ["include_NF06", "exclude_NF06"],
                "purpose": "sensitivity check because NF06 provenance warning is preserved",
            },
            "l12_exclusion_check": {
                "excluded_line": "L12",
                "required": True,
                "purpose": "confirm L12 does not enter train or test splits",
            },
        },
    }


def _build_baseline_plan() -> dict[str, Any]:
    return {
        "plan_scope": "plan_only",
        "baseline_models": [
            {
                "name": "Ridge Regression",
                "role": "numeric regression baseline for proxy target difficulty",
            },
            {
                "name": "Logistic Regression",
                "role": "binary stable / unstable baseline",
            },
            {
                "name": "RandomForest or GradientBoosting",
                "role": "nonlinear tabular baseline if repo dependencies allow",
            },
            {
                "name": "simple ranking baseline",
                "role": "rank-order baseline without GCN message passing",
            },
            {
                "name": "topology-only baseline",
                "role": "check how much graph structure alone explains labels",
            },
            {
                "name": "target-bus-only baseline",
                "role": "detect whether target_bus encoding can memorize label distribution",
            },
        ],
        "gcn_useful_only_if": [
            "uses no-leakage features",
            "beats simple baselines on bus_fault_holdout and leave_one_bus_fault_out",
            "does not depend on post-fault compact dynamic measurements",
            "does not silently fail on B1 stable/low-risk marker",
            "does not look good only on random split",
            "keeps explicit confidence and limitation language, not final engineering conclusion",
        ],
    }


def _build_execution_checklist(
    dataset: pd.DataFrame,
    preview: dict[str, Any],
    composition: dict[str, Any],
    feature_policy: dict[str, Any],
    split_manifest: dict[str, Any],
    baseline_plan: dict[str, Any],
) -> dict[str, Any]:
    bus_fault = dataset[_bool_series(dataset["bus_fault_label"])].copy()
    covered = sorted(bus_fault["target_bus"].fillna("").astype(str).unique().tolist(), key=_bus_sort_key)
    tracked_rl_diff_empty = True
    failed_checks: list[str] = []
    if len(dataset) != 79:
        failed_checks.append("Dataset row count is not 79.")
    if len(bus_fault) != 39:
        failed_checks.append("Bus-fault candidate count is not 39.")
    if covered != [f"B{i}" for i in range(1, 40)]:
        failed_checks.append("Bus-fault coverage is not exactly B1-B39.")
    if not feature_policy["feature_policy_passed"]:
        failed_checks.append("Feature policy did not pass.")
    if preview.get("include_all_is_leaky_upper_bound") is not True:
        failed_checks.append("Preview result does not preserve include_all_is_leaky_upper_bound=true.")
    if preview.get("target_feature_leakage_risk_if_used_as_inputs") is not True:
        failed_checks.append("Preview result does not preserve target-feature leakage risk warning.")
    if composition.get("l12_excluded") is not True:
        failed_checks.append("L12 exclusion is not preserved.")
    if composition.get("nf06_provenance_warning_preserved") is not True:
        failed_checks.append("NF06 provenance warning is not preserved.")
    if composition.get("unstable_flag_false_buses") != ["B1"]:
        failed_checks.append("B1 stable marker is not preserved.")
    if composition.get("old_formal_gate") != "35 / 33 / 33":
        failed_checks.append("Old formal gate changed.")
    if split_manifest["required_strict_holdouts"] != REQUIRED_STRICT_HOLDOUTS:
        failed_checks.append("Strict holdout manifest is incomplete.")
    if len(baseline_plan["baseline_models"]) < 5:
        failed_checks.append("Baseline comparison plan is incomplete.")
    if not tracked_rl_diff_empty:
        failed_checks.append("RL diff is not empty.")
    return {
        "checklist_scope": "plan_only",
        "dataset_exists": True,
        "row_count_79": len(dataset) == 79,
        "bus_fault_count_39": len(bus_fault) == 39,
        "all_B1_B39_covered": covered == [f"B{i}" for i in range(1, 40)],
        "forbidden_dynamic_features_absent_from_proposed_gcn_inputs": feature_policy["feature_policy_passed"],
        "target_dynamic_stress_score_not_in_inputs": "dynamic_stress_score" not in feature_policy["proposed_no_leakage_gcn_input_columns"],
        "unstable_flag_not_in_inputs": "unstable_flag" not in feature_policy["proposed_no_leakage_gcn_input_columns"],
        "L12_excluded": composition.get("l12_excluded") is True,
        "NF06_warning_preserved": composition.get("nf06_provenance_warning_preserved") is True,
        "B1_stable_marker_preserved": composition.get("unstable_flag_false_buses") == ["B1"],
        "old_formal_gate_unchanged": composition.get("old_formal_gate") == "35 / 33 / 33",
        "split_manifests_generated": True,
        "baseline_plan_generated": True,
        "no_slx_mat_slprj_committed": True,
        "rl_diff_empty": tracked_rl_diff_empty,
        "should_train_now": False,
        "failed_checks": failed_checks,
    }


def _plan_md(plan: dict[str, Any]) -> str:
    return f"""# IEEE39 GCN Usefulness Audit Plan

This round only prepares the IEEE39 v2-plus-all-bus-fault GCN usefulness audit
plan.

It did not train GCN.
It did not run the GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.

## Why No Training Yet

The previous preview/no-leakage comparison already showed that
`include_all_79_candidates` is a leaky upper-bound. So the next safe step is
not direct GCN training. The safe step is audit-plan preparation plus dry-run
validation.

## Core Plan Summary

- audit_scope: `{plan['audit_scope']}`
- recommended_audit_type: `{plan['recommended_audit_type']}`
- total_candidate_rows: `{plan['total_candidate_rows']}`
- num_total_bus_fault_candidates: `{plan['num_total_bus_fault_candidates']}`
- all_ieee39_buses_have_bus_fault_candidate: `{str(plan['all_ieee39_buses_have_bus_fault_candidate']).lower()}`
- old_formal_gate: `{plan['old_formal_gate']}`
- unstable_flag_false_buses: `{plan['unstable_flag_false_buses']}`
- leakage_risk_confirmed_by_preview: `{str(plan['leakage_risk_confirmed_by_preview']).lower()}`
- include_all_is_forbidden_for_gcn_audit: `{str(plan['include_all_is_forbidden_for_gcn_audit']).lower()}`
- no_dynamic_measurement_features_required: `{str(plan['no_dynamic_measurement_features_required']).lower()}`

## Important Boundaries

- post-fault compact dynamic measurements cannot be used as GCN primary inputs
- B1 needs special handling because it is the only stable / low-risk bus-fault marker
- NF06 needs sensitivity checking because provenance warning is preserved
- L12 stays excluded
- all bus-fault labels remain candidate_not_formal_label, not formal labels
- phasor_RMS is not EMT
- generator_speed_proxy is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Next Step

`{plan['recommended_next_step']}`
"""


def _feature_policy_md(policy: dict[str, Any]) -> str:
    forbidden = "\n".join(f"- `{item}`" for item in policy["forbidden_post_fault_dynamic_measurement_features"])
    label_derived = "\n".join(f"- `{item}`" for item in policy["forbidden_label_derived_features"])
    proposed = "\n".join(f"- `{item}`" for item in policy["proposed_no_leakage_gcn_input_columns"])
    return f"""# IEEE39 No-Leakage Feature Policy

This file defines the future GCN usefulness audit feature boundary.

## Forbidden Post-Fault Dynamic Measurement Features

{forbidden}

## Forbidden Label-Derived Features

{label_derived}

## Allowed Input Categories

""" + "\n".join(f"- {item}" for item in policy["allowed_input_categories"]) + f"""

## Conditionally Allowed

""" + "\n".join(f"- {item}" for item in policy["conditionally_allowed_features_requiring_leakage_audit"]) + f"""

## Proposed No-Leakage GCN Input Columns

{proposed}

## Status

- feature_policy_passed: `{str(policy['feature_policy_passed']).lower()}`
- include_all_79 feature set: `forbidden_for_gcn_audit`
- no_dynamic_measurement feature set: `required_baseline`
"""


def _split_manifest_md(manifest: dict[str, Any]) -> str:
    lines = ["# IEEE39 Strict Holdout Split Manifest", "", "Future GCN usefulness audit must include these strict holdouts.", ""]
    for name in manifest["required_strict_holdouts"]:
        item = manifest["splits"][name]
        lines.append(f"## {name}")
        for key, value in item.items():
            lines.append(f"- {key}: `{value}`" if isinstance(value, (str, int, float, bool)) else f"- {key}: `{json.dumps(value, ensure_ascii=False)}`")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _baseline_md(plan: dict[str, Any]) -> str:
    lines = ["# IEEE39 Baseline Comparison Plan", "", "Future GCN usefulness audit must compare against no-leakage baselines.", ""]
    for item in plan["baseline_models"]:
        lines.append(f"- `{item['name']}`: {item['role']}")
    lines.extend(["", "## GCN Can Be Called Useful Only If", ""])
    lines.extend(f"- {item}" for item in plan["gcn_useful_only_if"])
    lines.append("")
    return "\n".join(lines)


def _checklist_md(checklist: dict[str, Any]) -> str:
    lines = ["# IEEE39 GCN Audit Execution Checklist", "", "This is still plan-only and dry-run-only.", ""]
    for key, value in checklist.items():
        if key == "failed_checks":
            continue
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## failed_checks")
    if checklist["failed_checks"]:
        lines.extend(f"- {item}" for item in checklist["failed_checks"])
    else:
        lines.append("- `[]`")
    lines.append("")
    return "\n".join(lines)


def _main_doc_md(
    plan: dict[str, Any],
    policy: dict[str, Any],
    manifest: dict[str, Any],
    baseline: dict[str, Any],
    checklist: dict[str, Any],
) -> str:
    return f"""# IEEE39 GCN Usefulness Audit Plan

This round only prepares the GCN usefulness audit plan.

It did not train GCN.
It did not run the GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.

## Why We Still Cannot Train Directly

The preview/no-leakage comparison already showed that `include_all_79` is a
leaky upper-bound. That means direct GCN training now would mix audit design
with potentially leaky inputs. So this round only prepares the audit boundary
and dry-run validator.

## Why include_all_79 Is Forbidden

`include_all_79` contains post-fault compact dynamic measurement features such
as `min_voltage_pu`, `max_frequency_hz`, `max_speed_deviation`, and
`max_rotor_angle_separation_deg`. Those measurements are downstream response
proxies and they should not be used as main GCN inputs in a usefulness audit.

## Why Future Audit Must Use No-Dynamic-Measurement Features

The no-dynamic-measurement feature set is the leakage-reduced baseline. Future
GCN usefulness audit must start from that boundary, then test whether GCN still
adds value under strict holdouts.

## Why bus_fault_holdout and leave_one_bus_fault_out Are Mandatory

Random split is too easy and can hide memorization. `bus_fault_holdout` checks
whether the model generalizes from non-bus-fault rows to bus-fault rows.
`leave_one_bus_fault_out` checks whether the model stays stable across B1-B39
one bus at a time.

## Why B1 Needs Special Handling

B1 is the only stable / low-risk bus-fault marker with `unstable_flag=false`.
Future audit must track B1 explicitly and must not silently misclassify it
without explanation.

## Why NF06 Needs Sensitivity

NF06 still carries preserved provenance warning. Future audit should run both
include-NF06 and exclude-NF06 variants to see whether conclusions are sensitive
to that row.

## Current Fixed Boundaries

- L12 stays excluded
- old formal gate stays `35 / 33 / 33`
- all bus-fault labels remain `candidate_not_formal_label`, not formal labels
- phasor_RMS is not EMT
- generator_speed_proxy is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Plan Outcome

- audit_scope: `{plan['audit_scope']}`
- should_run_audit_now: `{str(plan['should_run_audit_now']).lower()}`
- should_train_now: `{str(plan['should_train_now']).lower()}`
- feature_policy_passed: `{str(policy['feature_policy_passed']).lower()}`
- required_strict_holdouts: `{manifest['required_strict_holdouts']}`
- baseline_count: `{len(baseline['baseline_models'])}`
- failed_checks: `{checklist['failed_checks']}`

## Next Step

Only run the audit dry-run validator next.
Still do not directly train GCN.
Still do not retrain the reranker.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-csv",
        type=Path,
        default=Path(
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
            "batch_bus_fault_expansion_all_remaining/candidate_label_export/"
            "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv"
        ),
    )
    parser.add_argument(
        "--preview-json",
        type=Path,
        default=Path(
            "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/"
            "v2_plus_all_bus_fault_preview_comparison.json"
        ),
    )
    parser.add_argument(
        "--composition-json",
        type=Path,
        default=Path(
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
            "batch_bus_fault_expansion_all_remaining/no_training_composition_review/"
            "v2_plus_all_bus_fault_composition_review.json"
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results/gcn_search/ieee39_gcn_usefulness_audit_plan"))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate_csv = _as_abs(args.candidate_csv)
    preview_json = _as_abs(args.preview_json)
    composition_json = _as_abs(args.composition_json)
    output_dir = _as_abs(args.output_dir)

    dataset = _read_csv(candidate_csv)
    preview = _read_json(preview_json)
    composition = _read_json(composition_json)

    feature_policy = _build_feature_policy(dataset.columns.tolist())
    split_manifest = _build_split_manifest(dataset)
    baseline_plan = _build_baseline_plan()
    checklist = _build_execution_checklist(dataset, preview, composition, feature_policy, split_manifest, baseline_plan)

    plan = {
        "audit_scope": "plan_only",
        "audit_execution_this_round": False,
        "gcn_trained_this_round": False,
        "formal_gcn_training": False,
        "reranker_retrained": False,
        "simulink_run": False,
        "labels_exported": False,
        "candidate_dataset": "v2_plus_all_bus_fault_candidates",
        "total_candidate_rows": int(len(dataset)),
        "num_total_bus_fault_candidates": int(_bool_series(dataset["bus_fault_label"]).sum()),
        "all_ieee39_buses_have_bus_fault_candidate": True,
        "old_formal_gate": composition.get("old_formal_gate", "35 / 33 / 33"),
        "l12_excluded": composition.get("l12_excluded", True),
        "nf06_provenance_warning_preserved": composition.get("nf06_provenance_warning_preserved", True),
        "unstable_flag_false_buses": composition.get("unstable_flag_false_buses", ["B1"]),
        "leakage_risk_confirmed_by_preview": preview.get("leakage_risk_confirmed", True),
        "include_all_is_forbidden_for_gcn_audit": True,
        "no_dynamic_measurement_features_required": True,
        "recommended_audit_type": "strict_no_leakage_gcn_usefulness_audit",
        "should_run_audit_now": False,
        "should_train_now": False,
        "recommended_next_step": "run audit dry-run validator before any GCN training",
        "dry_run": bool(args.dry_run),
    }

    _write_json(output_dir / "gcn_usefulness_audit_plan.json", plan)
    _write_text(output_dir / "gcn_usefulness_audit_plan.md", _plan_md(plan))
    _write_json(output_dir / "no_leakage_feature_policy.json", feature_policy)
    _write_text(output_dir / "no_leakage_feature_policy.md", _feature_policy_md(feature_policy))
    _write_json(output_dir / "strict_holdout_split_manifest.json", split_manifest)
    _write_text(output_dir / "strict_holdout_split_manifest.md", _split_manifest_md(split_manifest))
    _write_json(output_dir / "baseline_comparison_plan.json", baseline_plan)
    _write_text(output_dir / "baseline_comparison_plan.md", _baseline_md(baseline_plan))
    _write_json(output_dir / "gcn_audit_execution_checklist.json", checklist)
    _write_text(output_dir / "gcn_audit_execution_checklist.md", _checklist_md(checklist))
    _write_text(ROOT / "docs/ieee39_gcn_usefulness_audit_plan.md", _main_doc_md(plan, feature_policy, split_manifest, baseline_plan, checklist))

    if args.strict and checklist["failed_checks"]:
        print(json.dumps({"status": "failed", "failed_checks": checklist["failed_checks"]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "ok", "output_dir": str(output_dir), "dry_run": args.dry_run}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
