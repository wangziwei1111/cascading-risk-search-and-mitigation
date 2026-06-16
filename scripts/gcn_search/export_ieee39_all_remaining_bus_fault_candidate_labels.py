"""Export candidate-only labels for all remaining IEEE39 bus-fault smoke cases.

This script reads the batch smoke quality-review artifacts and appends the 37
quality-passed all-remaining bus-fault cases to the existing 42-row
v2-plus-B39+B26 candidate dataset. It does not run Simulink, run actual smoke,
train GCN, retrain the reranker, or run a GCN usefulness audit.
"""

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
BATCH_ID = "bus_fault_all_remaining_manual_wiring"
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
QUALITY_DIR = BASE / "batch_smoke_quality_review"
EXISTING_42 = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/"
    "ieee39_dynamic_label_schema_v2_plus_b39_b26_candidate.csv"
)
DEFAULT_OUT = BASE / "candidate_label_export"
DOC_PATH = ROOT / "docs/ieee39_all_remaining_bus_fault_candidate_label_export.md"
OLD_FORMAL_GATE = "35 / 33 / 33"
PREVIOUS_CANDIDATE_COUNT = 42
NEW_CANDIDATE_COUNT = 37
COMBINED_CANDIDATE_COUNT = 79
TOTAL_BUS_FAULT_CANDIDATES = 39

NORMAL_BUSES = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
ALL_NEW_BUSES = NORMAL_BUSES + ["B16"]
ALL_IEEE39_BUSES = [f"B{i}" for i in range(1, 40)]
EXISTING_BUS_FAULT_BUSES = ["B39", "B26"]


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
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _finite_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _dynamic_stress_score(record: dict[str, Any]) -> float:
    min_voltage = _finite_float(record.get("min_voltage_pu"), 1.0)
    min_frequency = _finite_float(record.get("min_frequency_hz"), 50.0)
    max_frequency = _finite_float(record.get("max_frequency_hz"), 50.0)
    speed = abs(_finite_float(record.get("max_speed_deviation"), 0.0))
    angle = max(0.0, _finite_float(record.get("max_rotor_angle_separation_deg"), 0.0))
    voltage_sag = max(0.0, 1.0 - min_voltage)
    frequency_excursion_hz = max(abs(min_frequency - 50.0), abs(max_frequency - 50.0))
    return 0.35 * voltage_sag + 0.25 * frequency_excursion_hz + 0.20 * (speed * 100.0) + 0.20 * (angle / 180.0)


def _candidate_from_review(review: dict[str, Any]) -> dict[str, Any]:
    bus = str(review["target_bus"])
    return {
        "test_case": f"{bus.lower()}_temporary_bus_fault_smoke",
        "simulation_success": True,
        "physical_fault_or_breaker_action_executed": True,
        "schema_only": False,
        "simulation_mode": "graphical_simulink_phasor_RMS",
        "trip_implementation": "temporary_bus_fault",
        "fault_configuration_status": "configured",
        "measurement_extraction_status": "voltage_speed_angle",
        "training_ready_candidate": True,
        "timeout_or_error_message": "",
        "fault_type": "three_phase_bus_fault_temp_smoke",
        "fault_start_s": 0.5,
        "fault_clear_s": 0.58,
        "tripped_line": "NO_LINE",
        "relay_operated": False,
        "breaker_opened": False,
        "min_voltage_pu": review["min_voltage_pu"],
        "max_voltage_pu": review["max_voltage_pu"],
        "min_frequency_hz": review["min_frequency_hz"],
        "max_frequency_hz": review["max_frequency_hz"],
        "max_speed_deviation": review["max_speed_deviation"],
        "max_rotor_angle_separation_deg": review["max_rotor_angle_separation_deg"],
        "signal_source_summary": review["signal_source_summary"],
        "unstable_flag": bool(review["unstable_flag"]),
        "trip_time_s": 0.5,
        "note": f"{bus} temporary bus-fault smoke candidate only; not formal label; not GCN training; not reranker retraining.",
        "source_model": f"IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_{bus}_TEMP_LOCAL_ONLY",
        "scenario_id": f"BF_{bus}_TEMP_SMOKE",
        "target_bus_or_component": bus,
        "duration_s": 0.08,
        "label_family": "non_line_trip",
        "label_source": "all_remaining_bus_fault_batch_smoke_quality_review",
        "export_status": "candidate_only",
        "training_ready_label_v2": True,
        "formal_line_trip_label": False,
        "handwired_line_trip_label": False,
        "non_line_trip_label": True,
        "source_smoke_scenario_id": f"BF_{bus}_TEMP_SMOKE",
        "schema_version": "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates",
        "provenance_check_required": False,
        "not_independent_physical_sample_until_verified": False,
        "duplicate_measurement_group": "",
        "label_id_v2": f"{bus.lower()}_bus_fault_candidate_001",
        "training_ready_candidate_smoke": True,
        "output_summary_path": review["source_smoke_summary_path"],
        "output_event_log_path": "",
        "target_bus": bus,
        "line_id": "NO_LINE",
        "bus_fault_label": True,
        "temporary_smoke_candidate": True,
        "candidate_not_formal_label": True,
        "source_model_type": "temporary_local_lab_copy",
        "source_slx_modified": False,
        "temporary_slx_committed": False,
        "human_verified_injection_point": True,
        "quality_review_passed_for_candidate_export": True,
        "training_ready_label_candidate": True,
        "selected_fault_block_path": f"Grid/Fault_{bus}_TEMP",
        "selected_injection_block_path": f"Grid/Fault_{bus}_TEMP",
        "dynamic_stress_score": _dynamic_stress_score(review),
        "phasor_rms_not_emt": True,
        "generator_speed_proxy_not_direct_frequency": True,
        "temporary_bus_fault_not_engineering_grade_protection": True,
        "labels_exported_this_round": "candidate_only",
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "old_formal_gate": OLD_FORMAL_GATE,
        "previous_candidate_count": PREVIOUS_CANDIDATE_COUNT,
        "num_new_all_remaining_bus_fault_candidates": NEW_CANDIDATE_COUNT,
        "num_v2_plus_all_bus_fault_candidate_labels": COMBINED_CANDIDATE_COUNT,
        "b39_b26_status": "existing_candidate_labels_not_formal",
        "l12_excluded": True,
        "nf06_provenance_warning_preserved": True,
    }


def _write_single_candidate(out_dir: Path, candidate: dict[str, Any]) -> None:
    bus = str(candidate["target_bus"])
    _write_json(out_dir / f"candidate_label_{bus}.json", candidate)
    with open(_fs_path(out_dir / f"candidate_label_{bus}.csv"), "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(candidate.keys()))
        writer.writeheader()
        writer.writerow(candidate)


def _write_summary_csv(path: Path, candidates: list[dict[str, Any]]) -> None:
    fields = [
        "target_bus",
        "scenario_id",
        "label_id_v2",
        "dynamic_stress_score",
        "unstable_flag",
        "min_voltage_pu",
        "max_frequency_hz",
        "max_rotor_angle_separation_deg",
        "candidate_not_formal_label",
        "labels_exported_this_round",
    ]
    with open(_fs_path(path), "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow({field: candidate.get(field) for field in fields})


def _align_and_combine(existing: pd.DataFrame, candidates: list[dict[str, Any]]) -> pd.DataFrame:
    existing = _normalize_existing_bus_fault_rows(existing.copy())
    new_df = pd.DataFrame(candidates)
    for col in existing.columns:
        if col not in new_df.columns:
            new_df[col] = ""
    for col in new_df.columns:
        if col not in existing.columns:
            existing[col] = ""
    return pd.concat([existing, new_df[existing.columns]], ignore_index=True)


def _normalize_existing_bus_fault_rows(existing: pd.DataFrame) -> pd.DataFrame:
    if "bus_fault_label" not in existing.columns:
        return existing
    mask = existing["bus_fault_label"].map(_as_bool)
    for idx, row in existing.loc[mask].iterrows():
        bus = str(row.get("target_bus") or row.get("target_bus_or_component") or "").strip()
        scenario = str(row.get("scenario_id") or "")
        if not bus and scenario.startswith("BF_B") and "_TEMP" in scenario:
            bus = scenario.removeprefix("BF_").split("_TEMP", 1)[0]
        if bus:
            existing.at[idx, "target_bus"] = bus
            existing.at[idx, "target_bus_or_component"] = bus
            if not str(row.get("selected_fault_block_path") or "").strip() or str(row.get("selected_fault_block_path")).lower() == "nan":
                existing.at[idx, "selected_fault_block_path"] = f"Grid/Fault_{bus}_TEMP"
            if not str(row.get("selected_injection_block_path") or "").strip() or str(row.get("selected_injection_block_path")).lower() == "nan":
                existing.at[idx, "selected_injection_block_path"] = f"Grid/Fault_{bus}_TEMP"
        existing.at[idx, "line_id"] = "NO_LINE"
        for col in [
            "quality_review_passed_for_candidate_export",
            "training_ready_label_candidate",
            "phasor_rms_not_emt",
            "generator_speed_proxy_not_direct_frequency",
            "temporary_bus_fault_not_engineering_grade_protection",
        ]:
            if col in existing.columns:
                existing.at[idx, col] = True
        for col in ["source_slx_modified", "temporary_slx_committed", "gcn_trained", "reranker_retrained", "gcn_usefulness_audit_run"]:
            if col in existing.columns:
                existing.at[idx, col] = False
        if "labels_exported_this_round" in existing.columns:
            existing.at[idx, "labels_exported_this_round"] = "candidate_only"
        if "old_formal_gate" in existing.columns:
            existing.at[idx, "old_formal_gate"] = OLD_FORMAL_GATE
        if "b39_b26_status" in existing.columns:
            existing.at[idx, "b39_b26_status"] = "existing_candidate_labels_not_formal"
        for col in ["l12_excluded", "nf06_provenance_warning_preserved"]:
            if col in existing.columns:
                existing.at[idx, col] = True
        if "dynamic_stress_score" in existing.columns and not _is_finite_value(row.get("dynamic_stress_score")):
            existing.at[idx, "dynamic_stress_score"] = _dynamic_stress_score(row.to_dict())
    return existing


def _is_finite_value(value: Any) -> bool:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(parsed)


def _write_doc(summary: dict[str, Any]) -> None:
    buses = ", ".join(summary["new_candidate_buses"])
    text = f"""# IEEE39 All-Remaining Bus-Fault Candidate Label Export

This round is candidate-only export for the 37 IEEE39 all-remaining bus-fault
temporary smoke samples that passed batch smoke quality review.

## Boundary

- This round did not run Simulink.
- This round did not run actual smoke.
- This round exported candidate labels only.
- This round did not train GCN.
- This round did not retrain the reranker.
- This round did not run a GCN usefulness audit.
- The 37 quality-passed buses were exported as candidate labels.
- All bus-fault candidates remain candidate_not_formal_label, not formal labels.
- Old formal gate remains 35 / 33 / 33.
- L12 remains excluded.
- NF06 provenance warning is preserved.

## Result

- previous candidate count: `{summary['previous_candidate_count']}`
- new all-remaining bus-fault candidates: `{summary['num_new_all_remaining_bus_fault_candidates']}`
- combined candidate count: `{summary['num_v2_plus_all_bus_fault_candidate_labels']}`
- total bus-fault candidates: `{summary['num_total_bus_fault_candidates']}`
- all IEEE39 buses have bus-fault candidate: `{summary['all_ieee39_buses_have_bus_fault_candidate']}`
- unstable_flag false buses: `{summary['unstable_flag_false_buses']}`
- new candidate buses: `{buses}`

B1 has `unstable_flag=false`, but it still passed quality review. The
`unstable_flag` value is a compact smoke threshold marker, not an export
quality criterion.

The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct
frequency. In plain text: generator_speed_proxy is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.
Post-fault compact dynamic measurements should not be used as main GCN inputs,
otherwise target-feature leakage risk remains.

## Next Step

Run v2-plus-all-bus-fault no-training composition review before any training.
Do not train GCN and do not retrain the reranker in the next check step.
"""
    _write_text(DOC_PATH, text)


def _write_coverage(out_dir: Path, candidate_buses: list[str]) -> dict[str, Any]:
    covered = sorted(candidate_buses, key=lambda bus: int(bus[1:]))
    missing = [bus for bus in ALL_IEEE39_BUSES if bus not in set(covered)]
    report = {
        "expected_buses": ALL_IEEE39_BUSES,
        "covered_buses": covered,
        "missing_buses": missing,
        "num_expected_buses": 39,
        "num_covered_buses": len(covered),
        "all_ieee39_buses_have_bus_fault_candidate": not missing,
        "existing_candidates": EXISTING_BUS_FAULT_BUSES,
        "newly_exported_candidates": ALL_NEW_BUSES,
        "candidate_not_formal_label_for_all": True,
    }
    _write_json(out_dir / "all_bus_fault_candidate_coverage_report.json", report)
    _write_text(
        out_dir / "all_bus_fault_candidate_coverage_report.md",
        f"""# All Bus-Fault Candidate Coverage Report

- expected buses: `39`
- covered buses: `{len(covered)}`
- missing buses: `{', '.join(missing) if missing else 'none'}`
- existing candidates: `B39, B26`
- newly exported candidates: `{', '.join(ALL_NEW_BUSES)}`
- all bus-fault labels are candidate_not_formal_label: `true`
""",
    )
    return report


def _write_blocker(out_dir: Path, reason: str, payload: dict[str, Any]) -> None:
    _write_json(out_dir / "candidate_label_export_blocker_report.json", {"reason": reason, "payload": payload})


def run_export(out_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    quality_summary = _read_json(QUALITY_DIR / "batch_smoke_quality_review_summary.json")
    eligible = _read_json(QUALITY_DIR / "buses_eligible_for_candidate_export.json")
    if eligible.get("eligible_count") != 37 or eligible.get("blocked_count") != 0:
        _write_blocker(out_dir, "eligible_or_blocked_count_mismatch", {"eligible": eligible, "quality_summary": quality_summary})
        raise RuntimeError("Eligible count must be 37 and blocked count must be 0.")
    eligible_buses = eligible["eligible_buses"]
    if set(eligible_buses) != set(ALL_NEW_BUSES):
        _write_blocker(out_dir, "eligible_bus_set_mismatch", {"eligible_buses": eligible_buses})
        raise RuntimeError("Eligible bus set does not match all new buses.")

    existing = pd.read_csv(EXISTING_42)
    if len(existing) != PREVIOUS_CANDIDATE_COUNT:
        _write_blocker(out_dir, "existing_candidate_count_mismatch", {"row_count": int(len(existing))})
        raise RuntimeError("Existing v2-plus-B39+B26 dataset must contain 42 rows.")

    candidates: list[dict[str, Any]] = []
    for bus in eligible_buses:
        review = _read_json(QUALITY_DIR / f"smoke_quality_review_{bus}.json")
        if review.get("quality_review_passed_for_candidate_export") is not True:
            _write_blocker(out_dir, "quality_review_not_passed", {"bus": bus, "review": review})
            raise RuntimeError(f"{bus} did not pass quality review.")
        candidate = _candidate_from_review(review)
        candidates.append(candidate)
        _write_single_candidate(out_dir, candidate)

    combined = _align_and_combine(existing.copy(), candidates)
    if len(combined) != COMBINED_CANDIDATE_COUNT:
        _write_blocker(out_dir, "combined_count_mismatch", {"combined_count": int(len(combined))})
        raise RuntimeError("Combined dataset must contain 79 rows.")
    combined_path = out_dir / "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv"
    combined.to_csv(_fs_path(combined_path), index=False, encoding="utf-8-sig")

    bus_fault = combined[combined["bus_fault_label"].map(_as_bool)].copy()
    bus_fault_buses = sorted(set(bus_fault["target_bus"].dropna().astype(str)), key=lambda bus: int(bus[1:]) if bus.startswith("B") and bus[1:].isdigit() else 999)
    coverage = _write_coverage(out_dir, bus_fault_buses)
    unstable_false_buses = [candidate["target_bus"] for candidate in candidates if candidate["unstable_flag"] is False]
    summary = {
        "export_scope": "candidate_only",
        "previous_candidate_count": PREVIOUS_CANDIDATE_COUNT,
        "num_new_all_remaining_bus_fault_candidates": len(candidates),
        "num_v2_plus_all_bus_fault_candidate_labels": len(combined),
        "num_total_bus_fault_candidates": int(len(bus_fault)),
        "all_ieee39_buses_have_bus_fault_candidate": coverage["all_ieee39_buses_have_bus_fault_candidate"],
        "new_candidate_buses": eligible_buses,
        "existing_candidate_buses": EXISTING_BUS_FAULT_BUSES,
        "unstable_flag_true_count_new_candidates": sum(1 for candidate in candidates if candidate["unstable_flag"] is True),
        "unstable_flag_false_count_new_candidates": len(unstable_false_buses),
        "unstable_flag_false_buses": unstable_false_buses,
        "quality_review_passed_count": quality_summary["num_quality_review_passed"],
        "quality_review_failed_count": quality_summary["num_quality_review_failed"],
        "formal_label_gate_changed": False,
        "old_formal_gate": OLD_FORMAL_GATE,
        "b39_b26_status": "existing_candidate_labels_not_formal",
        "l12_excluded": True,
        "nf06_provenance_warning_preserved": True,
        "labels_exported_this_round": "candidate_only",
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "should_train_now": False,
        "recommended_next_step": "run v2-plus-all-bus-fault no-training composition review before any training",
    }
    _write_json(out_dir / "batch_candidate_label_export_summary.json", summary)
    _write_text(
        out_dir / "batch_candidate_label_export_summary.md",
        f"""# Batch Candidate Label Export Summary

- export scope: `candidate_only`
- previous candidate count: `{PREVIOUS_CANDIDATE_COUNT}`
- new all-remaining bus-fault candidates: `{len(candidates)}`
- combined candidate count: `{len(combined)}`
- total bus-fault candidates: `{len(bus_fault)}`
- all IEEE39 buses have bus-fault candidate: `{coverage['all_ieee39_buses_have_bus_fault_candidate']}`
- unstable_flag false buses: `{unstable_false_buses}`
- old formal gate: `{OLD_FORMAL_GATE}`
- GCN trained: `false`
- reranker retrained: `false`
- GCN usefulness audit run: `false`

Next step: run v2-plus-all-bus-fault no-training composition review before any
training.
""",
    )
    _write_summary_csv(out_dir / "batch_candidate_label_export_summary.csv", candidates)
    _write_json(
        out_dir / "v2_plus_all_bus_fault_training_readiness.json",
        {
            "ready_for_future_preview_training": True,
            "should_train_now": False,
            "reason": "export-only round; run no-training composition review first",
            "candidate_count": COMBINED_CANDIDATE_COUNT,
            "num_bus_fault_candidates": int(len(bus_fault)),
            "all_ieee39_buses_have_bus_fault_candidate": coverage["all_ieee39_buses_have_bus_fault_candidate"],
            "b39_b26_existing_candidates_preserved": True,
            "new_all_remaining_bus_fault_candidates": len(candidates),
            "caveats": [
                "all bus-fault labels are temporary smoke candidates, not formal labels",
                "phasor_RMS not EMT",
                "generator_speed_proxy not direct frequency",
                "temporary bus-fault injection not engineering-grade protection",
                "target-feature leakage risk remains if compact dynamic measurements are used as input features",
                "no-training composition review is required before any preview or GCN audit",
                "formal GCN usefulness audit must use no-leakage feature set and holdout tests",
            ],
        },
    )
    _write_doc(summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_export(args.output_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.strict and summary["num_new_all_remaining_bus_fault_candidates"] != 37:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
