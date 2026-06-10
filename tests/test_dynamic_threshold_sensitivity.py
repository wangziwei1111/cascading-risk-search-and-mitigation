from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_dynamic_threshold_sensitivity import analyze_dynamic_threshold_sensitivity


def test_threshold_sensitivity_scans_multiple_thresholds_without_recall(tmp_path: Path) -> None:
    root = tmp_path / "results"
    for group in ["learned_top20", "random_top20"]:
        group_dir = root / group
        group_dir.mkdir(parents=True)
        pd.DataFrame(
            [
                {
                    "case_id": f"{group}_1",
                    "frequency_nadir_hz": 48.8,
                    "max_rotor_angle_separation_coi_deg": 400.0,
                    "max_line_loading_ratio": 1.0,
                    "dynamic_load_shed_mw": 0.0,
                    "passive_relay_trip_count": 0,
                }
            ]
        ).to_csv(group_dir / "simulink_dynamic_simulation_results.csv", index=False)
    result = analyze_dynamic_threshold_sensitivity(root, tmp_path / "out")
    table = pd.read_csv(result["csv"])
    assert table["frequency_threshold_hz"].nunique() > 1
    assert table["rotor_angle_threshold_deg"].nunique() > 1
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
    assert result["num_threshold_cases"] == len(table)
