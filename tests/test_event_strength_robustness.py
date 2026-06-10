from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_event_strength_robustness import analyze_event_strength_robustness


def test_event_strength_robustness_detects_no_learned_best(tmp_path: Path) -> None:
    grid = tmp_path / "grid.csv"
    pd.DataFrame([{"dynamic_unstable_fraction": 0.3}, {"dynamic_unstable_fraction": 0.5}]).to_csv(grid, index=False)
    summary = tmp_path / "summary.csv"
    pd.DataFrame(
        [
            {"method": "learned_mlp", "top_k": 100, "dynamic_precision_at_k": 0.27},
            {"method": "pio_gcn", "top_k": 100, "dynamic_precision_at_k": 0.36},
            {"method": "lodf", "top_k": 100, "dynamic_precision_at_k": 0.30},
        ]
    ).to_csv(summary, index=False)
    rank_depth = tmp_path / "rank.csv"
    pd.DataFrame([{"method": "learned_mlp", "k": 100, "mean_dynamic_stress_score_at_k": 0.1}]).to_csv(rank_depth, index=False)
    result = analyze_event_strength_robustness(grid, summary, rank_depth, tmp_path / "out")
    assert result["learned_advantage_robust"] is False
    assert result["top100_best_method"] == "pio_gcn"
