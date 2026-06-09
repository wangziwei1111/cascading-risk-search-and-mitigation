from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from prepare_dynamic_method_comparison_topk import prepare_dynamic_method_comparison_topk


def test_prepare_dynamic_method_comparison_outputs_three_inputs(tmp_path: Path) -> None:
    input_csv = tmp_path / "paths.csv"
    pd.DataFrame(
        [
            {"path": "L10->L05", "reranker_score": 0.9, "pio_score": 0.2, "lodf_score": 0.1},
            {"path": "L27->L02", "reranker_score": 0.1, "pio_score": 0.8, "lodf_score": 0.7},
        ]
    ).to_csv(input_csv, index=False)
    out = tmp_path / "methods"
    config = prepare_dynamic_method_comparison_topk(input_csv, out, top_k=2)
    assert {"learned_mlp", "pio_gcn", "lodf"}.issubset(config["outputs"])
    assert (out / "learned_mlp_topk_input_paths.csv").exists()
    assert (out / "pio_gcn_topk_input_paths.csv").exists()
    assert (out / "lodf_topk_input_paths.csv").exists()


def test_prepare_dynamic_method_comparison_warns_missing_scores(tmp_path: Path) -> None:
    input_csv = tmp_path / "paths.csv"
    pd.DataFrame([{"path": "L10->L05", "reranker_score": 0.9}]).to_csv(input_csv, index=False)
    config = prepare_dynamic_method_comparison_topk(input_csv, tmp_path / "methods", top_k=1)
    assert "learned_mlp" in config["outputs"]
    assert any("Skipped pio_gcn" in item for item in config["warnings"])
    assert any("Skipped lodf" in item for item in config["warnings"])
