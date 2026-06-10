from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_dynamic_method_comparison import analyze_dynamic_method_comparison


def test_non_smoke_method_comparison_prefix_and_warning(tmp_path: Path) -> None:
    for group in ["learned_mlp_top100", "pio_gcn_top100", "lodf_top100"]:
        case_dir = tmp_path / "cases" / group
        result_dir = tmp_path / "results" / group
        case_dir.mkdir(parents=True)
        result_dir.mkdir(parents=True)
        pd.DataFrame(
            [
                {"case_id": "c1", "path_rank": 1, "path": "L01->L02", "opa_is_critical": False},
                {"case_id": "c2", "path_rank": 2, "path": "L02->L03", "opa_is_critical": True},
            ]
        ).to_csv(case_dir / "simulink_topk_paths.csv", index=False)
        pd.DataFrame(
            [
                {"case_id": "c1", "dynamic_unstable": False, "frequency_nadir_hz": 49.8, "max_rotor_angle_separation_deg": 30, "max_rotor_angle_separation_coi_deg": 30, "max_line_loading_ratio": 0.9, "dynamic_load_shed_mw": 0, "passive_relay_trip_count": 0, "security_redispatch_count": 0, "unstable_reason": "stable"},
                {"case_id": "c2", "dynamic_unstable": False, "frequency_nadir_hz": 49.7, "max_rotor_angle_separation_deg": 40, "max_rotor_angle_separation_coi_deg": 40, "max_line_loading_ratio": 0.95, "dynamic_load_shed_mw": 0, "passive_relay_trip_count": 0, "security_redispatch_count": 0, "unstable_reason": "stable"},
            ]
        ).to_csv(result_dir / "simulink_dynamic_simulation_results.csv", index=False)

    stats = tmp_path / "stats.json"
    stats.write_text('{"dataset_source":"simulator_derived_medium","dataset_scale":"medium","num_samples":8000,"num_critical":120,"positive_ratio":0.015}', encoding="utf-8")
    model = tmp_path / "model.json"
    model.write_text('{"test_auc":0.7,"test_average_precision":0.2}', encoding="utf-8")
    result = analyze_dynamic_method_comparison(
        tmp_path / "cases",
        tmp_path / "results",
        tmp_path / "out",
        summary_prefix="dynamic_method_comparison_non_smoke",
        dataset_stats_json=stats,
        model_summary_json=model,
    )
    table = pd.read_csv(result["summary_csv"])
    assert Path(result["summary_csv"]).name == "dynamic_method_comparison_non_smoke_summary.csv"
    assert result["calibration_warning"] is True
    assert "dataset_source" in table.columns
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
