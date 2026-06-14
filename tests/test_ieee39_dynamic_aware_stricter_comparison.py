from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison"


def test_stricter_comparison_artifacts_and_dataset() -> None:
    required = [
        "stricter_comparison_dataset.csv",
        "stricter_comparison_config.json",
        "stricter_comparison_metrics.json",
        "stricter_comparison_predictions.csv",
        "stricter_comparison_feature_sets.json",
        "stricter_comparison_summary.md",
        "stricter_comparison_leakage_notes.md",
    ]
    for name in required:
        assert (OUT / name).exists()

    dataset = pd.read_csv(OUT / "stricter_comparison_dataset.csv")
    metrics = json.loads((OUT / "stricter_comparison_metrics.json").read_text(encoding="utf-8"))
    predictions = pd.read_csv(OUT / "stricter_comparison_predictions.csv")

    assert len(dataset) == 35
    assert metrics["num_samples"] == 35
    assert "L12" not in set(dataset["line_id"].astype(str))
    assert metrics["excluded_line_ids"] == ["L12"]
    assert metrics["preview_only"] is True
    assert metrics["final_performance_conclusion"] is False
    assert len(predictions) > 35


def test_stricter_feature_sets_and_splits() -> None:
    metrics = json.loads((OUT / "stricter_comparison_metrics.json").read_text(encoding="utf-8"))
    feature_sets = metrics["feature_sets"]
    assert {
        "leaky_dynamic_measurement_features",
        "no_dynamic_measurement_features",
        "topology_only_features",
    }.issubset(feature_sets)
    forbidden_measurements = {
        "min_voltage_pu",
        "max_voltage_pu",
        "min_frequency_hz",
        "max_frequency_hz",
        "max_speed_deviation",
        "max_rotor_angle_separation_deg",
    }
    assert forbidden_measurements.isdisjoint(set(feature_sets["topology_only_features"]))
    assert forbidden_measurements.isdisjoint(set(feature_sets["no_dynamic_measurement_features"]))
    assert forbidden_measurements.issubset(set(feature_sets["leaky_dynamic_measurement_features"]))
    assert "line_id" not in feature_sets["topology_only_features"]

    assert {
        "leave_one_out",
        "grouped_line_range_holdout",
        "endpoint_bus_region_holdout",
        "random_kfold_baseline",
    }.issubset(metrics["split_strategies"])
    for feature_set in feature_sets:
        assert metrics["per_feature_set_per_split_metrics"][feature_set]


def test_stricter_leakage_gap_is_recorded() -> None:
    metrics = json.loads((OUT / "stricter_comparison_metrics.json").read_text(encoding="utf-8"))
    gap = metrics["leakage_gap_summary"]
    assert gap["best_leaky_rmse"] is not None
    assert gap["best_no_leakage_rmse"] is not None
    assert gap["rmse_gap_no_leak_minus_leaky"] is not None
    assert "harder" in gap["interpretation"]
    assert metrics["target_columns"] == ["dynamic_stress_score", "unstable_flag"]
