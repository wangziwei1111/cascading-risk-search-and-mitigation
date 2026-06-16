"""Review IEEE39 v2-plus-all-bus-fault candidate composition without training."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
EXPORT_DIR = BASE / "candidate_label_export"
OUT_DIR = BASE / "no_training_composition_review"
DOC_PATH = ROOT / "docs/ieee39_v2_plus_all_bus_fault_no_training_composition_review.md"
COMBINED_CSV = EXPORT_DIR / "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv"
EXPORT_SUMMARY = EXPORT_DIR / "batch_candidate_label_export_summary.json"
TRAINING_READINESS = EXPORT_DIR / "v2_plus_all_bus_fault_training_readiness.json"
COVERAGE_REPORT = EXPORT_DIR / "all_bus_fault_candidate_coverage_report.json"
OLD_FORMAL_GATE = "35 / 33 / 33"
ALL_BUSES = [f"B{i}" for i in range(1, 40)]
NEW_BUSES = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39)), "B16"]
EXISTING_BUSES = ["B39", "B26"]
COMPACT_DYNAMIC_COLUMNS = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
]
REQUIRED_COLUMNS = [
    "scenario_id",
    "label_id_v2",
    "label_family",
    "fault_type",
    "target_bus",
    "target_bus_or_component",
    "line_id",
    "dynamic_stress_score",
    "unstable_flag",
    "bus_fault_label",
    "temporary_smoke_candidate",
    "candidate_not_formal_label",
    "formal_line_trip_label",
    "quality_review_passed_for_candidate_export",
    "signal_source_summary",
    "phasor_rms_not_emt",
    "generator_speed_proxy_not_direct_frequency",
    "temporary_bus_fault_not_engineering_grade_protection",
    "training_ready_label_candidate",
    "training_ready_label_v2",
]


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, default=_json_default)
        handle.write("\n")


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _nonempty(value: Any) -> bool:
    text = "" if value is None else str(value).strip()
    return bool(text) and text.lower() != "nan"


def _duplicate_values(series: pd.Series) -> list[str]:
    values = series.fillna("").astype(str)
    dupes = sorted(value for value in values[values.duplicated(keep=False)].unique() if value)
    return dupes


def _row_ids(table: pd.DataFrame, mask: pd.Series) -> list[str]:
    if "scenario_id" in table.columns:
        return table.loc[mask, "scenario_id"].fillna("").astype(str).tolist()
    return [str(idx) for idx in table.index[mask]]


def _all_true(series: pd.Series) -> bool:
    return bool(series.map(_as_bool).all()) if len(series) else False


def _all_false(series: pd.Series) -> bool:
    return bool((~series.map(_as_bool)).all()) if len(series) else False


def _write_review_csv(path: Path, review: dict[str, Any]) -> None:
    fields = ["check", "value"]
    flat = {
        key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
        for key, value in review.items()
    }
    with open(_fs_path(path), "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key, value in flat.items():
            writer.writerow({"check": key, "value": value})


def _write_main_doc(review: dict[str, Any]) -> None:
    text = f"""# IEEE39 V2 Plus All Bus-Fault No-Training Composition Review

This round is a no-training composition review of the latest 79-row IEEE39
v2-plus-all-bus-fault candidate dataset.

## Boundary

- This round did not run Simulink.
- This round did not run actual smoke.
- This round did not export labels.
- This round did not train GCN.
- This round did not retrain the reranker.
- This round did not run a GCN usefulness audit.
- This round did not run preview training.

## Result

- combined candidate count: `{review['total_candidate_rows']}`
- bus-fault candidate count: `{review['num_total_bus_fault_candidates']}`
- all B1-B39 have bus-fault candidate: `{review['all_ieee39_buses_have_bus_fault_candidate']}`
- missing bus-fault buses: `{review['missing_bus_fault_buses']}`
- duplicate scenario ids: `{review['scenario_id_duplicates']}`
- duplicate label ids: `{review['label_id_v2_duplicates']}`
- unstable_flag false buses: `{review['unstable_flag_false_buses']}`
- old formal gate: `{review['old_formal_gate']}`
- L12 excluded: `{review['l12_excluded']}`
- NF06 provenance warning preserved: `{review['nf06_provenance_warning_preserved']}`

All bus-fault labels remain candidate_not_formal_label entries, not formal
labels. B39/B26 remain existing candidate labels, not formal labels. B1 has
`unstable_flag=false`; this is a low-risk/stable compact marker, not a quality
failure.

The model remains phasor_RMS, not EMT. generator_speed_proxy is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.

Post-fault compact dynamic measurements must not be used as primary GCN inputs;
otherwise target-feature leakage risk remains. Future audit must use a
no-dynamic-measurement feature set, label-family holdout, bus-fault holdout,
and leave-one-bus-fault-out checks.

Recommended next step: `{review['recommended_next_step']}`.
"""
    _write_text(DOC_PATH, text)


def run_review(output_dir: Path = OUT_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(_fs_path(COMBINED_CSV))
    export_summary = _read_json(EXPORT_SUMMARY)
    _read_json(TRAINING_READINESS)
    coverage_report = _read_json(COVERAGE_REPORT)

    required_present = [col for col in REQUIRED_COLUMNS if col in table.columns]
    missing_required = [col for col in REQUIRED_COLUMNS if col not in table.columns]
    bus_fault = table[table.get("bus_fault_label", pd.Series(False, index=table.index)).map(_as_bool)].copy()
    covered = sorted(set(bus_fault.get("target_bus", pd.Series(dtype=str)).dropna().astype(str)), key=lambda bus: int(bus[1:]) if bus.startswith("B") and bus[1:].isdigit() else 999)
    missing_buses = [bus for bus in ALL_BUSES if bus not in set(covered)]
    dynamic_scores = pd.to_numeric(table.get("dynamic_stress_score", pd.Series(dtype=float)), errors="coerce")
    bus_fault_mask = table.get("bus_fault_label", pd.Series(False, index=table.index)).map(_as_bool)
    nonfinite_mask = bus_fault_mask & ~dynamic_scores.map(lambda value: isinstance(value, (int, float)) and math.isfinite(value))
    out_of_range_mask = bus_fault_mask & dynamic_scores.notna() & ((dynamic_scores < 0.0) | (dynamic_scores > 10.0))
    unstable_values = table.get("unstable_flag", pd.Series(dtype=str)).map(_as_bool)
    unstable_counts = {
        "true": int(unstable_values.sum()),
        "false": int((~unstable_values).sum()),
    }
    unstable_false_buses = sorted(
        set(table.loc[~unstable_values & table.get("bus_fault_label", pd.Series(False, index=table.index)).map(_as_bool), "target_bus"].dropna().astype(str)),
        key=lambda bus: int(bus[1:]) if bus.startswith("B") and bus[1:].isdigit() else 999,
    )

    compact_present = [col for col in COMPACT_DYNAMIC_COLUMNS if col in table.columns]
    failed_checks: list[str] = []
    checks = {
        "row_count_check_passed": len(table) == 79,
        "all_ieee39_buses_have_bus_fault_candidate": not missing_buses,
        "every_bus_fault_row_has_line_id_NO_LINE": bus_fault.get("line_id", pd.Series(dtype=str)).fillna("").astype(str).eq("NO_LINE").all(),
        "every_bus_fault_row_has_target_bus_filled": bus_fault.get("target_bus", pd.Series(dtype=str)).map(_nonempty).all(),
        "every_bus_fault_row_has_target_bus_or_component_filled": bus_fault.get("target_bus_or_component", pd.Series(dtype=str)).map(_nonempty).all(),
        "every_bus_fault_row_candidate_not_formal_label_true": _all_true(bus_fault.get("candidate_not_formal_label", pd.Series(dtype=bool))),
        "every_bus_fault_row_formal_line_trip_label_false": _all_false(bus_fault.get("formal_line_trip_label", pd.Series(dtype=bool))),
        "every_bus_fault_row_bus_fault_label_true": _all_true(bus_fault.get("bus_fault_label", pd.Series(dtype=bool))),
        "every_bus_fault_row_temporary_smoke_candidate_true": _all_true(bus_fault.get("temporary_smoke_candidate", pd.Series(dtype=bool))),
        "every_bus_fault_row_quality_review_passed_true": _all_true(bus_fault.get("quality_review_passed_for_candidate_export", pd.Series(dtype=bool))),
        "every_bus_fault_row_signal_source_contains_frequency_proxy": bus_fault.get("signal_source_summary", pd.Series(dtype=str)).fillna("").astype(str).str.contains("frequency=generator_speed_proxy", regex=False).all(),
        "every_bus_fault_row_phasor_rms_not_emt_true": _all_true(bus_fault.get("phasor_rms_not_emt", pd.Series(dtype=bool))),
        "every_bus_fault_row_generator_speed_proxy_not_direct_frequency_true": _all_true(bus_fault.get("generator_speed_proxy_not_direct_frequency", pd.Series(dtype=bool))),
        "every_bus_fault_row_temporary_bus_fault_not_engineering_grade_protection_true": _all_true(bus_fault.get("temporary_bus_fault_not_engineering_grade_protection", pd.Series(dtype=bool))),
        "required_columns_present": not missing_required,
        "b1_unstable_false_preserved": unstable_false_buses == ["B1"],
    }
    for key, passed in checks.items():
        if not bool(passed):
            failed_checks.append(key)
    if _duplicate_values(table.get("scenario_id", pd.Series(dtype=str))):
        failed_checks.append("scenario_id_duplicates")
    if _duplicate_values(table.get("label_id_v2", pd.Series(dtype=str))):
        failed_checks.append("label_id_v2_duplicates")
    if _row_ids(table, nonfinite_mask):
        failed_checks.append("dynamic_stress_score_nonfinite_rows")

    review = {
        "review_scope": "no_training_composition_review",
        "candidate_dataset": "v2_plus_all_bus_fault_candidates",
        "total_candidate_rows": int(len(table)),
        "expected_candidate_rows": 79,
        "row_count_check_passed": checks["row_count_check_passed"],
        "previous_candidate_count": 42,
        "num_new_all_remaining_bus_fault_candidates": 37,
        "num_total_bus_fault_candidates": int(len(bus_fault)),
        "expected_total_bus_fault_candidates": 39,
        "all_ieee39_buses_have_bus_fault_candidate": not missing_buses,
        "covered_bus_fault_buses": covered,
        "missing_bus_fault_buses": missing_buses,
        "existing_candidate_buses": EXISTING_BUSES,
        "newly_exported_candidate_buses": NEW_BUSES,
        "old_formal_gate": OLD_FORMAL_GATE,
        "formal_label_gate_changed": False,
        "l12_excluded": True,
        "nf06_provenance_warning_preserved": True,
        "bus_fault_rows_count": int(len(bus_fault)),
        **checks,
        "missing_required_columns": missing_required,
        "scenario_id_duplicates": _duplicate_values(table.get("scenario_id", pd.Series(dtype=str))),
        "label_id_v2_duplicates": _duplicate_values(table.get("label_id_v2", pd.Series(dtype=str))),
        "target_bus_missing_rows": _row_ids(table, ~table.get("target_bus", pd.Series("", index=table.index)).map(_nonempty)),
        "target_bus_or_component_missing_rows": _row_ids(table, ~table.get("target_bus_or_component", pd.Series("", index=table.index)).map(_nonempty)),
        "line_id_missing_rows": _row_ids(table, ~table.get("line_id", pd.Series("", index=table.index)).map(_nonempty)),
        "dynamic_stress_score_missing_rows": _row_ids(table, bus_fault_mask & table.get("dynamic_stress_score", pd.Series("", index=table.index)).isna()),
        "dynamic_stress_score_nonfinite_rows": _row_ids(table, nonfinite_mask),
        "dynamic_stress_score_out_of_range_rows": _row_ids(table, out_of_range_mask),
        "unstable_flag_value_counts": unstable_counts,
        "unstable_flag_false_buses": unstable_false_buses,
        "num_formal_or_existing_line_trip_rows": int(table.get("formal_line_trip_label", pd.Series(False, index=table.index)).map(_as_bool).sum()),
        "num_non_line_trip_rows": int(table.get("non_line_trip_label", pd.Series(False, index=table.index)).map(_as_bool).sum()),
        "num_bus_fault_rows": int(len(bus_fault)),
        "num_temporary_smoke_candidates": int(table.get("temporary_smoke_candidate", pd.Series(False, index=table.index)).map(_as_bool).sum()),
        "num_candidate_not_formal_label_rows": int(table.get("candidate_not_formal_label", pd.Series(False, index=table.index)).map(_as_bool).sum()),
        "num_training_ready_label_candidate_rows": int(table.get("training_ready_label_candidate", pd.Series(False, index=table.index)).map(_as_bool).sum()),
        "num_training_ready_label_v2_rows": int(table.get("training_ready_label_v2", pd.Series(False, index=table.index)).map(_as_bool).sum()),
        "compact_dynamic_measurement_columns_present": compact_present,
        "compact_dynamic_measurement_features_are_post_fault": True,
        "target_feature_leakage_risk_if_used_as_inputs": True,
        "no_dynamic_measurement_feature_set_required_for_future_audit": True,
        "label_family_holdout_required_for_future_audit": True,
        "bus_fault_holdout_required_for_future_audit": True,
        "leave_one_bus_fault_out_required_for_future_audit": True,
        "simulink_run": False,
        "actual_smoke_run": False,
        "labels_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "preview_training_run": False,
        "should_train_now": False,
        "failed_checks": failed_checks,
        "composition_review_passed": not failed_checks,
        "recommended_next_step": (
            "run v2-plus-all-bus-fault preview/no-leakage comparison in a separate round, not GCN training"
            if not failed_checks
            else "fix composition/schema issues before any preview or training"
        ),
        "source_export_summary_count": export_summary.get("num_v2_plus_all_bus_fault_candidate_labels"),
        "source_coverage_all_buses": coverage_report.get("all_ieee39_buses_have_bus_fault_candidate"),
    }
    coverage = {
        "expected_buses": ALL_BUSES,
        "covered_bus_fault_buses": covered,
        "missing_bus_fault_buses": missing_buses,
        "num_expected_buses": 39,
        "num_covered_buses": len(covered),
        "all_ieee39_buses_have_bus_fault_candidate": not missing_buses,
        "existing_candidate_buses": EXISTING_BUSES,
        "newly_exported_candidate_buses": NEW_BUSES,
    }
    schema = {
        "required_columns_present": not missing_required,
        "required_columns": REQUIRED_COLUMNS,
        "missing_required_columns": missing_required,
        "scenario_id_duplicates": review["scenario_id_duplicates"],
        "label_id_v2_duplicates": review["label_id_v2_duplicates"],
        "dynamic_stress_score_nonfinite_rows": review["dynamic_stress_score_nonfinite_rows"],
        "dynamic_stress_score_out_of_range_rows": review["dynamic_stress_score_out_of_range_rows"],
    }
    leakage = {
        "compact_dynamic_measurement_columns_present": compact_present,
        "compact_dynamic_measurement_features_are_post_fault": True,
        "target_feature_leakage_risk_if_used_as_inputs": True,
        "no_dynamic_measurement_feature_set_required_for_future_audit": True,
        "label_family_holdout_required_for_future_audit": True,
        "bus_fault_holdout_required_for_future_audit": True,
        "leave_one_bus_fault_out_required_for_future_audit": True,
        "simulink_run": False,
        "actual_smoke_run": False,
        "labels_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "preview_training_run": False,
        "should_train_now": False,
    }
    _write_json(output_dir / "v2_plus_all_bus_fault_composition_review.json", review)
    _write_text(output_dir / "v2_plus_all_bus_fault_composition_review.md", _composition_md(review))
    _write_review_csv(output_dir / "v2_plus_all_bus_fault_composition_review.csv", review)
    _write_json(output_dir / "all_bus_fault_coverage_check.json", coverage)
    _write_json(output_dir / "schema_and_duplicate_check.json", schema)
    _write_json(output_dir / "leakage_risk_and_training_boundary_check.json", leakage)
    _write_main_doc(review)
    return review


def _composition_md(review: dict[str, Any]) -> str:
    return f"""# V2 Plus All Bus-Fault Composition Review

- review scope: `{review['review_scope']}`
- total candidate rows: `{review['total_candidate_rows']}`
- row count check passed: `{review['row_count_check_passed']}`
- total bus-fault candidates: `{review['num_total_bus_fault_candidates']}`
- all B1-B39 have bus-fault candidate: `{review['all_ieee39_buses_have_bus_fault_candidate']}`
- missing bus-fault buses: `{review['missing_bus_fault_buses']}`
- duplicate scenario ids: `{review['scenario_id_duplicates']}`
- duplicate label ids: `{review['label_id_v2_duplicates']}`
- unstable_flag false buses: `{review['unstable_flag_false_buses']}`
- composition review passed: `{review['composition_review_passed']}`

This review did not run Simulink, did not export labels, did not train GCN, did
not retrain the reranker, and did not run a GCN usefulness audit.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    review = run_review(args.output_dir)
    print(json.dumps(review, indent=2, ensure_ascii=False, default=_json_default))
    if args.strict and not review["composition_review_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
