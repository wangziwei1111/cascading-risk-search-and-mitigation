"""Export IEEE39 non-line-trip dynamic label candidates.

This script consumes successful non-line-trip smoke-test rows and writes a
separate candidate export plus a v2 combined candidate schema. It deliberately
does not overwrite the existing formal IEEE39 dynamic label gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export"

EXPECTED_SMOKE_IDS = ["NF01", "NF02", "NF03", "NF04", "NF06"]
MEASUREMENT_COLUMNS = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "unstable_flag",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _validate_inputs(smoke: pd.DataFrame, smoke_report: dict[str, Any], quality: dict[str, Any], readiness: dict[str, Any]) -> None:
    requested = list(smoke_report.get("scenario_ids_requested", []))
    successful = list(smoke_report.get("scenario_ids_successful", []))
    if requested != EXPECTED_SMOKE_IDS or successful != EXPECTED_SMOKE_IDS:
        raise ValueError("Smoke report must request and succeed NF01/NF02/NF03/NF04/NF06 in order.")
    if smoke_report.get("scenario_ids_failed") != [] or smoke_report.get("scenario_ids_timeout") != []:
        raise ValueError("Smoke report contains failed or timeout scenarios.")
    if quality.get("num_training_ready_labels") != 35:
        raise ValueError("Original quality summary must preserve 35 training-ready labels.")
    if quality.get("num_training_ready_handwired_line_trip_labels") != 33:
        raise ValueError("Original quality summary must preserve 33 handwired line-trip labels.")
    if quality.get("num_unique_handwired_line_ids") != 33:
        raise ValueError("Original quality summary must preserve 33 unique handwired line IDs.")
    if readiness.get("num_training_ready_labels") != 35:
        raise ValueError("Original readiness summary must preserve 35 training-ready labels.")
    joined = smoke.to_json().lower()
    if "l12" in joined or "handwired_timed_breaker" in joined or "single_line_trip" in joined:
        raise ValueError("Smoke summary must not contain L12 or handwired line-trip rows.")
    for scenario_id in EXPECTED_SMOKE_IDS:
        if scenario_id not in set(smoke["scenario_id"].astype(str)):
            raise ValueError(f"Missing smoke scenario {scenario_id}.")


def _successful_smoke_candidates(smoke: pd.DataFrame) -> pd.DataFrame:
    mask = (
        smoke["scenario_id"].astype(str).isin(EXPECTED_SMOKE_IDS)
        & smoke["simulation_success"].map(_boolish)
        & smoke["physical_fault_or_breaker_action_executed"].map(_boolish)
        & smoke["training_ready_candidate_smoke"].map(_boolish)
        & smoke["measurement_extraction_status"].astype(str).eq("voltage_speed_angle")
        & smoke["signal_source_summary"].astype(str).str.contains("frequency=generator_speed_proxy", regex=False)
    )
    candidates = smoke.loc[mask].copy()
    if len(candidates) != 5:
        raise ValueError(f"Expected 5 successful smoke candidates, got {len(candidates)}.")
    candidates = candidates.sort_values("scenario_id").reset_index(drop=True)
    candidates["label_family"] = "non_line_trip"
    candidates["label_source"] = "smoke_test_export"
    candidates["export_status"] = "candidate_training_ready"
    candidates["training_ready_candidate"] = True
    candidates["training_ready_label_v2"] = True
    candidates["formal_line_trip_label"] = False
    candidates["handwired_line_trip_label"] = False
    candidates["non_line_trip_label"] = True
    candidates["source_smoke_scenario_id"] = candidates["scenario_id"].astype(str)
    candidates["schema_version"] = "ieee39_dynamic_label_schema_v2"
    candidates["provenance_check_required"] = False
    candidates["not_independent_physical_sample_until_verified"] = False
    candidates["duplicate_measurement_group"] = ""
    candidates["label_id_v2"] = candidates["scenario_id"].map(lambda x: f"non_line_trip_{x}")
    return candidates


def _measurement_key(row: pd.Series) -> tuple[Any, ...]:
    values: list[Any] = []
    for col in MEASUREMENT_COLUMNS:
        value = row[col]
        if isinstance(value, float):
            values.append(round(value, 12))
        else:
            values.append(value)
    return tuple(values)


def _annotate_duplicates(candidates: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    candidates = candidates.copy()
    candidates["_measurement_key"] = candidates.apply(_measurement_key, axis=1)
    groups: list[dict[str, Any]] = []
    group_index = 1
    for _, group in candidates.groupby("_measurement_key", sort=False):
        if len(group) <= 1:
            continue
        group_id = f"group_{group_index}"
        group_index += 1
        idx = group.index
        candidates.loc[idx, "duplicate_measurement_group"] = group_id
        scenario_ids = list(group["scenario_id"].astype(str))
        fault_types = sorted(set(group["fault_type"].astype(str)))
        metadata_cols = ["fault_start_s", "fault_clear_s", "duration_s"]
        same_timing = bool(group[metadata_cols].drop_duplicates().shape[0] == 1)
        groups.append(
            {
                "duplicate_measurement_group": group_id,
                "scenario_ids": scenario_ids,
                "fault_types": fault_types,
                "same_fault_start_clear_duration": same_timing,
                "output_summary_paths": list(group["output_summary_path"].astype(str)),
                "fault_type_differs_but_measurement_identical": len(fault_types) > 1,
                "note": _duplicate_note(scenario_ids),
            }
        )
    nf06_mask = candidates["scenario_id"].astype(str).eq("NF06")
    candidates.loc[nf06_mask, "provenance_check_required"] = True
    candidates.loc[nf06_mask, "not_independent_physical_sample_until_verified"] = True
    candidates = candidates.drop(columns=["_measurement_key"])
    report = {
        "num_duplicate_measurement_groups": len(groups),
        "duplicate_measurement_groups": groups,
        "measurement_identical_scenarios": [group["scenario_ids"] for group in groups],
        "same_timing_scenarios": _same_timing_groups(candidates),
        "nf01_nf04_nf06_conclusion": (
            "NF01 and NF04 are both existing three-phase fault block 0.10 s cases, so identical values are expected. "
            "NF06 is relay_proxy_fault_smoke but currently has measurements identical to the 0.10 s fault group, "
            "so it is retained but marked provenance_check_required and not_independent_physical_sample_until_verified."
        ),
        "provenance_check_required_scenarios": ["NF06"],
        "rows_deleted_due_to_duplicates": 0,
    }
    return candidates, report


def _duplicate_note(scenario_ids: list[str]) -> str:
    ids = set(scenario_ids)
    if {"NF01", "NF04"}.issubset(ids) and "NF06" in ids:
        return "NF01/NF04 duplicate timing is expected; NF06 needs provenance check because relay proxy measurements match the same group."
    if {"NF01", "NF04"}.issubset(ids):
        return "NF01 and NF04 are both 0.10 s existing three-phase fault block cases."
    return "Measurement-identical smoke candidates; review before treating as independent samples."


def _same_timing_groups(candidates: pd.DataFrame) -> list[dict[str, Any]]:
    groups = []
    for _, group in candidates.groupby(["fault_start_s", "fault_clear_s", "duration_s"], dropna=False):
        if len(group) <= 1:
            continue
        groups.append(
            {
                "scenario_ids": list(group["scenario_id"].astype(str)),
                "fault_start_s": float(group["fault_start_s"].iloc[0]),
                "fault_clear_s": float(group["fault_clear_s"].iloc[0]),
                "duration_s": float(group["duration_s"].iloc[0]),
                "fault_types": sorted(set(group["fault_type"].astype(str))),
            }
        )
    return groups


def _base_training_ready_v2(base: pd.DataFrame) -> pd.DataFrame:
    work = base[base["training_ready_candidate"].map(_boolish)].copy().reset_index(drop=True)
    if len(work) != 35:
        raise ValueError(f"Expected 35 original training-ready rows, got {len(work)}.")
    work["scenario_id"] = work.get("test_case", pd.Series([f"v1_{i:03d}" for i in range(len(work))])).astype(str)
    work["target_bus_or_component"] = work.get("tripped_line", "").astype(str)
    work["duration_s"] = (pd.to_numeric(work["fault_clear_s"], errors="coerce") - pd.to_numeric(work["fault_start_s"], errors="coerce")).clip(lower=0.0).fillna(0.0)
    work["label_family"] = "existing_formal_dynamic"
    work["label_source"] = "formal_v1_existing"
    work["export_status"] = "existing_training_ready"
    work["training_ready_label_v2"] = True
    work["formal_line_trip_label"] = work.get("trip_implementation", "").astype(str).eq("handwired_timed_breaker")
    work["handwired_line_trip_label"] = work["formal_line_trip_label"]
    work["non_line_trip_label"] = False
    work["source_smoke_scenario_id"] = ""
    work["schema_version"] = "ieee39_dynamic_label_schema_v2"
    work["provenance_check_required"] = False
    work["not_independent_physical_sample_until_verified"] = False
    work["duplicate_measurement_group"] = ""
    work["label_id_v2"] = [f"formal_v1_{i+1:03d}" for i in range(len(work))]
    return work


def _combined(base_v2: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    columns = list(dict.fromkeys(list(base_v2.columns) + list(candidates.columns)))
    return pd.concat([base_v2.reindex(columns=columns), candidates.reindex(columns=columns)], ignore_index=True)


def _write_duplicate_report(out_dir: Path, report: dict[str, Any]) -> None:
    _write_json(out_dir / "ieee39_non_line_trip_duplicate_provenance_report.json", report)
    lines = [
        "# IEEE39 Non-Line-Trip Duplicate / Provenance Report",
        "",
        f"- duplicate measurement groups: {report['num_duplicate_measurement_groups']}",
        f"- provenance check required scenarios: {', '.join(report['provenance_check_required_scenarios'])}",
        f"- rows deleted due to duplicates: {report['rows_deleted_due_to_duplicates']}",
        "",
        "## NF01 / NF04 / NF06",
        "",
        report["nf01_nf04_nf06_conclusion"],
        "",
        "Rows are retained, but duplicate/provenance flags must be reviewed before treating them as independent physical samples.",
    ]
    for group in report["duplicate_measurement_groups"]:
        lines.extend(
            [
                "",
                f"## {group['duplicate_measurement_group']}",
                "",
                f"- scenarios: {', '.join(group['scenario_ids'])}",
                f"- fault types: {', '.join(group['fault_types'])}",
                f"- same timing: {group['same_fault_start_clear_duration']}",
                f"- fault type differs with identical measurement: {group['fault_type_differs_but_measurement_identical']}",
                f"- note: {group['note']}",
            ]
        )
    (out_dir / "ieee39_non_line_trip_duplicate_provenance_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_quality_and_readiness(out_dir: Path, candidates: pd.DataFrame, combined: pd.DataFrame, duplicate_report: dict[str, Any]) -> None:
    quality = {
        "schema_version": "ieee39_dynamic_label_schema_v2",
        "original_formal_gate_preserved": True,
        "original_num_training_ready_labels": 35,
        "original_num_training_ready_handwired_line_trip_labels": 33,
        "original_num_unique_handwired_line_ids": 33,
        "num_non_line_trip_candidate_labels": int(len(candidates)),
        "num_training_ready_labels_v2_combined_candidate": int(len(combined)),
        "num_duplicate_measurement_groups": duplicate_report["num_duplicate_measurement_groups"],
        "duplicate_measurement_groups": duplicate_report["duplicate_measurement_groups"],
        "provenance_check_required_scenarios": duplicate_report["provenance_check_required_scenarios"],
        "l12_excluded": True,
        "l12_reason": "simulation_timeout / suspected islanding",
        "allowed_for_dynamic_aware_training_v2_preview": True,
        "should_retrain_reranker_now": False,
        "recommended_next_step": "Review duplicate/provenance warnings, especially NF06, then run a separate v2 preview training round.",
    }
    readiness = {
        "ready_for_v2_preview_training": True,
        "should_train_now": False,
        "reason": "The v2 candidate set is ready for a future preview training run, but this export round does not retrain. Duplicate/provenance checks should be reviewed first, especially NF06.",
        "caveats": [
            "phasor_RMS, not EMT",
            "generator_speed_proxy, not direct frequency",
            "relay proxy not engineering-grade protection",
            "duplicate smoke candidates are not necessarily independent physical samples",
            "preview-only, not final dynamic performance conclusion",
        ],
    }
    _write_json(out_dir / "ieee39_dynamic_label_quality_summary_v2_with_non_line_trip_candidates.json", quality)
    _write_json(out_dir / "ieee39_dynamic_aware_training_readiness_v2_with_non_line_trip_candidates.json", readiness)


def _write_outputs(out_dir: Path, candidates: pd.DataFrame, combined: pd.DataFrame, duplicate_report: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(out_dir / "ieee39_non_line_trip_dynamic_label_candidates.csv", index=False, encoding="utf-8")
    _write_json(out_dir / "ieee39_non_line_trip_dynamic_label_candidates.json", candidates.to_dict(orient="records"))
    combined.to_csv(out_dir / "ieee39_dynamic_label_schema_v2_combined_candidates.csv", index=False, encoding="utf-8")
    _write_json(out_dir / "ieee39_dynamic_label_schema_v2_combined_candidates.json", combined.to_dict(orient="records"))
    _write_duplicate_report(out_dir, duplicate_report)
    _write_quality_and_readiness(out_dir, candidates, combined, duplicate_report)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-summary", type=Path, required=True)
    parser.add_argument("--smoke-report", type=Path, required=True)
    parser.add_argument("--base-fault-summary", type=Path, required=True)
    parser.add_argument("--label-quality-summary", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    smoke = pd.read_csv(args.smoke_summary)
    smoke_report = _read_json(args.smoke_report)
    base = pd.read_csv(args.base_fault_summary)
    quality = _read_json(args.label_quality_summary)
    readiness = _read_json(args.readiness)
    _validate_inputs(smoke, smoke_report, quality, readiness)
    candidates = _successful_smoke_candidates(smoke)
    candidates, duplicate_report = _annotate_duplicates(candidates)
    base_v2 = _base_training_ready_v2(base)
    combined = _combined(base_v2, candidates)
    if len(combined) != 40:
        raise ValueError(f"Expected combined v2 row count 40, got {len(combined)}.")
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    _write_outputs(out_dir, candidates, combined, duplicate_report)
    print(f"Wrote IEEE39 non-line-trip label candidate export to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
