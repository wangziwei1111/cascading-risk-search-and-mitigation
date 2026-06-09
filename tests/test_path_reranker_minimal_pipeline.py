from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from build_path_reranker_dataset import PathRerankerDatasetConfig, build_path_reranker_dataset
from export_path_reranker_per_path_ranking import PathRerankerPerPathExportConfig, export_path_reranker_per_path_ranking
from train_path_reranker import FORBIDDEN_LABEL_COLUMNS, TrainPathRerankerConfig, train_path_reranker
from evaluate_path_reranker_strict_heldout import StrictHeldoutConfig, evaluate_strict_heldout


def test_minimal_path_reranker_pipeline_runs_end_to_end(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    model_dir = tmp_path / "models"
    eval_dir = tmp_path / "eval"
    export_dir = tmp_path / "export"
    build_path_reranker_dataset(
        PathRerankerDatasetConfig(
            output_dir=str(dataset_dir),
            train_seeds=(20260722,),
            val_seeds=(20260723,),
            test_seeds=(20260724,),
            max_paths_per_seed=30,
            smoke=True,
        )
    )
    train_path_reranker(TrainPathRerankerConfig(dataset_dir=str(dataset_dir), output_dir=str(model_dir), epochs=10))
    evaluate_strict_heldout(StrictHeldoutConfig(dataset_dir=str(dataset_dir), model_dir=str(model_dir), output_dir=str(eval_dir), top_k=(20,)))
    result = export_path_reranker_per_path_ranking(
        PathRerankerPerPathExportConfig(dataset_dir=str(dataset_dir), model_dir=str(model_dir), output_dir=str(export_dir), top_k=(20,))
    )
    ranking = pd.read_csv(result["output_csv"])
    assert {"case_id", "path_rank", "path", "reranker_score", "opa_is_critical"}.issubset(ranking.columns)
    feature_columns = (model_dir / "path_reranker_feature_columns.json").read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_LABEL_COLUMNS:
        assert forbidden not in feature_columns


def test_export_retrain_if_missing_smoke_builds_artifacts(tmp_path: Path) -> None:
    result = export_path_reranker_per_path_ranking(
        PathRerankerPerPathExportConfig(
            dataset_dir=str(tmp_path / "dataset"),
            model_dir=str(tmp_path / "models"),
            output_dir=str(tmp_path / "export"),
            top_k=(20,),
            retrain_if_missing=True,
            smoke=True,
            max_paths_per_seed=30,
        )
    )
    assert result["rebuilt_dataset"] is True
    assert result["retrained_model"] is True
    assert Path(result["output_csv"]).exists()
