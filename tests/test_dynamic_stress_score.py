from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from compute_dynamic_stress_score import compute_dynamic_stress_score


def test_dynamic_stress_score_orders_low_frequency_angle_and_shed(tmp_path: Path) -> None:
    dynamic = tmp_path / "dynamic.csv"
    out = tmp_path / "stress.csv"
    pd.DataFrame(
        [
            {"case_id": "mild", "frequency_nadir_hz": 49.8, "max_rotor_angle_separation_deg": 40, "max_line_loading_ratio": 0.9, "dynamic_load_shed_mw": 0, "passive_relay_trip_count": 0},
            {"case_id": "severe", "frequency_nadir_hz": 48.0, "max_rotor_angle_separation_deg": 400, "max_line_loading_ratio": 1.2, "dynamic_load_shed_mw": 20, "passive_relay_trip_count": 1},
        ]
    ).to_csv(dynamic, index=False)
    result = compute_dynamic_stress_score(dynamic, out)
    assert result.iloc[0]["case_id"] == "severe"
    assert result.iloc[0]["dynamic_stress_score"] > result.iloc[1]["dynamic_stress_score"]
    assert "low_frequency" in result.iloc[0]["stress_reason"]
