from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from summarize_dynamic_negative_controls_v2 import summarize_dynamic_negative_controls_v2


def test_negative_controls_v2_detects_all_groups_unstable_degeneracy(tmp_path: Path) -> None:
    comparison = tmp_path / "comparison.csv"
    pd.DataFrame(
        [
            {"group": "learned_top20", "num_cases": 20, "dynamic_precision_at_20": 1.0, "mean_dynamic_stress_score": 2.0, "cases_with_security_redispatch_or_load_shed": 20, "cases_with_passive_relay_trip": 0, "mean_frequency_nadir_hz": 48.0, "mean_rotor_angle_separation_deg": 500.0},
            {"group": "random_top20", "num_cases": 20, "dynamic_precision_at_20": 1.0, "mean_dynamic_stress_score": 1.5, "cases_with_security_redispatch_or_load_shed": 20, "cases_with_passive_relay_trip": 0, "mean_frequency_nadir_hz": 48.1, "mean_rotor_angle_separation_deg": 450.0},
        ]
    ).to_csv(comparison, index=False)
    sensitivity = tmp_path / "sensitivity.csv"
    pd.DataFrame(
        [
            {"group": "learned_top20", "frequency_threshold_hz": 48.0, "rotor_angle_threshold_deg": 720.0, "unstable_fraction": 0.2},
            {"group": "random_top20", "frequency_threshold_hz": 48.0, "rotor_angle_threshold_deg": 720.0, "unstable_fraction": 0.1},
        ]
    ).to_csv(sensitivity, index=False)
    result = summarize_dynamic_negative_controls_v2(comparison, sensitivity, tmp_path / "out")
    table = pd.read_csv(result["csv"])
    assert result["global_degeneracy_warning"] is True
    assert "global_degeneracy_warning" in table.columns
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
