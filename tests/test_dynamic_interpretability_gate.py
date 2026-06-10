from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from check_dynamic_interpretability_gate import check_dynamic_interpretability_gate


def test_gate_blocks_when_controls_all_unstable(tmp_path: Path) -> None:
    ladder, v3 = _write_inputs(tmp_path, low=1.0, random=1.0)
    result = check_dynamic_interpretability_gate(ladder, v3, tmp_path / "out")
    assert result["allowed_next_step"] == "continue_dynamic_calibration"


def test_gate_allows_when_controls_have_variation(tmp_path: Path) -> None:
    ladder, v3 = _write_inputs(tmp_path, low=0.5, random=0.5)
    result = check_dynamic_interpretability_gate(ladder, v3, tmp_path / "out")
    assert result["allowed_next_step"] == "expand_top50_top100"


def _write_inputs(tmp_path: Path, low: float, random: float) -> tuple[Path, Path]:
    ladder = tmp_path / "ladder.csv"
    pd.DataFrame(
        [
            {"case_group": "no_trip", "unstable_fraction": 0.0, "sanity_level_passed": True},
            {"case_group": "single_mild_trip", "unstable_fraction": 0.0, "sanity_level_passed": True},
            {"case_group": "low_risk_ordered_n2", "unstable_fraction": low, "sanity_level_passed": low < 1.0},
            {"case_group": "random_ordered_n2", "unstable_fraction": random, "sanity_level_passed": random < 1.0},
        ]
    ).to_csv(ladder, index=False)
    v3 = tmp_path / "v3.csv"
    pd.DataFrame(
        [
            {"group": "learned_top20", "unstable_fraction_post_fault_calibrated": 1.0},
            {"group": "low_score_top20", "unstable_fraction_post_fault_calibrated": low},
            {"group": "random_top20", "unstable_fraction_post_fault_calibrated": random},
            {"group": "line_order_top20", "unstable_fraction_post_fault_calibrated": 0.5},
        ]
    ).to_csv(v3, index=False)
    return ladder, v3
