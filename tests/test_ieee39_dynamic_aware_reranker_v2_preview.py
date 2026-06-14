from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview"


def _load_run(name: str) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    run_dir = OUT / name
    dataset = pd.read_csv(run_dir / "preview_training_dataset.csv")
    metrics = json.loads((run_dir / "preview_training_metrics.json").read_text(encoding="utf-8"))
    predictions = pd.read_csv(run_dir / "preview_training_predictions.csv")
    return dataset, metrics, predictions


def test_v2_preview_scripts_and_run_artifacts_exist() -> None:
    assert (ROOT / "scripts/gcn_search/train_ieee39_dynamic_aware_reranker_v2_preview.py").exists()
    assert (ROOT / "scripts/gcn_search/compare_ieee39_dynamic_aware_v2_preview_runs.py").exists()

    for run_name in ["include_all_candidates", "exclude_provenance_required"]:
        run_dir = OUT / run_name
        for filename in [
            "preview_training_dataset.csv",
            "preview_training_config.json",
            "preview_training_metrics.json",
            "preview_training_predictions.csv",
            "preview_model_coefficients.csv",
            "preview_dynamic_aware_reranker_model.json",
            "preview_training_readme.md",
        ]:
            path = run_dir / filename
            assert path.exists(), f"missing {path}"
            assert path.stat().st_size > 0, f"empty {path}"


def test_include_all_candidates_has_40_rows_and_nf06() -> None:
    dataset, metrics, predictions = _load_run("include_all_candidates")
    assert len(dataset) == 40
    assert metrics["num_samples"] == 40
    assert metrics["contains_nf06"] is True
    assert "NF06" in set(dataset["scenario_id"].astype(str))
    assert "NF06" in set(predictions["scenario_id"].astype(str))
    assert metrics["num_existing_formal_dynamic_rows"] == 35
    assert metrics["num_handwired_line_trip_rows"] == 33
    assert metrics["num_non_line_trip_candidate_rows"] == 5
    assert metrics["provenance_check_required_rows"] == 1


def test_exclude_provenance_candidates_has_39_rows_and_no_nf06() -> None:
    dataset, metrics, predictions = _load_run("exclude_provenance_required")
    assert len(dataset) == 39
    assert metrics["num_samples"] == 39
    assert metrics["contains_nf06"] is False
    assert "NF06" not in set(dataset["scenario_id"].astype(str))
    assert "NF06" not in set(predictions["scenario_id"].astype(str))
    assert metrics["num_existing_formal_dynamic_rows"] == 35
    assert metrics["num_handwired_line_trip_rows"] == 33
    assert metrics["num_non_line_trip_candidate_rows"] == 4
    assert metrics["provenance_check_required_rows"] == 0


def test_v2_preview_boundaries_and_holdout_metrics() -> None:
    for run_name in ["include_all_candidates", "exclude_provenance_required"]:
        dataset, metrics, _ = _load_run(run_name)
        assert "L12" not in set(dataset["line_id"].astype(str))
        assert metrics["preview_only"] is True
        assert metrics["final_performance_conclusion"] is False
        assert "label_family_holdout" in metrics["metrics_by_split"]
        holdout = metrics["label_family_holdout_metrics"]
        assert holdout["regression"]["rmse"] > 0
        assert holdout["num_folds"] == 1
        assert "classification_skipped_reason" in holdout
        assert metrics["regression_metrics"]["rmse"] > 0
        assert metrics["classification_metrics"]["accuracy"] >= 0.0

