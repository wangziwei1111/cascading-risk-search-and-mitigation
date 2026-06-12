from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv"
OUT_DIR = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation"
OUT_PATH = OUT_DIR / "clean_breaker_lab_per_line_checklist.txt"


def _line_path(line_id: str) -> str:
    if not MAP_PATH.exists():
        return "Grid/B10 to B13" if line_id == "L03" else "not available"
    table = pd.read_csv(MAP_PATH)
    match = table[table.get("line_id", pd.Series(dtype=str)).astype(str) == line_id]
    if match.empty:
        return "Grid/B10 to B13" if line_id == "L03" else "not in current line map"
    path = str(match.iloc[0].get("line_block_path", "not available"))
    return path.replace("IEEE39BusSystem_dynamic_experiment_wrapper/", "")


def build_checklist() -> str:
    l03_path = _line_path("L03")
    return f"""IEEE39 per-line clean breaker lab checklist

Current status:
- Clean lab L02 has already passed structure validation and isolated compact simulation.
- Clean lab L02 is already a training-ready handwired line-trip label.
- Do not keep adding L03/L04 breakers into the same clean lab that already contains L02.

Why per-line clean labs are required:
- The current target is single-line dynamic labels, not multi-line cascading trip sequences.
- If L02_TripCommand and L03_TripCommand both act at 0.5 s, the simulation becomes an L02 + L03 simultaneous trip.
- A simultaneous multi-line trip must not be used as a single-line L03 label.
- Use one independent clean lab .slx per line.

Recommended local model names:
- IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L02.slx
- IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx
- IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L04.slx

Next model to open:
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx

Next manual target:
- line_id: L03
- line block path: {l03_path}
- breaker name: L03_HandwiredTimedBreaker
- trip command name: L03_TripCommand
- Step time: 0.5 s
- Initial value: 0
- Final value: 1

Manual wiring rules:
1. Only wire L03 in the L03 per-line clean lab.
2. Do not copy L03 from the old handwired model.
3. Do not continue wiring from a clean lab that already contains L02.
4. Drag a fresh same-type breaker from Library Browser.
5. The breaker must be in series on one side of the line.
6. The original B10 to B10 to B13 connection must be opened.
7. Do not leave a bypass path around the breaker.
8. L03_TripCommand must control only L03_HandwiredTimedBreaker.
9. Save the .slx locally after manual wiring.
10. Do not commit any .slx, .slxc, slprj, .mat, raw trajectories, or full timeseries.

After manual wiring, ask Codex to run:
matlab:
cd matlab/simulink_ieee39
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_line("../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx", "L03")

powershell:
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trip_isolated.py --line-id L03 --model-path results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx --timeout-seconds 240 --simulation-stop-time 0.5

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
