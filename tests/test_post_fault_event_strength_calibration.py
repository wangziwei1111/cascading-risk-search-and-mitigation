from __future__ import annotations

from pathlib import Path
import sys
import json

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from calibrate_post_fault_event_strength import calibrate_post_fault_event_strength


def test_event_strength_calibration_recommends_nondegenerate_threshold(tmp_path: Path) -> None:
    results_root = tmp_path / "results"
    for group in ["learned_mlp_top100", "pio_gcn_top100", "lodf_top100"]:
        group_dir = results_root / group
        group_dir.mkdir(parents=True)
        pd.DataFrame(
            [
                {"case_id": "c1", "frequency_nadir_hz": 49.2, "max_rotor_angle_separation_coi_deg": 100, "passive_relay_trip_count": 0, "security_redispatch_count": 0},
                {"case_id": "c2", "frequency_nadir_hz": 49.8, "max_rotor_angle_separation_coi_deg": 100, "passive_relay_trip_count": 0, "security_redispatch_count": 0},
            ]
        ).to_csv(group_dir / "simulink_dynamic_simulation_results.csv", index=False)
    options = tmp_path / "options.json"
    options.write_text(json.dumps({"frequency_unstable_threshold_hz": 49.0, "rotor_angle_unstable_threshold_deg": 180.0, "line_loading_scale": 0.002}), encoding="utf-8")
    result = calibrate_post_fault_event_strength(tmp_path / "cases", tmp_path / "base.json", tmp_path / "out", results_root, options, max_cases_per_group=2)
    grid = pd.read_csv(result["grid_csv"])
    assert grid["nondegenerate_dynamic_layer"].astype(bool).any()
    recommended = json.loads(Path(result["recommended_options"]).read_text(encoding="utf-8"))
    assert "frequency_unstable_threshold_hz" in recommended
