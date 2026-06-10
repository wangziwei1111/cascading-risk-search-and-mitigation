from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from prepare_dynamic_negative_control_inputs import prepare_dynamic_negative_control_inputs
from run_dynamic_negative_control_pipeline import _write_summary


def test_negative_control_v3_summary_has_no_dynamic_recall(tmp_path: Path) -> None:
    rows = [
        {"group": "learned_top20", "num_cases": 20, "dynamic_precision_at_20": 1.0, "dynamic_unstable_count": 20, "mean_frequency_nadir_hz": 48.0, "min_frequency_nadir_hz": 47.0, "mean_rotor_angle_separation_deg": 200.0, "max_rotor_angle_separation_deg": 300.0, "mean_dynamic_stress_score": 5.0, "cases_with_security_redispatch_or_load_shed": 10, "cases_with_passive_relay_trip": 2, "total_dynamic_load_shed_mw": 0.0},
        {"group": "random_top20", "num_cases": 20, "dynamic_precision_at_20": 0.5, "dynamic_unstable_count": 10, "mean_frequency_nadir_hz": 49.0, "min_frequency_nadir_hz": 48.5, "mean_rotor_angle_separation_deg": 100.0, "max_rotor_angle_separation_deg": 200.0, "mean_dynamic_stress_score": 1.0, "cases_with_security_redispatch_or_load_shed": 2, "cases_with_passive_relay_trip": 0, "total_dynamic_load_shed_mw": 0.0},
    ]
    result = _write_summary(rows, tmp_path / "summary", matlab_executed=False, is_post_fault=True)
    table = pd.read_csv(result["csv"])
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
    assert "unstable_fraction_post_fault_calibrated" in table.columns


def test_combined_low_stress_selection_does_not_use_label_columns(tmp_path: Path) -> None:
    input_csv = tmp_path / "ranking.csv"
    pd.DataFrame(
        [
            {"path": "L01->L02", "reranker_score": 0.9, "pio_score": 0.9, "lodf_score": 0.9, "opa_is_critical": 0},
            {"path": "L03->L04", "reranker_score": 0.1, "pio_score": 0.2, "lodf_score": 0.1, "opa_is_critical": 1},
        ]
    ).to_csv(input_csv, index=False)
    result = prepare_dynamic_negative_control_inputs(input_csv, tmp_path / "out", top_k=1, low_risk_mode="combined_low_stress")
    config = pd.read_json(tmp_path / "out" / "low_risk_selection_config.json", typ="series")
    assert config["label_columns_used"] == []
    low = pd.read_csv(result["outputs"]["low_score_top20"])
    assert low["path"].iloc[0] == "L03->L04"
