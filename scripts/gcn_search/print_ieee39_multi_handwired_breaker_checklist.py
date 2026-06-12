from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv"
QUALITY_PATH = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json"
OUT_DIR = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation"
OUT_PATH = OUT_DIR / "multi_handwired_breaker_checklist.txt"


def _load_line_map() -> pd.DataFrame:
    if not MAP_PATH.exists():
        return pd.DataFrame(columns=["line_id", "line_block_path"])
    return pd.read_csv(MAP_PATH)


def _line_rows() -> list[str]:
    table = _load_line_map()
    lines = [f"L{i:02d}" for i in range(2, 11)]
    rows = []
    for line_id in ["L01", *lines]:
        match = table[table.get("line_id", pd.Series(dtype=str)).astype(str) == line_id]
        line_path = str(match.iloc[0].get("line_block_path", "not in current line map")) if not match.empty else "not in current line map"
        status = "validated reference" if line_id == "L01" else "recommended next handwired candidate"
        rows.append(
            "\n".join(
                [
                    f"- line_id: {line_id}",
                    f"  line block path: {line_path}",
                    f"  recommended breaker name: {line_id}_HandwiredTimedBreaker",
                    f"  recommended trip command name: {line_id}_TripCommand",
                    "  trip time: 0.5 s",
                    f"  status: {status}",
                ]
            )
        )
    return rows


def build_checklist() -> str:
    rows = "\n".join(_line_rows())
    return f"""IEEE39 multi-line handwired timed breaker checklist

Current reference:
- L01 has already passed handwired validation and compact line-trip simulation.
- Use L01_HandwiredTimedBreaker and L01_TripCommand as the naming template.

Recommended next batch:
- L02
- L03
- L04
- L05

Optional later batch if the first expansion works:
- L06
- L07
- L08
- L09
- L10

Per-line wiring targets:
{rows}

Manual wiring rules:
1. Keep editing the local handwired model only:
   results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx
2. The handwired .slx must not be committed. Do not commit any .slx, .slxc, slprj, .mat, raw trajectories, or full timeseries.
3. Add only 2-3 lines per manual editing round.
4. Each trip command should use Step time = 0.5 s, Initial value = 0, Final value = 1.
5. If a breaker appears to operate in the opposite direction, try Initial value = 1 and Final value = 0.
6. Run validation after each small batch.
7. This remains phasor_RMS pilot breaker-like validation, not EMT and not engineering-grade protection.
8. If num_training_ready_labels < 10, dynamic-aware reranker training remains blocked.

MATLAB commands after manual wiring:
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
validate_ieee39_multi_handwired_breakers( ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation", ...
  ["L01","L02","L03","L04"], ...
  "%s_HandwiredTimedBreaker", ...
  "%s_TripCommand" ...
)
run_ieee39_multi_handwired_line_trip_suite( ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests", ...
  ["L01","L02","L03","L04"], ...
  0.5 ...
)
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = build_checklist()
    OUT_PATH.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nSaved checklist to: {OUT_PATH}")


if __name__ == "__main__":
    main()
