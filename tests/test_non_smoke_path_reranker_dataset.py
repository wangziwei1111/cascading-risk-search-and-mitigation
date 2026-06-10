from __future__ import annotations

from pathlib import Path
import sys
import json

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from build_path_reranker_dataset import PathRerankerDatasetConfig, build_path_reranker_dataset
from train_path_reranker import FORBIDDEN_LABEL_COLUMNS, train_path_reranker, TrainPathRerankerConfig


def test_non_smoke_dataset_stats_and_feature_columns(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "dataset"
    stats = build_path_reranker_dataset(
        PathRerankerDatasetConfig(
            output_dir=str(dataset_dir),
            train_seeds=(1, 2),
            val_seeds=(3,),
            test_seeds=(4,),
            max_paths_per_seed=80,
            smoke=False,
            dataset_scale="medium",
            dataset_source="simulator_derived_medium",
        )
    )
    assert stats["smoke"] is False
    assert stats["dataset_scale"] == "medium"
    assert stats["dataset_source"] == "simulator_derived_medium"
    assert stats["num_samples"] == 320
    assert stats["num_critical"] > 0
    assert 0.0 < stats["positive_ratio"] < 1.0

    model_dir = tmp_path / "model"
    train_path_reranker(TrainPathRerankerConfig(dataset_dir=str(dataset_dir), output_dir=str(model_dir), epochs=3))
    summary = json.loads((model_dir / "path_reranker_model_summary.json").read_text(encoding="utf-8"))
    feature_columns = set(summary["feature_columns"])
    assert not (feature_columns & FORBIDDEN_LABEL_COLUMNS)
