from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
FULL_MAP_PATH = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv"
EXTENDED_MAP_PATH = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extended.csv"
LEGACY_MAP_PATH = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv"
QUALITY_PATH = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json"
READINESS_PATH = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json"
BATCH_VALIDATION_PATH = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/"
    "ieee39_clean_breaker_lab_batch_validation_summary.csv"
)
BATCH_TRIP_PATH = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/"
    "ieee39_clean_breaker_lab_batch_line_trip_summary.csv"
)
REMAINING_PREPARE_PATH = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/"
    "ieee39_clean_breaker_lab_remaining_prepare_summary.csv"
)
OUT_DIR = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation"
OUT_PATH = OUT_DIR / "clean_breaker_lab_batch_checklist.txt"
VALIDATED_LINES = ["L09", "L10"]
REMAINING_LINES = [f"L{i:02d}" for i in range(11, 35)]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _line_map() -> pd.DataFrame:
    for path in [FULL_MAP_PATH, EXTENDED_MAP_PATH, LEGACY_MAP_PATH]:
        if path.exists():
            return pd.read_csv(path)
    return pd.DataFrame(columns=["line_id", "line_block_path"])


def _line_path(table: pd.DataFrame, line_id: str) -> str:
    match = table[table.get("line_id", pd.Series(dtype=str)).astype(str) == line_id]
    if match.empty:
        return "not_in_current_line_map"
    return str(match.iloc[0].get("line_block_path", "not_in_current_line_map")).replace(
        "IEEE39BusSystem_dynamic_experiment_wrapper/", ""
    )


def _target_block(line_id: str, line_path: str) -> str:
    model = (
        "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/"
        f"IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx"
    )
    if line_path == "not_in_current_line_map":
        return f"""- line_id: {line_id}
  line block path: not_in_current_line_map
  status: do not wire until mapped
  note: do not invent a block path"""
    return f"""- line_id: {line_id}
  line block path: {line_path}
  per-line clean lab .slx path: {model}
  breaker name: {line_id}_HandwiredTimedBreaker
  trip command name: {line_id}_TripCommand
  Step time: 0.5 s
  Initial value: 0
  Final value: 1"""


def _validated_summary() -> str:
    rows: list[str] = []
    if not BATCH_VALIDATION_PATH.exists() or not BATCH_TRIP_PATH.exists():
        return "- L09/L10 batch validation or compact simulation summary is missing."
    validation = pd.read_csv(BATCH_VALIDATION_PATH)
    trips = pd.read_csv(BATCH_TRIP_PATH)
    for line_id in VALIDATED_LINES:
        vrow = validation[validation["line_id"].astype(str) == line_id]
        trow = trips[trips["tripped_line"].astype(str) == line_id]
        if vrow.empty or trow.empty:
            rows.append(f"- {line_id}: missing validation or simulation row")
            continue
        v = vrow.iloc[0]
        t = trow.iloc[0]
        rows.append(
            f"- {line_id}: validation_passed={v.get('validation_passed')}, "
            f"simulation_success={t.get('simulation_success')}, "
            f"training_ready_candidate={t.get('training_ready_candidate')}, "
            f"measurement_extraction_status={t.get('measurement_extraction_status')}, "
            f"line block path={str(v.get('line_block_path')).replace('IEEE39BusSystem_dynamic_experiment_wrapper/', '')}"
        )
    return "\n".join(rows)


def build_checklist() -> str:
    table = _line_map()
    quality = _read_json(QUALITY_PATH)
    readiness = _read_json(READINESS_PATH)
    remaining_blocks = [_target_block(line_id, _line_path(table, line_id)) for line_id in REMAINING_LINES]
    remaining_status = "available" if REMAINING_PREPARE_PATH.exists() else "missing"
    return f"""IEEE39 batch per-line clean breaker lab checklist

Validated L09/L10 results:
{_validated_summary()}

Validated line targets:
- line_id: L09
  line block path: {_line_path(table, "L09")}
  breaker name: L09_HandwiredTimedBreaker
  trip command name: L09_TripCommand
- line_id: L10
  line block path: {_line_path(table, "L10")}
  breaker name: L10_HandwiredTimedBreaker
  trip command name: L10_TripCommand

Already successful earlier clean lab labels:
- clean lab L02
- per-line clean lab L03
- per-line clean lab L04
- per-line clean lab L05
- per-line clean lab L06
- per-line clean lab L07
- per-line clean lab L08

Latest formal fault summary:
- results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10.csv

Current expected label gate:
- num_training_ready_labels = {quality.get("num_training_ready_labels", "unknown")}
- num_training_ready_handwired_line_trip_labels = {quality.get("num_training_ready_handwired_line_trip_labels", "unknown")}
- num_unique_handwired_line_ids = {quality.get("num_unique_handwired_line_ids", "unknown")}
- allowed_for_dynamic_aware_training = {str(quality.get("allowed_for_dynamic_aware_training", "unknown")).lower()}
- ready_for_preview_training = {str(readiness.get("ready_for_preview_training", "unknown")).lower()}

Preview dynamic-aware reranker training already ran earlier as a sanity check.
Do not retrain the dynamic-aware reranker in this round.

Remaining prepared-but-unwired clean lab targets:
- prepare summary status: {remaining_status}
- target line ids: L11-L34

Per-line targets:
{chr(10).join(remaining_blocks)}

Manual wiring rules:
1. One line uses one .slx.
2. Each .slx must contain only the corresponding line_id breaker.
3. Do not wire more than one target breaker inside the same per-line .slx.
4. Do not copy from the old handwired model.
5. Do not copy from clean labs that already contain L02-L10.
6. During a single-line label run, only the target breaker may act.
7. Sequential or simultaneous multi-line trip experiments can be studied later, but must not be mixed into single-line labels.
8. Keep all .slx files local; do not commit .slx, .slxc, slprj, .mat, raw trajectories, or full timeseries.
9. This checklist does not auto-insert breakers and does not modify Simscape physical wiring.

After manual wiring, ask Codex to run batch validation for the newly wired line ids.
Example MATLAB flow:
cd matlab/simulink_ieee39
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_lines_batch(["L11","L12"])

If validation passes, ask Codex to run batch isolated compact simulation for the same line ids.

Boundaries:
- The model remains phasor_RMS, not EMT.
- generator_speed_proxy is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- Current preview training is a workflow sanity check only, not a final dynamic performance conclusion.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = build_checklist()
    OUT_PATH.write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved checklist to: {OUT_PATH}")


if __name__ == "__main__":
    main()
