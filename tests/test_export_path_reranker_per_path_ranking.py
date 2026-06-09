from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from export_path_reranker_per_path_ranking import (
    FORBIDDEN_LABEL_FEATURE_COLUMNS,
    REQUIRED_OUTPUT_COLUMNS,
    PathRerankerPerPathExportConfig,
    export_path_reranker_per_path_ranking,
)


def test_export_path_reranker_per_path_ranking_from_mock_artifact(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    model = tmp_path / "model"
    out = tmp_path / "out"
    dataset.mkdir()
    model.mkdir()
    pd.DataFrame(
        [
            {"split": "train", "path": "L01->L02", "reranker_score": 0.1},
            {"split": "test", "path": "L10->L05", "reranker_score": 0.9, "pio_score": 0.4, "lodf_score": 0.2, "opa_is_critical": True, "opa_total_load_shed_mw": 100.0},
            {"split": "test", "path": "L27->L02", "reranker_score": 0.7, "pio_score": 0.3, "lodf_score": 0.1, "opa_is_critical": False, "opa_total_load_shed_mw": 0.0},
        ]
    ).to_csv(dataset / "test_per_path_scores.csv", index=False)

    result = export_path_reranker_per_path_ranking(
        PathRerankerPerPathExportConfig(dataset_dir=str(dataset), model_dir=str(model), output_dir=str(out), split="test")
    )
    exported = pd.read_csv(result["output_csv"])
    assert list(exported.columns) == REQUIRED_OUTPUT_COLUMNS
    assert exported["path"].tolist() == ["L10->L05", "L27->L02"]
    assert set(exported["split"]) == {"test"}
    assert (out / "learned_mlp_per_path_ranking_config.json").exists()
    assert (out / "learned_mlp_topk_preview.csv").exists()


def test_export_path_reranker_missing_artifacts_errors(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="path reranker dataset/model artifacts not available"):
        export_path_reranker_per_path_ranking(
            PathRerankerPerPathExportConfig(dataset_dir=str(tmp_path / "missing_dataset"), model_dir=str(tmp_path / "missing_model"))
        )


def test_forbidden_label_columns_are_declared_not_features() -> None:
    assert {"opa_is_critical", "opa_total_load_shed_mw", "truth_rank"}.issubset(FORBIDDEN_LABEL_FEATURE_COLUMNS)
