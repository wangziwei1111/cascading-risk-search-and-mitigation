from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from prepare_dynamic_negative_control_inputs import GROUPS, prepare_dynamic_negative_control_inputs
from run_dynamic_negative_control_pipeline import _write_summary


def test_negative_control_input_preparation_is_reproducible(tmp_path: Path) -> None:
    input_csv = tmp_path / "ranking.csv"
    rows = []
    for idx in range(1, 31):
        rows.append({"path": f"L{idx:02d}->L{(idx % 38) + 1:02d}", "reranker_score": 1.0 / idx, "path_rank": idx})
    pd.DataFrame(rows).to_csv(input_csv, index=False)
    result1 = prepare_dynamic_negative_control_inputs(input_csv, tmp_path / "out1", top_k=5, random_seed=7)
    result2 = prepare_dynamic_negative_control_inputs(input_csv, tmp_path / "out2", top_k=5, random_seed=7)
    assert set(result1["outputs"]) == set(GROUPS)
    random1 = pd.read_csv(result1["outputs"]["random_top20"])["path"].tolist()
    random2 = pd.read_csv(result2["outputs"]["random_top20"])["path"].tolist()
    assert random1 == random2


def test_negative_control_summary_flags_global_degeneracy(tmp_path: Path) -> None:
    rows = [
        {"group": group, "num_cases": 20, "dynamic_precision_at_20": 1.0, "dynamic_unstable_count": 20, "mean_frequency_nadir_hz": 48.0, "min_frequency_nadir_hz": 47.9, "mean_rotor_angle_separation_deg": 300.0, "max_rotor_angle_separation_deg": 400.0, "mean_dynamic_stress_score": 2.0, "cases_with_security_redispatch_or_load_shed": 20, "cases_with_passive_relay_trip": 0, "total_dynamic_load_shed_mw": 10.0, "degeneracy_warning": True}
        for group in GROUPS
    ]
    result = _write_summary(rows, tmp_path / "summary", matlab_executed=True)
    assert result["global_degeneracy_warning"] is True
    table = pd.read_csv(result["csv"])
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
