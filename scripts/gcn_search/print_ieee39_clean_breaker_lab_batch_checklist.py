from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
EXTENDED_MAP_PATH = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extended.csv"
LEGACY_MAP_PATH = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv"
OUT_DIR = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation"
OUT_PATH = OUT_DIR / "clean_breaker_lab_batch_checklist.txt"
TARGET_LINES = ["L06", "L07", "L08", "L09", "L10"]


def _line_map() -> pd.DataFrame:
    if EXTENDED_MAP_PATH.exists():
        return pd.read_csv(EXTENDED_MAP_PATH)
    if LEGACY_MAP_PATH.exists():
        return pd.read_csv(LEGACY_MAP_PATH)
    return pd.DataFrame(columns=["line_id", "line_block_path"])


def _line_path(table: pd.DataFrame, line_id: str) -> str:
    match = table[table.get("line_id", pd.Series(dtype=str)).astype(str) == line_id]
    if match.empty:
        return "not_in_current_line_map"
    return str(match.iloc[0].get("line_block_path", "not_in_current_line_map")).replace("IEEE39BusSystem_dynamic_experiment_wrapper/", "")


def _target_block(line_id: str, line_path: str) -> str:
    model = f"results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx"
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


def build_checklist() -> str:
    table = _line_map()
    blocks = [_target_block(line_id, _line_path(table, line_id)) for line_id in TARGET_LINES]
    return f"""IEEE39 batch per-line clean breaker lab checklist

Already successful training-ready handwired line trips:
- L01
- clean lab L02
- per-line clean lab L03
- per-line clean lab L04
- per-line clean lab L05

Current expected label gate:
- num_training_ready_labels = 7
- num_training_ready_handwired_line_trip_labels = 5
- num_unique_handwired_line_ids = 5
- allowed_for_dynamic_aware_training = false

Next recommended manual targets:
- priority: L06
- priority: L07
- priority: L08
- L06-L10 are listed below only if present in the verified line map; otherwise they are marked not_in_current_line_map.

Per-line targets:
{chr(10).join(blocks)}

Manual wiring rules:
1. One line uses one .slx.
2. Each .slx must contain only the corresponding line_id breaker.
3. Do not wire more than one target breaker inside the same per-line .slx.
4. Do not copy from the old handwired model.
5. Do not copy from clean labs that already contain L02 or L03.
6. During a single-line label run, only the target breaker may act.
7. Sequential or simultaneous multi-line trip experiments can be studied later, but not mixed into single-line labels.
8. Keep all .slx files local; do not commit .slx, .slxc, slprj, .mat, raw trajectories, or full timeseries.

After manual wiring, ask Codex to run batch validation:
matlab:
cd matlab/simulink_ieee39
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_lines_batch(["L06","L07","L08"])

If validation passes, ask Codex to run batch isolated compact simulation:
powershell:
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L06 L07 L08 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{{line_id}}.slx" --timeout-seconds 240 --simulation-stop-time 0.5

Boundaries:
- The model remains phasor_RMS, not EMT.
- generator_speed_proxy is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- If training-ready labels remain below 10, dynamic-aware reranker training remains blocked.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = build_checklist()
    OUT_PATH.write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved checklist to: {OUT_PATH}")


if __name__ == "__main__":
    main()
