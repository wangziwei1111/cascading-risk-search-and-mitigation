"""Run IEEE39 GCN usefulness audit dry-run validation.

This script is dry-run only. It reads existing CSV/JSON artifacts and checks
whether a future GCN usefulness audit can be executed safely without leakage.
It does not train GCN, does not run the formal audit, does not run Simulink,
does not export labels, and does not save any model.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PLAN_DIR = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan"
DEFAULT_OUTPUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run"
DATASET_PATH = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
    "batch_bus_fault_expansion_all_remaining/candidate_label_export/"
    "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv"
)
PREVIEW_PATH = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/"
    "v2_plus_all_bus_fault_preview_comparison.json"
)
EXPORT_SUMMARY_PATH = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
    "batch_bus_fault_expansion_all_remaining/candidate_label_export/"
    "batch_candidate_label_export_summary.json"
)
POLICY_PATH = PLAN_DIR / "no_leakage_feature_policy.json"
SPLIT_PATH = PLAN_DIR / "strict_holdout_split_manifest.json"
BASELINE_PATH = PLAN_DIR / "baseline_comparison_plan.json"
CHECKLIST_PATH = PLAN_DIR / "gcn_audit_execution_checklist.json"
PLAN_PATH = PLAN_DIR / "gcn_usefulness_audit_plan.json"

OLD_FORMAL_GATE = "35 / 33 / 33"
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
ALLOWED_CONSERVATIVE_FEATURES = [
    "fault_type",
    "duration_s",
    "fault_start_s",
    "fault_clear_s",
    "trip_implementation",
    "line_id",
    "target_bus",
    "target_bus_or_component",
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
REQUIRED_BASELINES = [
    "Ridge Regression",
    "Logistic Regression",
    "RandomForest or GradientBoosting",
    "simple ranking baseline",
    "topology-only baseline",
    "target-bus-only baseline",
]
FORBIDDEN_TRACKED_TOKENS = [
    ".slx",
    ".slxc",
    "slprj",
    ".mat",
    "raw traject",
    "full timeseries",
    "local_lab_copies",
]


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


def _write_summary_csv(path: Path, summary: dict[str, Any]) -> None:
    rows: list[dict[str, str]] = []
    for key, value in summary.items():
        if isinstance(value, (list, dict)):
            rendered = json.dumps(value, ensure_ascii=False)
        else:
            rendered = str(value)
        rows.append({"field": key, "value": rendered})
    pd.DataFrame(rows).to_csv(_fs_path(path), index=False, encoding="utf-8-sig")


def _path_exists(path: Path) -> bool:
    return os.path.exists(_fs_path(path))


def _bool_series(series: pd.Series) -> pd.Series:
    return series.map(lambda value: str(value).strip().lower() in {"1", "true", "yes"})


def _bus_sort_key(value: str) -> tuple[int, str]:
    if value.startswith("B") and value[1:].isdigit():
        return (int(value[1:]), value)
    return (10_000, value)


def _git_output(args: list[str]) -> str:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True)
    return result.stdout


def _load_required_inputs() -> dict[str, Any]:
    return {
        "plan": _read_json(PLAN_PATH),
        "policy": _read_json(POLICY_PATH),
        "split_manifest": _read_json(SPLIT_PATH),
        "baseline_plan": _read_json(BASELINE_PATH),
        "checklist": _read_json(CHECKLIST_PATH),
        "preview": _read_json(PREVIEW_PATH),
        "export_summary": _read_json(EXPORT_SUMMARY_PATH),
        "dataset": _read_csv(DATASET_PATH),
    }


def _dataset_checks(dataset: pd.DataFrame, export_summary: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    failed_checks: list[str] = []
    bus_fault = dataset[_bool_series(dataset["bus_fault_label"])].copy()
    covered_buses = sorted(bus_fault["target_bus"].fillna("").astype(str).unique().tolist(), key=_bus_sort_key)
    expected_buses = [f"B{i}" for i in range(1, 40)]
    missing_buses = [bus for bus in expected_buses if bus not in covered_buses]

    scenario_dups = (
        dataset.loc[dataset["scenario_id"].astype(str).duplicated(keep=False), "scenario_id"]
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )
    label_dups = (
        dataset.loc[dataset["label_id_v2"].astype(str).duplicated(keep=False), "label_id_v2"]
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    if len(dataset) != 79:
        failed_checks.append(f"Dataset row count mismatch: expected 79, got {len(dataset)}.")
    if len(bus_fault) != 39:
        failed_checks.append(f"Bus-fault row count mismatch: expected 39, got {len(bus_fault)}.")
    if missing_buses:
        failed_checks.append(f"Bus-fault coverage is incomplete. Missing buses: {missing_buses}.")
    if scenario_dups:
        failed_checks.append(f"Duplicate scenario_id values detected: {scenario_dups}.")
    if label_dups:
        failed_checks.append(f"Duplicate label_id_v2 values detected: {label_dups}.")

    old_formal_gate_values = sorted({str(value).strip() for value in dataset["old_formal_gate"].fillna("")})
    nonempty_old_formal_gate = sorted([value for value in old_formal_gate_values if value])
    if export_summary.get("old_formal_gate") != OLD_FORMAL_GATE:
        failed_checks.append("Export summary does not preserve old_formal_gate = 35 / 33 / 33.")
    if export_summary.get("formal_label_gate_changed") is not False:
        failed_checks.append("formal_label_gate_changed must stay false.")
    if export_summary.get("l12_excluded") is not True:
        failed_checks.append("Export summary does not preserve L12 exclusion.")
    if export_summary.get("nf06_provenance_warning_preserved") is not True:
        failed_checks.append("Export summary does not preserve NF06 provenance warning.")
    if export_summary.get("unstable_flag_false_buses") != ["B1"]:
        failed_checks.append("Export summary does not preserve B1 stable marker.")
    if nonempty_old_formal_gate != [OLD_FORMAL_GATE]:
        failed_checks.append(f"Dataset old_formal_gate values changed: {nonempty_old_formal_gate}.")

    nf06_rows = dataset[dataset["scenario_id"].astype(str) == "NF06"].copy()
    if nf06_rows.empty or not _bool_series(nf06_rows["provenance_check_required"]).any():
        failed_checks.append("NF06 provenance warning is not preserved in dataset rows.")

    b1_bus_fault = bus_fault[bus_fault["target_bus"].astype(str) == "B1"].copy()
    if len(b1_bus_fault) != 1 or _bool_series(b1_bus_fault["unstable_flag"]).any():
        failed_checks.append("B1 stable marker is not preserved as the unique unstable_flag=false bus-fault row.")

    return (
        {
            "candidate_dataset_exists": True,
            "total_candidate_rows": int(len(dataset)),
            "num_total_bus_fault_candidates": int(len(bus_fault)),
            "all_ieee39_buses_have_bus_fault_candidate": missing_buses == [],
            "covered_buses": covered_buses,
            "missing_buses": missing_buses,
            "scenario_id_duplicates": scenario_dups,
            "label_id_v2_duplicates": label_dups,
            "old_formal_gate": export_summary.get("old_formal_gate"),
            "formal_label_gate_changed": bool(export_summary.get("formal_label_gate_changed")),
            "l12_excluded": export_summary.get("l12_excluded") is True,
            "nf06_provenance_warning_preserved": export_summary.get("nf06_provenance_warning_preserved") is True,
            "b1_stable_marker_preserved": export_summary.get("unstable_flag_false_buses") == ["B1"],
        },
        failed_checks,
    )


def _feature_checks(dataset: pd.DataFrame, policy: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    failed_checks: list[str] = []
    warning_checks: list[str] = []
    columns = dataset.columns.astype(str).tolist()
    proposed = [name for name in ALLOWED_CONSERVATIVE_FEATURES if name in columns]
    forbidden_detected = [name for name in proposed if name in FORBIDDEN_FEATURES or name in LABEL_DERIVED_FEATURES]

    if forbidden_detected:
        failed_checks.append(f"Forbidden features leaked into proposed GCN inputs: {forbidden_detected}.")
    if "dynamic_stress_score" in proposed:
        failed_checks.append("dynamic_stress_score must not enter proposed GCN inputs.")
    if "unstable_flag" in proposed:
        failed_checks.append("unstable_flag must not enter proposed GCN inputs.")

    policy_proposed = policy.get("proposed_no_leakage_gcn_input_columns", [])
    if sorted(policy_proposed) != sorted(proposed):
        warning_checks.append(
            "Policy proposed_no_leakage_gcn_input_columns differs from validator-generated conservative proposal."
        )
    if "target_bus" in proposed or "target_bus_or_component" in proposed:
        warning_checks.append(
            "target_bus / target_bus_or_component can cause target-bus memorization and must be compared against target-bus-only baseline."
        )
    if any(name in proposed for name in {"duration_s", "fault_start_s", "fault_clear_s"}):
        warning_checks.append(
            "duration_s / fault_start_s / fault_clear_s are only intervention design variables, not free physical state features."
        )

    manifest = {
        "manifest_scope": "dry_run_only",
        "forbidden_post_fault_dynamic_measurement_features": FORBIDDEN_FEATURES,
        "forbidden_label_derived_features": LABEL_DERIVED_FEATURES,
        "dataset_columns": columns,
        "proposed_no_leakage_gcn_input_columns": proposed,
        "forbidden_features_detected_in_inputs": forbidden_detected,
        "target_bus_memorization_risk_flagged": "target_bus" in proposed or "target_bus_or_component" in proposed,
        "duration_feature_risk_flagged": any(name in proposed for name in {"duration_s", "fault_start_s", "fault_clear_s"}),
        "notes": [
            "post-fault compact dynamic measurements cannot be used as GCN main inputs",
            "candidate family flags must not enter primary GCN inputs",
            "graph topology / adjacency features are allowed only if they do not encode label leakage",
        ],
    }
    return manifest, failed_checks, warning_checks


def _split_checks(split_manifest: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    failed_checks: list[str] = []
    splits = split_manifest.get("splits", {})

    if split_manifest.get("required_strict_holdouts") != REQUIRED_STRICT_HOLDOUTS:
        failed_checks.append("required_strict_holdouts does not match the expected strict holdout list.")

    for name in REQUIRED_STRICT_HOLDOUTS:
        if name not in splits:
            failed_checks.append(f"Missing strict holdout: {name}.")

    leave_one = splits.get("leave_one_bus_fault_out", {})
    leave_one_buses = leave_one.get("holdout_targets", [])
    no_dyn_leave_one = splits.get("no_dynamic_measurement_leave_one_bus_fault_out", {})
    no_dyn_buses = no_dyn_leave_one.get("holdout_targets", [])
    expected_buses = [f"B{i}" for i in range(1, 40)]

    if leave_one_buses != expected_buses:
        failed_checks.append("leave_one_bus_fault_out does not cover exactly B1-B39.")
    if no_dyn_buses != expected_buses:
        failed_checks.append("no_dynamic_measurement_leave_one_bus_fault_out does not cover exactly B1-B39.")
    if leave_one.get("special_tracking_bus") != "B1":
        failed_checks.append("leave_one_bus_fault_out must special-track B1.")
    if no_dyn_leave_one.get("special_tracking_bus") != "B1":
        failed_checks.append("no_dynamic_measurement_leave_one_bus_fault_out must special-track B1.")

    nf06 = splits.get("nf06_provenance_sensitivity", {})
    if sorted(nf06.get("variants", [])) != ["exclude_NF06", "include_NF06"]:
        failed_checks.append("nf06_provenance_sensitivity must contain include_NF06 and exclude_NF06.")

    l12 = splits.get("l12_exclusion_check", {})
    if l12.get("required") is not True:
        failed_checks.append("l12_exclusion_check.required must stay true.")
    if l12.get("excluded_line") != "L12":
        failed_checks.append("l12_exclusion_check.excluded_line must stay L12.")

    return (
        {
            "strict_holdouts_complete": len(failed_checks) == 0,
            "required_strict_holdouts": REQUIRED_STRICT_HOLDOUTS,
            "b1_special_tracking_enabled": leave_one.get("special_tracking_bus") == "B1"
            and no_dyn_leave_one.get("special_tracking_bus") == "B1",
            "nf06_sensitivity_enabled": sorted(nf06.get("variants", [])) == ["exclude_NF06", "include_NF06"],
            "l12_exclusion_check_enabled": l12.get("required") is True and l12.get("excluded_line") == "L12",
        },
        failed_checks,
    )


def _baseline_checks(baseline_plan: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    failed_checks: list[str] = []
    baseline_names = [str(item.get("name", "")) for item in baseline_plan.get("baseline_models", [])]
    for required in REQUIRED_BASELINES:
        if required not in baseline_names:
            failed_checks.append(f"Missing baseline plan entry: {required}.")

    return (
        {
            "baseline_comparison_complete": len(failed_checks) == 0,
            "baseline_models": baseline_names,
            "gcn_can_only_be_called_useful_if": baseline_plan.get("gcn_useful_only_if", []),
        },
        failed_checks,
    )


def _repo_checks() -> tuple[dict[str, Any], list[str]]:
    failed_checks: list[str] = []
    rl_diff = _git_output(["git", "diff", "--", "src/rl_mitigation", "scripts/rl_mitigation"]).strip()
    tracked_files = _git_output(["git", "ls-files"]).splitlines()
    forbidden_tracked = [
        path
        for path in tracked_files
        if any(token in path.lower() for token in FORBIDDEN_TRACKED_TOKENS)
    ]
    if rl_diff:
        failed_checks.append("RL mitigation diff is not empty.")
    if forbidden_tracked:
        failed_checks.append(f"Forbidden tracked files detected: {forbidden_tracked}.")

    return (
        {
            "rl_diff_empty": rl_diff == "",
            "forbidden_tracked_files_detected": forbidden_tracked,
        },
        failed_checks,
    )


def _render_md(summary: dict[str, Any]) -> str:
    warning_lines = "\n".join(f"- {item}" for item in summary["warning_checks"]) if summary["warning_checks"] else "- none"
    failed_lines = "\n".join(f"- {item}" for item in summary["failed_checks"]) if summary["failed_checks"] else "- none"
    proposed_lines = "\n".join(f"- `{item}`" for item in summary["proposed_no_leakage_gcn_input_columns"]) or "- none"
    holdout_lines = "\n".join(f"- `{item}`" for item in summary["required_strict_holdouts"])
    baseline_lines = "\n".join(f"- `{item}`" for item in summary["baseline_models"])
    return f"""# IEEE39 GCN Usefulness Audit Dry-Run Validator Summary

This round only runs the dry-run validator. It does not train GCN, does not run
the formal GCN usefulness audit, does not run Simulink, does not export labels,
and does not save any model.

## Validator Scope

- validator_scope: `{summary['validator_scope']}`
- dry_run_validator_passed: `{str(summary['dry_run_validator_passed']).lower()}`
- should_run_formal_gcn_audit_now: `{str(summary['should_run_formal_gcn_audit_now']).lower()}`
- should_train_gcn_now: `{str(summary['should_train_gcn_now']).lower()}`
- recommended_next_step: `{summary['recommended_next_step']}`

## Dataset Checks

- total_candidate_rows: `{summary['total_candidate_rows']}`
- num_total_bus_fault_candidates: `{summary['num_total_bus_fault_candidates']}`
- all_ieee39_buses_have_bus_fault_candidate: `{str(summary['all_ieee39_buses_have_bus_fault_candidate']).lower()}`
- old_formal_gate: `{summary['old_formal_gate']}`
- l12_excluded: `{str(summary['l12_excluded']).lower()}`
- nf06_provenance_warning_preserved: `{str(summary['nf06_provenance_warning_preserved']).lower()}`
- b1_special_tracking_enabled: `{str(summary['b1_special_tracking_enabled']).lower()}`

## Proposed No-Leakage Inputs

{proposed_lines}

## Required Strict Holdouts

{holdout_lines}

## Required Baselines

{baseline_lines}

## warning_checks

{warning_lines}

## failed_checks

{failed_lines}
"""


def _render_manifest_md(manifest: dict[str, Any]) -> str:
    proposed = "\n".join(f"- `{item}`" for item in manifest["proposed_no_leakage_gcn_input_columns"]) or "- none"
    forbidden = "\n".join(f"- `{item}`" for item in manifest["forbidden_post_fault_dynamic_measurement_features"] + manifest["forbidden_label_derived_features"])
    allowed = "\n".join(f"- `{item}`" for item in manifest["proposed_no_leakage_gcn_input_columns"]) or "- none"
    conditional = "\n".join(
        [
            "- `target_bus` / `target_bus_or_component` only with explicit target-bus-only baseline comparison",
            "- `duration_s` / `fault_start_s` / `fault_clear_s` only as intervention design variables",
        ]
    )
    return f"""# Proposed No-Leakage GCN Inputs Manifest

- proposed_input_columns: `{json.dumps(manifest['proposed_no_leakage_gcn_input_columns'], ensure_ascii=False)}`
- forbidden_columns_checked: `{json.dumps(manifest['forbidden_post_fault_dynamic_measurement_features'] + manifest['forbidden_label_derived_features'], ensure_ascii=False)}`
- forbidden_columns_present: `{json.dumps(manifest['forbidden_features_detected_in_inputs'], ensure_ascii=False)}`
- allowed_columns_present: `{json.dumps(manifest['proposed_no_leakage_gcn_input_columns'], ensure_ascii=False)}`
- conditionally_allowed_columns: `["target_bus", "target_bus_or_component", "duration_s", "fault_start_s", "fault_clear_s"]`
- target_bus_memorization_risk: `{str(manifest['target_bus_memorization_risk_flagged']).lower()}`
- mitigation: `compare against target-bus-only baseline and topology-only baseline`
- post_fault_dynamic_measurement_features_excluded: `{str(not manifest['forbidden_features_detected_in_inputs']).lower()}`
- label_derived_features_excluded: `{str(not manifest['forbidden_features_detected_in_inputs']).lower()}`
- target_columns_excluded: `true`

## Proposed Input Columns

{proposed}

## Forbidden Columns Checked

{forbidden}

## Allowed Columns Present

{allowed}

## Conditionally Allowed Columns

{conditional}
"""


def _build_execution_draft(summary: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_scope": "execution_draft_only",
        "execute_this_round": False,
        "suggested_next_round_title": "Run IEEE39 strict no-leakage GCN usefulness audit",
        "required_inputs": [
            str(DATASET_PATH.relative_to(ROOT)),
            str(PLAN_PATH.relative_to(ROOT)),
            str(POLICY_PATH.relative_to(ROOT)),
            str(SPLIT_PATH.relative_to(ROOT)),
            str(BASELINE_PATH.relative_to(ROOT)),
            str(PREVIEW_PATH.relative_to(ROOT)),
            str(EXPORT_SUMMARY_PATH.relative_to(ROOT)),
        ],
        "required_splits": summary["required_strict_holdouts"],
        "required_baselines": summary["baseline_models"],
        "required_outputs": [
            "strict holdout metrics",
            "per-bus leave-one-bus-fault-out report",
            "B1 special tracking report",
            "NF06 include/exclude sensitivity comparison",
            "L12 exclusion confirmation",
            "baseline comparison summary",
        ],
        "required_boundary_flags": {
            "must_use_no_leakage_features": True,
            "must_keep_l12_excluded": True,
            "must_preserve_nf06_warning": True,
            "must_preserve_old_formal_gate": OLD_FORMAL_GATE,
            "must_not_use_post_fault_compact_measurements_as_main_inputs": True,
        },
        "stopping_conditions": [
            "forbidden feature enters proposed GCN inputs",
            "strict holdout split is incomplete",
            "baseline comparison plan is incomplete",
            "B1 special tracking is missing",
            "NF06 sensitivity is missing",
            "L12 exclusion is not preserved",
            "RL mitigation diff is non-empty",
        ],
        "forbidden_features": manifest["forbidden_post_fault_dynamic_measurement_features"]
        + manifest["forbidden_label_derived_features"],
        "must_compare_against_baselines": True,
        "must_report_B1": True,
        "must_report_NF06_sensitivity": True,
        "must_report_L12_exclusion": True,
        "must_not_claim_final_engineering_conclusion": True,
    }


def _render_execution_draft_md(draft: dict[str, Any]) -> str:
    return f"""# Formal GCN Audit Execution Draft

- draft_scope: `{draft['draft_scope']}`
- execute_this_round: `{str(draft['execute_this_round']).lower()}`
- suggested_next_round_title: `{draft['suggested_next_round_title']}`
- must_compare_against_baselines: `{str(draft['must_compare_against_baselines']).lower()}`
- must_report_B1: `{str(draft['must_report_B1']).lower()}`
- must_report_NF06_sensitivity: `{str(draft['must_report_NF06_sensitivity']).lower()}`
- must_report_L12_exclusion: `{str(draft['must_report_L12_exclusion']).lower()}`
- must_not_claim_final_engineering_conclusion: `{str(draft['must_not_claim_final_engineering_conclusion']).lower()}`

## Required Inputs

""" + "\n".join(f"- `{item}`" for item in draft["required_inputs"]) + """

## Required Splits

""" + "\n".join(f"- `{item}`" for item in draft["required_splits"]) + """

## Required Baselines

""" + "\n".join(f"- `{item}`" for item in draft["required_baselines"]) + """

## Required Outputs

""" + "\n".join(f"- {item}" for item in draft["required_outputs"]) + """

## Required Boundary Flags

""" + "\n".join(f"- `{key}`: `{value}`" for key, value in draft["required_boundary_flags"].items()) + """

## Stopping Conditions

""" + "\n".join(f"- {item}" for item in draft["stopping_conditions"]) + "\n"


def _render_round_doc(summary: dict[str, Any]) -> str:
    return f"""# IEEE39 GCN Usefulness Audit Dry-Run Validator

This round is the IEEE39 GCN audit dry-run validator.

It did not train GCN.
It did not run the formal GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.

## What The Dry-Run Validator Checked

- candidate dataset row count, bus-fault row count, and B1-B39 coverage
- duplicate `scenario_id` / `label_id_v2` risks
- forbidden feature exclusion from proposed GCN inputs
- strict holdout completeness
- baseline comparison completeness
- B1 special tracking
- NF06 sensitivity
- L12 exclusion
- RL diff cleanliness
- forbidden tracked artifact cleanliness

## Dry-Run Result

- validator_scope: `{summary['validator_scope']}`
- dry_run_validator_passed: `{str(summary['dry_run_validator_passed']).lower()}`
- total_candidate_rows: `{summary['total_candidate_rows']}`
- num_total_bus_fault_candidates: `{summary['num_total_bus_fault_candidates']}`
- forbidden_features_detected_in_inputs: `{json.dumps(summary['forbidden_features_detected_in_inputs'], ensure_ascii=False)}`
- strict_holdouts_complete: `{str(summary['strict_holdouts_complete']).lower()}`
- baseline_comparison_complete: `{str(summary['baseline_comparison_complete']).lower()}`
- b1_special_tracking_enabled: `{str(summary['b1_special_tracking_enabled']).lower()}`
- nf06_sensitivity_enabled: `{str(summary['nf06_sensitivity_enabled']).lower()}`
- l12_exclusion_check_enabled: `{str(summary['l12_exclusion_check_enabled']).lower()}`
- target_bus_memorization_risk_flagged: `{str(summary['target_bus_memorization_risk_flagged']).lower()}`

## Important Boundary Notes

- forbidden features are excluded from proposed primary GCN inputs
- strict holdouts are complete
- baseline comparison is complete
- B1 remains special-tracked
- NF06 sensitivity remains enabled
- L12 remains excluded
- target_bus encoding has memorization risk and must be compared against target-bus-only baseline
- even after dry-run pass, the next step cannot be blind training
- the next step can only be preparing formal GCN usefulness audit execution
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
"""


def build_summary(strict: bool = False, dry_run: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    failed_checks: list[str] = []
    warning_checks: list[str] = []

    required_files = [
        PLAN_PATH,
        POLICY_PATH,
        SPLIT_PATH,
        BASELINE_PATH,
        CHECKLIST_PATH,
        PREVIEW_PATH,
        EXPORT_SUMMARY_PATH,
        DATASET_PATH,
    ]
    missing_files = [str(path.relative_to(ROOT)) for path in required_files if not _path_exists(path)]
    if missing_files:
        failed_checks.extend([f"Missing required input artifact: {item}" for item in missing_files])
        summary = {
            "validator_scope": "dry_run_only",
            "audit_execution_this_round": False,
            "gcn_trained_this_round": False,
            "formal_gcn_training": False,
            "reranker_retrained": False,
            "simulink_run": False,
            "labels_exported": False,
            "model_saved": False,
            "total_candidate_rows": 0,
            "num_total_bus_fault_candidates": 0,
            "all_ieee39_buses_have_bus_fault_candidate": False,
            "forbidden_features_detected_in_inputs": [],
            "forbidden_features_absent_from_gcn_inputs": False,
            "proposed_no_leakage_gcn_input_columns": [],
            "target_bus_memorization_risk_flagged": False,
            "strict_holdouts_complete": False,
            "required_strict_holdouts": REQUIRED_STRICT_HOLDOUTS,
            "baseline_comparison_complete": False,
            "baseline_models": [],
            "b1_special_tracking_enabled": False,
            "nf06_sensitivity_enabled": False,
            "l12_exclusion_check_enabled": False,
            "old_formal_gate": OLD_FORMAL_GATE,
            "l12_excluded": False,
            "nf06_provenance_warning_preserved": False,
            "warning_checks": warning_checks,
            "failed_checks": failed_checks,
            "dry_run_validator_passed": False,
            "should_run_formal_gcn_audit_now": False,
            "should_train_gcn_now": False,
            "recommended_next_step": "fix dry-run blockers before any formal GCN audit",
            "dry_run": dry_run,
            "strict": strict,
        }
        manifest = {
            "manifest_scope": "dry_run_only",
            "proposed_no_leakage_gcn_input_columns": [],
            "forbidden_features_detected_in_inputs": [],
            "missing_required_inputs": missing_files,
        }
        return summary, manifest

    inputs = _load_required_inputs()
    dataset_info, dataset_failures = _dataset_checks(inputs["dataset"], inputs["export_summary"])
    feature_manifest, feature_failures, feature_warnings = _feature_checks(inputs["dataset"], inputs["policy"])
    split_info, split_failures = _split_checks(inputs["split_manifest"])
    baseline_info, baseline_failures = _baseline_checks(inputs["baseline_plan"])
    repo_info, repo_failures = _repo_checks()

    failed_checks.extend(dataset_failures)
    failed_checks.extend(feature_failures)
    failed_checks.extend(split_failures)
    failed_checks.extend(baseline_failures)
    failed_checks.extend(repo_failures)
    warning_checks.extend(feature_warnings)

    plan = inputs["plan"]
    preview = inputs["preview"]
    checklist = inputs["checklist"]

    if plan.get("audit_scope") != "plan_only":
        failed_checks.append("Plan audit_scope changed away from plan_only.")
    if preview.get("include_all_is_leaky_upper_bound") is not True:
        failed_checks.append("Preview comparison no longer preserves include_all_is_leaky_upper_bound=true.")
    if preview.get("target_feature_leakage_risk_if_used_as_inputs") is not True:
        failed_checks.append("Preview comparison no longer preserves target_feature_leakage_risk_if_used_as_inputs=true.")
    if checklist.get("should_train_now") is not False:
        failed_checks.append("Plan checklist should_train_now must stay false.")
    if plan.get("should_train_now") is not False or plan.get("should_run_audit_now") is not False:
        failed_checks.append("Plan should_run_audit_now / should_train_now must stay false in this dry-run round.")

    warning_checks.extend(
        [
            "phasor_RMS is not EMT.",
            "generator_speed_proxy is not direct frequency.",
            "temporary bus-fault injection is not engineering-grade protection.",
        ]
    )

    summary = {
        "validator_scope": "dry_run_only",
        "audit_execution_this_round": False,
        "gcn_trained_this_round": False,
        "formal_gcn_training": False,
        "reranker_retrained": False,
        "simulink_run": False,
        "labels_exported": False,
        "model_saved": False,
        "total_candidate_rows": dataset_info["total_candidate_rows"],
        "num_total_bus_fault_candidates": dataset_info["num_total_bus_fault_candidates"],
        "all_ieee39_buses_have_bus_fault_candidate": dataset_info["all_ieee39_buses_have_bus_fault_candidate"],
        "forbidden_features_detected_in_inputs": feature_manifest["forbidden_features_detected_in_inputs"],
        "forbidden_features_absent_from_gcn_inputs": feature_manifest["forbidden_features_detected_in_inputs"] == [],
        "proposed_no_leakage_gcn_input_columns": feature_manifest["proposed_no_leakage_gcn_input_columns"],
        "target_bus_memorization_risk_flagged": feature_manifest["target_bus_memorization_risk_flagged"],
        "strict_holdouts_complete": split_info["strict_holdouts_complete"],
        "required_strict_holdouts": split_info["required_strict_holdouts"],
        "baseline_comparison_complete": baseline_info["baseline_comparison_complete"],
        "baseline_models": baseline_info["baseline_models"],
        "b1_special_tracking_enabled": split_info["b1_special_tracking_enabled"],
        "nf06_sensitivity_enabled": split_info["nf06_sensitivity_enabled"],
        "l12_exclusion_check_enabled": split_info["l12_exclusion_check_enabled"],
        "old_formal_gate": dataset_info["old_formal_gate"],
        "l12_excluded": dataset_info["l12_excluded"],
        "nf06_provenance_warning_preserved": dataset_info["nf06_provenance_warning_preserved"],
        "warning_checks": warning_checks,
        "failed_checks": failed_checks,
        "dry_run_validator_passed": failed_checks == [],
        "should_run_formal_gcn_audit_now": False,
        "should_train_gcn_now": False,
        "recommended_next_step": (
            "prepare formal GCN usefulness audit execution in a separate round, still with no-leakage features and strict holdouts"
            if failed_checks == []
            else "fix dry-run blockers before any formal GCN audit"
        ),
        "dry_run": dry_run,
        "strict": strict,
    }
    return summary, feature_manifest


def run_validator(output_dir: Path, strict: bool = False, dry_run: bool = True) -> dict[str, Any]:
    summary, manifest = build_summary(strict=strict, dry_run=dry_run)
    execution_draft = _build_execution_draft(summary, manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "gcn_audit_dry_run_validator_summary.json", summary)
    _write_text(output_dir / "gcn_audit_dry_run_validator_summary.md", _render_md(summary))
    _write_summary_csv(output_dir / "gcn_audit_dry_run_validator_summary.csv", summary)
    _write_json(output_dir / "proposed_no_leakage_gcn_inputs_manifest.json", manifest)
    _write_text(output_dir / "proposed_no_leakage_gcn_inputs_manifest.md", _render_manifest_md(manifest))
    _write_json(output_dir / "formal_gcn_audit_execution_draft.json", execution_draft)
    _write_text(output_dir / "formal_gcn_audit_execution_draft.md", _render_execution_draft_md(execution_draft))
    _write_text(ROOT / "docs/ieee39_gcn_usefulness_audit_dry_run_validator.md", _render_round_doc(summary))
    if strict and not summary["dry_run_validator_passed"]:
        raise SystemExit(1)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IEEE39 GCN usefulness audit dry-run validator.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for dry-run validator artifacts.",
    )
    parser.add_argument("--strict", action="store_true", help="Return non-zero exit code if any check fails.")
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=True,
        help="Keep dry-run mode enabled. This is the default and only supported mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_validator(args.output_dir, strict=args.strict, dry_run=args.dry_run)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
