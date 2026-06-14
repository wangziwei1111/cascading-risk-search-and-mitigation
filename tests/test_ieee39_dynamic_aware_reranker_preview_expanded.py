from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded"


def test_expanded_preview_artifacts_exist_and_exclude_l12() -> None:
    dataset_path = OUT_DIR / "preview_training_dataset.csv"
    metrics_path = OUT_DIR / "preview_training_metrics.json"
    predictions_path = OUT_DIR / "preview_training_predictions.csv"
    config_path = OUT_DIR / "preview_training_config.json"
    readme_path = OUT_DIR / "preview_training_readme.md"
    for path in [dataset_path, metrics_path, predictions_path, config_path, readme_path]:
        assert path.exists()

    dataset = pd.read_csv(dataset_path)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    predictions = pd.read_csv(predictions_path)

    assert len(dataset) == 35
    assert metrics["num_samples"] == 35
    assert "L12" not in set(dataset["line_id"].astype(str))
    assert "L12" not in set(predictions["line_id"].astype(str))
    assert set(dataset["measurement_extraction_status"].astype(str)) == {"voltage_speed_angle"}
    assert dataset["training_ready_candidate"].astype(str).str.lower().isin({"1", "true"}).all()
    assert metrics["preview_only"] is True
    assert metrics["allowed_for_dynamic_aware_training"] is True
    assert metrics["ready_for_preview_training"] is True
    assert metrics["random_seed"] == 42
    assert metrics["cv_strategy"] == "leave_one_out"
    assert metrics["feature_columns"]
    assert metrics["target_columns"] == ["dynamic_stress_score", "unstable_flag"]


def test_expanded_preview_readme_is_conservative() -> None:
    text = (OUT_DIR / "preview_training_readme.md").read_text(encoding="utf-8").lower()
    for required in [
        "preview-only sanity check",
        "not a final dynamic performance conclusion",
        "l12 excluded",
        "simulation_timeout / suspected islanding",
        "phasor_rms, not emt",
        "generator_speed_proxy` is not direct frequency",
        "pilot breaker-like validation, not engineering-grade protection",
        "metrics may be optimistic",
        "raw trajectories",
        "full timeseries",
    ]:
        assert required in text
    for forbidden in [
        "emt validation completed",
        "engineering-grade protection completed",
        "is a final dynamic performance conclusion",
        "production ready",
        "must commit `.slx`",
        "must commit `.mat`",
    ]:
        assert forbidden not in text
