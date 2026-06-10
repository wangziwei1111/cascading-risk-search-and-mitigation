from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from bootstrap_dynamic_method_comparison import bootstrap_dynamic_method_comparison


def test_dynamic_method_bootstrap_ci_outputs_expected_columns(tmp_path: Path) -> None:
    results_root = tmp_path / "results"
    for group in ["learned_mlp_top50", "learned_mlp_top100", "pio_gcn_top50", "pio_gcn_top100", "lodf_top50", "lodf_top100"]:
        group_dir = results_root / group
        group_dir.mkdir(parents=True)
        pd.DataFrame(
            [
                {"case_id": "c1", "dynamic_unstable": True, "frequency_nadir_hz": 49.2, "max_rotor_angle_separation_deg": 170, "max_rotor_angle_separation_coi_deg": 170, "max_line_loading_ratio": 0.9, "dynamic_load_shed_mw": 0, "passive_relay_trip_count": 0},
                {"case_id": "c2", "dynamic_unstable": False, "frequency_nadir_hz": 49.8, "max_rotor_angle_separation_deg": 120, "max_rotor_angle_separation_coi_deg": 120, "max_line_loading_ratio": 0.8, "dynamic_load_shed_mw": 0, "passive_relay_trip_count": 0},
            ]
        ).to_csv(group_dir / "simulink_dynamic_simulation_results.csv", index=False)
    summary = tmp_path / "summary.csv"
    pd.DataFrame([{"method": "learned_mlp", "top_k": 50}]).to_csv(summary, index=False)
    result = bootstrap_dynamic_method_comparison(results_root, tmp_path / "cases", summary, tmp_path / "out", bootstrap_n=20, seed=1)
    table = pd.read_csv(result["csv"])
    required = {"method", "top_k", "metric", "estimate", "ci_low", "ci_high", "bootstrap_n", "random_seed"}
    assert required.issubset(table.columns)
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
