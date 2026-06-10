from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from export_dynamic_method_comparison_cases import export_dynamic_method_comparison_cases
from prepare_dynamic_method_comparison_topk import prepare_dynamic_method_comparison_topk


def test_method_comparison_inputs_and_cases_do_not_use_labels(tmp_path: Path) -> None:
    ranking = tmp_path / "ranking.csv"
    rows = []
    for idx in range(1, 121):
        rows.append(
            {
                "path": f"L{idx % 38 + 1:02d}->L{(idx + 1) % 38 + 1:02d}",
                "reranker_score": 200 - idx,
                "pio_score": 100 + idx,
                "lodf_score": idx,
                "opa_is_critical": 1 if idx == 119 else 0,
                "opa_total_load_shed_mw": 999 if idx == 119 else 0,
            }
        )
    pd.DataFrame(rows).to_csv(ranking, index=False)
    config = prepare_dynamic_method_comparison_topk(ranking, tmp_path / "inputs", top_k=100)
    assert config["label_columns_used_for_sorting"] == []
    assert (tmp_path / "inputs" / "learned_mlp_top50_input_paths.csv").exists()
    export_dynamic_method_comparison_cases(tmp_path / "inputs", tmp_path / "cases", top_k=(50, 100), simulation_end_time=10.0)
    assert (tmp_path / "cases" / "learned_mlp_top50" / "matlab_batch_input.csv").exists()
    assert (tmp_path / "cases" / "pio_gcn_top100" / "simulink_topk_paths.csv").exists()
