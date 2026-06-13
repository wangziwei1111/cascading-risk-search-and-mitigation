from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
QUALITY_PATH = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json"
READINESS_PATH = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json"
VALIDATION_PATH = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/"
    "ieee39_clean_breaker_lab_batch_validation_summary.csv"
)
TRIP_PATH = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/"
    "ieee39_clean_breaker_lab_batch_line_trip_summary.csv"
)
MERGE_PATH = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/"
    "ieee39_clean_breaker_lab_l11_to_l34_merge_summary.json"
)
OUT_DIR = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation"
OUT_PATH = OUT_DIR / "clean_breaker_lab_batch_checklist.txt"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _boolish(value: object) -> bool:
    return str(value).lower() in {"1", "true", "yes"}


def _line_list(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


def _validation_section(validation: pd.DataFrame) -> str:
    if validation.empty:
        return "- validation summary missing"
    rows = []
    for _, row in validation.iterrows():
        rows.append(
            f"- {row['line_id']}: validation_passed={row['validation_passed']}, "
            f"breaker_found={row['breaker_block_found']}, trip_command_found={row['trip_command_found']}, "
            f"line block path={str(row['line_block_path']).replace('IEEE39BusSystem_dynamic_experiment_wrapper/', '')}"
        )
    return "\n".join(rows)


def _simulation_section(trips: pd.DataFrame) -> str:
    if trips.empty:
        return "- compact simulation summary missing"
    rows = []
    for _, row in trips.iterrows():
        rows.append(
            f"- {row['tripped_line']}: simulation_success={row['simulation_success']}, "
            f"measurement_extraction_status={row['measurement_extraction_status']}, "
            f"training_ready_candidate={row['training_ready_candidate']}, "
            f"breaker_opened={row['breaker_opened']}, source_model={row['source_model']}, "
            f"breaker name={row['tripped_line']}_HandwiredTimedBreaker, "
            f"trip command name={row['tripped_line']}_TripCommand"
        )
    return "\n".join(rows)


def build_checklist() -> str:
    quality = _read_json(QUALITY_PATH)
    readiness = _read_json(READINESS_PATH)
    merge = _read_json(MERGE_PATH)
    validation = _read_csv(VALIDATION_PATH)
    trips = _read_csv(TRIP_PATH)
    validation_passed = validation.loc[
        validation.get("validation_passed", pd.Series(False, index=validation.index)).map(_boolish),
        "line_id",
    ].astype(str).tolist() if not validation.empty else []
    validation_failed = [line for line in validation.get("line_id", pd.Series(dtype=str)).astype(str).tolist() if line not in validation_passed]
    success = merge.get("merged_line_ids", [])
    timeout = merge.get("timeout_line_ids", [])
    failed = merge.get("failed_line_ids", [])
    skipped = merge.get("skipped_line_ids", [])

    return f"""IEEE39 batch per-line clean breaker lab checklist

Already successful before this round:
- L01-L10 are training-ready handwired line-trip labels.

Round L11-L34 structure validation:
- validation_passed lines: {_line_list(validation_passed)}
- validation_failed lines: {_line_list(validation_failed)}

Round L11-L34 compact simulation:
- simulation_success and merged lines: {_line_list(success)}
- timeout lines: {_line_list(timeout)}
- failed lines: {_line_list(failed)}
- skipped lines: {_line_list(skipped)}

Validation details:
{_validation_section(validation)}

Simulation details:
{_simulation_section(trips)}

Latest formal fault summary:
- results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10_l11_to_l34.csv

Current label gate:
- num_training_ready_labels = {quality.get("num_training_ready_labels", "unknown")}
- num_training_ready_handwired_line_trip_labels = {quality.get("num_training_ready_handwired_line_trip_labels", "unknown")}
- num_unique_handwired_line_ids = {quality.get("num_unique_handwired_line_ids", "unknown")}
- allowed_for_dynamic_aware_training = {str(quality.get("allowed_for_dynamic_aware_training", "unknown")).lower()}
- ready_for_preview_training = {str(readiness.get("ready_for_preview_training", "unknown")).lower()}

Next manual priority:
- Recheck L12 first. Its structure validation passed, but compact simulation timed out.
- Inspect L12_HandwiredTimedBreaker series wiring, bypass paths, short circuits, L12_TripCommand target, Step direction, and abnormal Simscape islands.

This round did not retrain the dynamic-aware reranker.
The previous preview dynamic-aware reranker training remains a workflow sanity check only.

Boundaries:
- The model remains phasor_RMS, not EMT.
- generator_speed_proxy is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- Current labels are single-line dynamic labels, not simultaneous or sequential multi-line trips.
- Do not commit .slx, .slxc, slprj, .mat, raw trajectories, or full timeseries.
- This checklist does not auto-insert breakers and does not modify Simscape physical wiring.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = build_checklist()
    OUT_PATH.write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved checklist to: {OUT_PATH}")


if __name__ == "__main__":
    main()
