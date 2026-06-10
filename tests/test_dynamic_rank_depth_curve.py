from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_dynamic_rank_depth_curve import analyze_dynamic_rank_depth_curve


def test_rank_depth_curve_outputs_requested_k_values(tmp_path: Path) -> None:
    for group in ["learned_mlp_top100", "pio_gcn_top100", "lodf_top100"]:
        case_dir = tmp_path / "cases" / group
        result_dir = tmp_path / "results" / group
        case_dir.mkdir(parents=True)
        result_dir.mkdir(parents=True)
        paths = [{"case_id": f"c{i}", "path_rank": i, "path": f"L{i:02d}->L{(i % 38) + 1:02d}"} for i in range(1, 101)]
        pd.DataFrame(paths).to_csv(case_dir / "simulink_topk_paths.csv", index=False)
        results = [
            {"case_id": f"c{i}", "dynamic_unstable": i <= 5, "frequency_nadir_hz": 49.5, "max_rotor_angle_separation_deg": 20, "max_rotor_angle_separation_coi_deg": 20, "max_line_loading_ratio": 1.0, "dynamic_load_shed_mw": 0, "passive_relay_trip_count": 0, "security_redispatch_count": 0}
            for i in range(1, 101)
        ]
        pd.DataFrame(results).to_csv(result_dir / "simulink_dynamic_simulation_results.csv", index=False)
    result = analyze_dynamic_rank_depth_curve(tmp_path / "cases", tmp_path / "results", tmp_path / "out", ks=(10, 20, 50, 100))
    table = pd.read_csv(result["csv"])
    assert set(table["k"]) == {10, 20, 50, 100}
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
