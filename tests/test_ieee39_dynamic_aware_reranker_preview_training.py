from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts" / "gcn_search"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from train_ieee39_dynamic_aware_reranker_preview import PreviewTrainingConfig, run_preview_training


QUALITY = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json"
READINESS = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json"
FAULT_SUMMARY = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/"
    "ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10.csv"
)


def test_preview_training_refuses_when_gate_is_closed(tmp_path: Path) -> None:
    quality = json.loads(QUALITY.read_text(encoding="utf-8"))
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))
    quality["num_training_ready_labels"] = 9
    readiness["allowed_for_dynamic_aware_training"] = False
    quality_path = tmp_path / "quality.json"
    readiness_path = tmp_path / "readiness.json"
    quality_path.write_text(json.dumps(quality), encoding="utf-8")
    readiness_path.write_text(json.dumps(readiness), encoding="utf-8")

    with pytest.raises(RuntimeError, match="Refusing preview training"):
        run_preview_training(
            PreviewTrainingConfig(
                dynamic_label_summary=str(quality_path),
                training_readiness=str(readiness_path),
                fault_summary_csv=str(FAULT_SUMMARY),
                output_dir=str(tmp_path / "out"),
            )
        )


def test_preview_training_generates_dataset_metrics_and_predictions(tmp_path: Path) -> None:
    result = run_preview_training(
        PreviewTrainingConfig(
            dynamic_label_summary=str(QUALITY),
            training_readiness=str(READINESS),
            fault_summary_csv=str(FAULT_SUMMARY),
            output_dir=str(tmp_path / "preview"),
            random_seed=42,
        )
    )

    dataset = pd.read_csv(result["dataset"])
    metrics = json.loads(Path(result["metrics"]).read_text(encoding="utf-8"))
    predictions = pd.read_csv(result["predictions"])

    assert len(dataset) == 12
    assert metrics["preview_only"] is True
    assert metrics["allowed_for_dynamic_aware_training"] is True
    assert metrics["ready_for_preview_training"] is True
    assert metrics["num_samples"] == 12
    assert metrics["num_training_ready_labels"] == 12
    assert metrics["num_handwired_line_trip_labels"] == 10
    assert metrics["num_unique_handwired_line_ids"] == 10
    assert metrics["cv_strategy"] == "leave_one_out"
    assert "dynamic_stress_score" in metrics["target_columns"]
    assert "unstable_flag" in metrics["target_columns"]
    assert {"mae", "rmse", "spearman", "pearson"}.issubset(metrics["regression_metrics"])
    assert "feature_columns" in metrics and metrics["feature_columns"]

    required_prediction_columns = {
        "line_id",
        "test_case",
        "source_model",
        "y_true_dynamic_stress_score",
        "y_pred_dynamic_stress_score",
        "residual",
        "y_true_unstable_flag",
        "y_pred_unstable_score",
        "fold_id",
        "note",
    }
    assert required_prediction_columns.issubset(predictions.columns)
    assert predictions["y_true_dynamic_stress_score"].notna().all()
    assert predictions["y_pred_dynamic_stress_score"].notna().all()

    if not metrics["classification_metrics"]:
        assert metrics["skipped_metrics_reason"]


def test_preview_training_docs_are_conservative() -> None:
    doc = (ROOT / "docs/ieee39_dynamic_aware_reranker_preview_training.md").read_text(encoding="utf-8").lower()
    for required in [
        "preview dynamic-aware reranker training",
        "num_training_ready_labels = 12",
        "historical preview training artifact still contains 10 samples",
        "allowed_for_dynamic_aware_training = true",
        "ready_for_preview_training = true",
        "phasor_rms, not emt",
        "generator_speed_proxy` is not direct frequency",
        "pilot breaker-like validation, not engineering-grade protection",
        "not a final dynamic performance conclusion",
        "do not commit `.slx`",
        "raw trajectories",
        "full timeseries",
    ]:
        assert required in doc
    for forbidden in [
        "emt validation completed",
        "engineering-grade protection completed",
        "is a final dynamic performance conclusion",
        "production ready",
    ]:
        assert forbidden not in doc
