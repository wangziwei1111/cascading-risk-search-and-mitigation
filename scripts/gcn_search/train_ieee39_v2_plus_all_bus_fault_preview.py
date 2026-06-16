"""Run IEEE39 v2-plus-all-bus-fault preview/no-leakage comparison.

This round is preview-only. It does not run Simulink, does not export labels,
does not train GCN, does not retrain the formal reranker, and does not run a
GCN usefulness audit.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from train_ieee39_dynamic_aware_reranker_v2_plus_b39_preview import (
    build_features,
    evaluate_folds,
    prepare_dataset,
    _json_safe,
    _write_json,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview"
EXISTING_BUS_FAULT_BUSES = {"B26", "B39"}
DYNAMIC_STRESS_COLUMNS = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
]


def _as_abs(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(_fs_path(path))


def _finite_or_none(value: Any) -> float | None:
    if value is None:
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def _selected_prediction(predictions: pd.DataFrame, scenario_id: str) -> dict[str, Any]:
    row = predictions[predictions["scenario_id"].astype(str).eq(scenario_id)]
    if row.empty:
        raise ValueError(f"Missing prediction for {scenario_id}.")
    record = row.iloc[0]
    return {
        "scenario_id": scenario_id,
        "target_bus": str(record.get("target_bus", "")),
        "true_dynamic_stress_score": _finite_or_none(record["y_true_dynamic_stress_score"]),
        "predicted_dynamic_stress_score": _finite_or_none(record["y_pred_dynamic_stress_score"]),
        "absolute_error": _finite_or_none(record["absolute_error"]),
        "true_unstable_flag": int(record["y_true_unstable_flag"]),
        "unstable_probability": _finite_or_none(record["y_pred_unstable_probability"]),
    }


def _format_float(value: Any) -> str:
    value = _finite_or_none(value)
    return "n/a" if value is None else f"{value:.6f}"


def _run_mode(
    name: str,
    dataset: pd.DataFrame,
    feature_set: str,
    folds: list[tuple[str, np.ndarray, np.ndarray]],
    out_dir: Path,
    random_seed: int,
    extra: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    features, feature_columns = build_features(dataset, feature_set)
    metrics, predictions = evaluate_folds(dataset, features, folds, random_seed)
    payload: dict[str, Any] = {
        "preview_only": True,
        "final_performance_conclusion": False,
        "simulink_run": False,
        "actual_smoke_run": False,
        "labels_exported": False,
        "gcn_trained": False,
        "formal_reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "should_train_now": False,
        "mode": name,
        "feature_set": feature_set,
        "model_regression": "Ridge Regression",
        "model_classification": "Logistic Regression",
        "random_seed": int(random_seed),
        "num_samples": int(len(dataset)),
        "num_predictions": int(metrics["num_predictions"]),
        "num_bus_fault_candidates": int(dataset["bus_fault_label"].sum()),
        "feature_columns": feature_columns,
        "compact_dynamic_measurement_features_are_post_fault": True,
        "target_feature_leakage_risk_if_used_as_inputs": feature_set != "no_dynamic_measurement_features",
        "regression_metrics": metrics["regression"],
        "classification_metrics": metrics["classification"],
        "classification_skipped_reason": metrics["classification_skipped_reason"],
        "folds": metrics["folds"],
        "notes": [
            "preview-only",
            "not GCN training",
            "not GCN usefulness audit",
            "not formal reranker retraining",
            "phasor_RMS is not EMT",
            "generator_speed_proxy is not direct frequency",
            "temporary bus-fault injection is not engineering-grade protection",
        ],
    }
    if extra:
        payload.update(extra)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "preview_training_metrics.json", payload)
    return payload, predictions


def _leave_one_out_folds(dataset: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    idx = np.arange(len(dataset))
    return [(f"loo_{i}", np.setdiff1d(idx, [i]), np.array([i])) for i in range(len(dataset))]


def _label_family_holdout_folds(dataset: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    family = dataset["label_family"].astype(str)
    train_idx = np.where(family.eq("existing_formal_dynamic"))[0]
    test_idx = np.where(family.ne("existing_formal_dynamic"))[0]
    if len(train_idx) == 0 or len(test_idx) == 0:
        raise ValueError("label_family_holdout requires both formal and non-formal rows.")
    return [("holdout_non_formal_families", train_idx, test_idx)]


def _bus_fault_holdout_folds(dataset: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    bus_fault = dataset["bus_fault_label"].astype(float).to_numpy() > 0.5
    train_idx = np.where(~bus_fault)[0]
    test_idx = np.where(bus_fault)[0]
    if len(test_idx) == 0:
        raise ValueError("bus_fault_holdout requires bus-fault rows.")
    return [("holdout_all_bus_fault_candidates", train_idx, test_idx)]


def _scenario_holdout_folds(dataset: pd.DataFrame, scenario_ids: list[str]) -> list[tuple[str, np.ndarray, np.ndarray]]:
    scenario = dataset["scenario_id"].astype(str)
    test_mask = scenario.isin(scenario_ids).to_numpy()
    train_idx = np.where(~test_mask)[0]
    test_idx = np.where(test_mask)[0]
    if len(test_idx) == 0:
        raise ValueError("scenario holdout requires at least one test row.")
    return [("holdout_selected_scenarios", train_idx, test_idx)]


def _bus_fault_only(dataset: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    bus_fault_ids = set(dataset.loc[dataset["bus_fault_label"].astype(float) > 0.5, "scenario_id"].astype(str))
    return predictions[predictions["scenario_id"].astype(str).isin(bus_fault_ids)].copy()


def _existing_vs_new_summary(predictions: pd.DataFrame) -> dict[str, Any]:
    work = predictions.copy()
    work["target_bus"] = work["target_bus"].fillna("").astype(str)
    work["candidate_origin"] = np.where(work["target_bus"].isin(EXISTING_BUS_FAULT_BUSES), "existing", "new")
    existing = work[work["candidate_origin"].eq("existing")]
    new = work[work["candidate_origin"].eq("new")]
    return {
        "preview_only": True,
        "final_performance_conclusion": False,
        "simulink_run": False,
        "actual_smoke_run": False,
        "labels_exported": False,
        "gcn_trained": False,
        "formal_reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "should_train_now": False,
        "mode": "existing_vs_new_bus_fault_check",
        "num_existing_bus_fault_candidates": int(len(existing)),
        "num_new_bus_fault_candidates": int(len(new)),
        "existing_candidate_buses": sorted(existing["target_bus"].unique().tolist()),
        "new_candidate_buses": sorted(new["target_bus"].unique().tolist()),
        "existing_mean_abs_error": _finite_or_none(existing["absolute_error"].mean()) if not existing.empty else None,
        "new_mean_abs_error": _finite_or_none(new["absolute_error"].mean()) if not new.empty else None,
        "existing_rmse": _finite_or_none(np.sqrt(np.mean(existing["absolute_error"].to_numpy(dtype=float) ** 2))) if not existing.empty else None,
        "new_rmse": _finite_or_none(np.sqrt(np.mean(new["absolute_error"].to_numpy(dtype=float) ** 2))) if not new.empty else None,
        "existing_unstable_probability_mean": _finite_or_none(existing["y_pred_unstable_probability"].mean()) if not existing.empty else None,
        "new_unstable_probability_mean": _finite_or_none(new["y_pred_unstable_probability"].mean()) if not new.empty else None,
        "notes": [
            "distribution description only",
            "not a formal conclusion",
            "derived from no_dynamic_measurement_leave_one_bus_fault_out predictions",
        ],
    }


def _leave_one_bus_fault_summary(predictions: pd.DataFrame, mode: str) -> dict[str, Any]:
    work = predictions.copy()
    work["target_bus"] = work["target_bus"].fillna("").astype(str)
    work["absolute_error"] = pd.to_numeric(work["absolute_error"], errors="coerce")
    work["y_true_dynamic_stress_score"] = pd.to_numeric(work["y_true_dynamic_stress_score"], errors="coerce")
    work["y_pred_dynamic_stress_score"] = pd.to_numeric(work["y_pred_dynamic_stress_score"], errors="coerce")
    work["y_pred_unstable_probability"] = pd.to_numeric(work["y_pred_unstable_probability"], errors="coerce")
    errors = work["absolute_error"].to_numpy(dtype=float)
    worst = work.sort_values("absolute_error", ascending=False).head(10)
    b1 = work[work["target_bus"].eq("B1")]
    if b1.empty:
        raise ValueError("B1 leave-one-bus-fault-out metrics are missing.")
    b1_row = b1.iloc[0]
    return {
        "mode": mode,
        "num_bus_fault_candidates": int(len(work)),
        "lobo_rmse": _finite_or_none(np.sqrt(np.mean(errors**2))),
        "lobo_mae": _finite_or_none(np.mean(errors)),
        "lobo_max_abs_error": _finite_or_none(np.max(errors)),
        "lobo_median_abs_error": _finite_or_none(np.median(errors)),
        "worst_10_buses_by_abs_error": [
            {
                "target_bus": str(row["target_bus"]),
                "scenario_id": str(row["scenario_id"]),
                "absolute_error": _finite_or_none(row["absolute_error"]),
                "true_dynamic_stress_score": _finite_or_none(row["y_true_dynamic_stress_score"]),
                "predicted_dynamic_stress_score": _finite_or_none(row["y_pred_dynamic_stress_score"]),
                "unstable_probability": _finite_or_none(row["y_pred_unstable_probability"]),
            }
            for _, row in worst.iterrows()
        ],
        "b1_true_dynamic_stress_score": _finite_or_none(b1_row["y_true_dynamic_stress_score"]),
        "b1_predicted_dynamic_stress_score": _finite_or_none(b1_row["y_pred_dynamic_stress_score"]),
        "b1_absolute_error": _finite_or_none(b1_row["absolute_error"]),
        "b1_true_unstable_flag": int(b1_row["y_true_unstable_flag"]),
        "b1_unstable_probability": _finite_or_none(b1_row["y_pred_unstable_probability"]),
        "per_bus_predictions": [
            {
                "target_bus": str(row["target_bus"]),
                "scenario_id": str(row["scenario_id"]),
                "true_dynamic_stress_score": _finite_or_none(row["y_true_dynamic_stress_score"]),
                "predicted_dynamic_stress_score": _finite_or_none(row["y_pred_dynamic_stress_score"]),
                "absolute_error": _finite_or_none(row["absolute_error"]),
                "true_unstable_flag": int(row["y_true_unstable_flag"]),
                "unstable_probability": _finite_or_none(row["y_pred_unstable_probability"]),
            }
            for _, row in work.sort_values("target_bus").iterrows()
        ],
    }


def _comparison_csv_rows(comparison: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {
            "mode": "include_all_79_candidates",
            "rmse": comparison["include_all_79_rmse"],
            "mae": comparison["include_all_79_mae"],
            "note": "leaky upper-bound",
        },
        {
            "mode": "no_dynamic_measurement_features",
            "rmse": comparison["no_dynamic_measurement_rmse"],
            "mae": comparison["no_dynamic_measurement_mae"],
            "note": "leakage-reduced sanity check",
        },
        {
            "mode": "label_family_holdout",
            "rmse": comparison["label_family_holdout_rmse"],
            "mae": comparison["label_family_holdout_mae"],
            "note": "train formal / test non-formal families",
        },
        {
            "mode": "bus_fault_holdout",
            "rmse": comparison["bus_fault_holdout_rmse"],
            "mae": comparison["bus_fault_holdout_mae"],
            "note": "train non-bus-fault / test all bus-fault candidates",
        },
        {
            "mode": "leave_one_bus_fault_out",
            "rmse": comparison["leave_one_bus_fault_out_rmse"],
            "mae": comparison["leave_one_bus_fault_out_mae"],
            "note": "all-feature leave-one-bus-fault-out",
        },
        {
            "mode": "no_dynamic_measurement_leave_one_bus_fault_out",
            "rmse": comparison["no_dynamic_measurement_leave_one_bus_fault_out_rmse"],
            "mae": comparison["no_dynamic_measurement_leave_one_bus_fault_out_mae"],
            "note": "no-leakage leave-one-bus-fault-out",
        },
    ]
    return pd.DataFrame(rows)


def _recommended_next_step(comparison: dict[str, Any]) -> str:
    include_rmse = float(comparison["include_all_79_rmse"])
    no_dyn_rmse = float(comparison["no_dynamic_measurement_rmse"])
    lobo_rmse = float(comparison["leave_one_bus_fault_out_rmse"])
    no_dyn_lobo_rmse = float(comparison["no_dynamic_measurement_leave_one_bus_fault_out_rmse"])
    if no_dyn_rmse > include_rmse * 1.25 or no_dyn_lobo_rmse > lobo_rmse * 1.25:
        return "leakage risk confirmed; prepare GCN usefulness audit only with no-leakage features and strict holdouts, not training yet"
    if no_dyn_rmse > 0.35 or no_dyn_lobo_rmse > 0.35:
        return "inspect features and labels before GCN usefulness audit"
    return "prepare GCN usefulness audit only with no-leakage features and strict holdouts, not training yet"


def _render_md(comparison: dict[str, Any]) -> str:
    return f"""# IEEE39 v2-plus-all-bus-fault Preview/No-Leakage Comparison

This round is preview/no-leakage comparison only. It did not run Simulink, did
not run actual smoke, did not export labels, did not train GCN, did not
retrain the formal reranker, and did not run a GCN usefulness audit.

## Plain-Language Meaning

This step uses very small preview models to ask one narrow question: if we keep
post-fault compact dynamic measurements as inputs, do we get leakage-like
performance inflation, and if we remove them, how hard is bus-fault
generalization really?

## Boundary Flags

- preview_only: `{str(comparison['preview_only']).lower()}`
- final_performance_conclusion: `{str(comparison['final_performance_conclusion']).lower()}`
- simulink_run: `{str(comparison['simulink_run']).lower()}`
- actual_smoke_run: `{str(comparison['actual_smoke_run']).lower()}`
- labels_exported: `{str(comparison['labels_exported']).lower()}`
- gcn_trained: `{str(comparison['gcn_trained']).lower()}`
- formal_reranker_retrained: `{str(comparison['formal_reranker_retrained']).lower()}`
- gcn_usefulness_audit_run: `{str(comparison['gcn_usefulness_audit_run']).lower()}`
- should_train_now: `{str(comparison['should_train_now']).lower()}`
- total_candidate_rows: `{comparison['total_candidate_rows']}`
- num_total_bus_fault_candidates: `{comparison['num_total_bus_fault_candidates']}`
- all_ieee39_buses_have_bus_fault_candidate: `{str(comparison['all_ieee39_buses_have_bus_fault_candidate']).lower()}`
- unstable_flag_false_buses: `{comparison['unstable_flag_false_buses']}`
- old_formal_gate: `{comparison['old_formal_gate']}`

## Metrics Summary

| mode | RMSE | MAE | note |
| --- | ---: | ---: | --- |
| include_all_79_candidates | {_format_float(comparison['include_all_79_rmse'])} | {_format_float(comparison['include_all_79_mae'])} | leaky upper-bound |
| no_dynamic_measurement_features | {_format_float(comparison['no_dynamic_measurement_rmse'])} | {_format_float(comparison['no_dynamic_measurement_mae'])} | leakage-reduced sanity check |
| label_family_holdout | {_format_float(comparison['label_family_holdout_rmse'])} | {_format_float(comparison['label_family_holdout_mae'])} | train formal, test non-formal families |
| bus_fault_holdout | {_format_float(comparison['bus_fault_holdout_rmse'])} | {_format_float(comparison['bus_fault_holdout_mae'])} | train non-bus-fault, test 39 bus-fault candidates |
| leave_one_bus_fault_out | {_format_float(comparison['leave_one_bus_fault_out_rmse'])} | {_format_float(comparison['leave_one_bus_fault_out_mae'])} | one bus-fault candidate held out each time |
| no_dynamic_measurement_leave_one_bus_fault_out | {_format_float(comparison['no_dynamic_measurement_leave_one_bus_fault_out_rmse'])} | {_format_float(comparison['no_dynamic_measurement_leave_one_bus_fault_out_mae'])} | stricter no-leakage bus-fault generalization |

## B1 Detail

B1 keeps `unstable_flag=false` as a low-risk / stable marker. That is not an
error.

| target | true stress | predicted stress | absolute error | true unstable | unstable probability |
| --- | ---: | ---: | ---: | ---: | ---: |
| B1 | {_format_float(comparison['b1_true_dynamic_stress_score'])} | {_format_float(comparison['b1_predicted_dynamic_stress_score'])} | {_format_float(comparison['b1_absolute_error'])} | {comparison['b1_true_unstable_flag']} | {_format_float(comparison['b1_unstable_probability'])} |

## Conservative Interpretation

- `include_all_79_candidates` is a leaky upper-bound because post-fault compact
  dynamic measurements also help define the proxy target.
- `no_dynamic_measurement_features` and
  `no_dynamic_measurement_leave_one_bus_fault_out` are more important than the
  include-all score.
- The 79-row dataset still contains candidate labels, not formal labels.
- Bus-fault rows remain temporary smoke candidates, not engineering-grade
  protection labels.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- This round cannot directly prove GCN useful or not useful because no GCN
  usefulness audit ran.

## Recommended Next Step

`{comparison['recommended_next_step']}`
"""


def run_preview(args: argparse.Namespace) -> dict[str, Any]:
    candidate_path = _as_abs(args.combined_candidates)
    review_path = _as_abs(args.composition_review)
    leakage_path = _as_abs(args.leakage_review)
    out_dir = _as_abs(args.output_dir)

    raw = _read_csv(candidate_path)
    review = _read_json(review_path)
    leakage = _read_json(leakage_path)

    required_review_flags = [
        "composition_review_passed",
        "row_count_check_passed",
        "all_ieee39_buses_have_bus_fault_candidate",
        "target_feature_leakage_risk_if_used_as_inputs",
    ]
    missing = [key for key in required_review_flags if review.get(key) is not True]
    if missing:
        raise ValueError(f"All-bus-fault composition review is not ready: {missing}")
    if leakage.get("should_train_now") is not False:
        raise ValueError("Leakage review must keep should_train_now=false.")

    prepare_raw = raw.drop(columns=[col for col in raw.columns if col.lower() == "l12_excluded"], errors="ignore")
    all_dataset = prepare_dataset(prepare_raw, exclude_provenance_required=False)
    if len(all_dataset) != 79:
        raise ValueError(f"Expected 79 prepared rows, got {len(all_dataset)}.")
    if int(all_dataset["bus_fault_label"].sum()) != 39:
        raise ValueError("Expected 39 bus-fault candidates in prepared dataset.")

    include_metrics, _ = _run_mode(
        "include_all_79_candidates",
        all_dataset,
        "with_dynamic_measurement_features",
        _leave_one_out_folds(all_dataset),
        out_dir / "include_all_79_candidates",
        args.random_seed,
        {"include_all_is_leaky_upper_bound": True},
    )
    no_dynamic_metrics, _ = _run_mode(
        "no_dynamic_measurement_features",
        all_dataset,
        "no_dynamic_measurement_features",
        _leave_one_out_folds(all_dataset),
        out_dir / "no_dynamic_measurement_features",
        args.random_seed,
        {"include_all_is_leaky_upper_bound": False, "leakage_reduced": True},
    )
    label_family_metrics, _ = _run_mode(
        "label_family_holdout",
        all_dataset,
        "with_dynamic_measurement_features",
        _label_family_holdout_folds(all_dataset),
        out_dir / "label_family_holdout",
        args.random_seed,
        {
            "train_rows": "existing_formal_dynamic",
            "test_rows": "non_line_trip including all bus-fault candidates",
        },
    )
    bus_fault_metrics, bus_fault_predictions = _run_mode(
        "bus_fault_holdout",
        all_dataset,
        "with_dynamic_measurement_features",
        _bus_fault_holdout_folds(all_dataset),
        out_dir / "bus_fault_holdout",
        args.random_seed,
        {"train_rows": "non-bus-fault", "test_rows": "39 bus-fault candidates"},
    )
    bus_fault_predictions = _bus_fault_only(all_dataset, bus_fault_predictions)
    bus_fault_metrics["per_bus_predictions"] = [
        _selected_prediction(bus_fault_predictions, scenario_id)
        for scenario_id in bus_fault_predictions["scenario_id"].astype(str).tolist()
    ]
    bus_fault_b1 = _selected_prediction(bus_fault_predictions, "BF_B1_TEMP_SMOKE")
    _write_json(out_dir / "bus_fault_holdout" / "preview_training_metrics.json", bus_fault_metrics)

    lobo_bus_ids = all_dataset.loc[all_dataset["bus_fault_label"].astype(float) > 0.5, "scenario_id"].astype(str).tolist()
    lobo_dataset = all_dataset[all_dataset["scenario_id"].astype(str).isin(lobo_bus_ids)].copy()

    leave_one_metrics, leave_one_predictions = _run_mode(
        "leave_one_bus_fault_out",
        all_dataset,
        "with_dynamic_measurement_features",
        _scenario_holdout_folds(all_dataset, lobo_bus_ids),
        out_dir / "leave_one_bus_fault_out",
        args.random_seed,
        {"holdout_type": "all_bus_fault_candidates", "test_count": 39},
    )
    # Replace the coarse scenario holdout metrics with true bus-wise leave-one-out.
    leave_one_metrics, leave_one_predictions = _run_mode(
        "leave_one_bus_fault_out",
        lobo_dataset,
        "with_dynamic_measurement_features",
        _leave_one_out_folds(lobo_dataset),
        out_dir / "leave_one_bus_fault_out",
        args.random_seed,
        {"holdout_type": "leave-one-bus-fault-out", "test_count": 39},
    )
    leave_one_summary = _leave_one_bus_fault_summary(leave_one_predictions, "leave_one_bus_fault_out")
    leave_one_metrics.update(leave_one_summary)
    _write_json(out_dir / "leave_one_bus_fault_out" / "preview_training_metrics.json", leave_one_metrics)

    no_dynamic_leave_one_metrics, no_dynamic_leave_one_predictions = _run_mode(
        "no_dynamic_measurement_leave_one_bus_fault_out",
        lobo_dataset,
        "no_dynamic_measurement_features",
        _leave_one_out_folds(lobo_dataset),
        out_dir / "no_dynamic_measurement_leave_one_bus_fault_out",
        args.random_seed,
        {"holdout_type": "leave-one-bus-fault-out", "test_count": 39, "leakage_reduced": True},
    )
    no_dynamic_leave_one_summary = _leave_one_bus_fault_summary(
        no_dynamic_leave_one_predictions, "no_dynamic_measurement_leave_one_bus_fault_out"
    )
    no_dynamic_leave_one_metrics.update(no_dynamic_leave_one_summary)
    _write_json(
        out_dir / "no_dynamic_measurement_leave_one_bus_fault_out" / "preview_training_metrics.json",
        no_dynamic_leave_one_metrics,
    )

    existing_vs_new = _existing_vs_new_summary(no_dynamic_leave_one_predictions)
    _write_json(out_dir / "existing_vs_new_bus_fault_check" / "preview_training_metrics.json", existing_vs_new)

    comparison = {
        "preview_only": True,
        "final_performance_conclusion": False,
        "candidate_dataset": "v2_plus_all_bus_fault_candidates",
        "total_candidate_rows": 79,
        "num_total_bus_fault_candidates": 39,
        "all_ieee39_buses_have_bus_fault_candidate": True,
        "old_formal_gate": review.get("old_formal_gate", "35 / 33 / 33"),
        "l12_excluded": bool(review.get("l12_excluded", True)),
        "nf06_provenance_warning_preserved": bool(review.get("nf06_provenance_warning_preserved", True)),
        "unstable_flag_false_buses": review.get("unstable_flag_false_buses", ["B1"]),
        "simulink_run": False,
        "actual_smoke_run": False,
        "labels_exported": False,
        "gcn_trained": False,
        "formal_reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "should_train_now": False,
        "compact_dynamic_measurement_features_are_post_fault": True,
        "target_feature_leakage_risk_if_used_as_inputs": True,
        "include_all_is_leaky_upper_bound": True,
        "no_dynamic_measurement_feature_set_required_for_future_audit": True,
        "include_all_79_rmse": include_metrics["regression_metrics"]["rmse"],
        "include_all_79_mae": include_metrics["regression_metrics"]["mae"],
        "no_dynamic_measurement_rmse": no_dynamic_metrics["regression_metrics"]["rmse"],
        "no_dynamic_measurement_mae": no_dynamic_metrics["regression_metrics"]["mae"],
        "label_family_holdout_rmse": label_family_metrics["regression_metrics"]["rmse"],
        "label_family_holdout_mae": label_family_metrics["regression_metrics"]["mae"],
        "bus_fault_holdout_rmse": bus_fault_metrics["regression_metrics"]["rmse"],
        "bus_fault_holdout_mae": bus_fault_metrics["regression_metrics"]["mae"],
        "leave_one_bus_fault_out_rmse": leave_one_metrics["lobo_rmse"],
        "leave_one_bus_fault_out_mae": leave_one_metrics["lobo_mae"],
        "no_dynamic_measurement_leave_one_bus_fault_out_rmse": no_dynamic_leave_one_metrics["lobo_rmse"],
        "no_dynamic_measurement_leave_one_bus_fault_out_mae": no_dynamic_leave_one_metrics["lobo_mae"],
        "b1_true_dynamic_stress_score": no_dynamic_leave_one_metrics["b1_true_dynamic_stress_score"],
        "b1_predicted_dynamic_stress_score": no_dynamic_leave_one_metrics["b1_predicted_dynamic_stress_score"],
        "b1_absolute_error": no_dynamic_leave_one_metrics["b1_absolute_error"],
        "b1_true_unstable_flag": no_dynamic_leave_one_metrics["b1_true_unstable_flag"],
        "b1_unstable_probability": (
            no_dynamic_leave_one_metrics["b1_unstable_probability"]
            if no_dynamic_leave_one_metrics["b1_unstable_probability"] is not None
            else bus_fault_b1["unstable_probability"]
        ),
        "b1_unstable_probability_source": (
            "no_dynamic_measurement_leave_one_bus_fault_out"
            if no_dynamic_leave_one_metrics["b1_unstable_probability"] is not None
            else "bus_fault_holdout_fallback"
        ),
        "worst_10_lobo_buses_by_abs_error": no_dynamic_leave_one_metrics["worst_10_buses_by_abs_error"],
        "mode_metrics": {
            "include_all_79_candidates": include_metrics,
            "no_dynamic_measurement_features": no_dynamic_metrics,
            "label_family_holdout": label_family_metrics,
            "bus_fault_holdout": bus_fault_metrics,
            "leave_one_bus_fault_out": leave_one_metrics,
            "no_dynamic_measurement_leave_one_bus_fault_out": no_dynamic_leave_one_metrics,
            "existing_vs_new_bus_fault_check": existing_vs_new,
        },
        "leakage_risk_confirmed": True,
        "recommended_next_step": "",
    }
    comparison["recommended_next_step"] = _recommended_next_step(comparison)

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "v2_plus_all_bus_fault_preview_comparison.json", comparison)
    (out_dir / "v2_plus_all_bus_fault_preview_comparison.md").write_text(_render_md(comparison), encoding="utf-8")
    _comparison_csv_rows(comparison).to_csv(out_dir / "v2_plus_all_bus_fault_preview_comparison.csv", index=False)
    print(json.dumps(_json_safe({"comparison": str(out_dir / "v2_plus_all_bus_fault_preview_comparison.json")}), indent=2))
    return comparison


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--combined-candidates",
        type=Path,
        default=Path(
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
            "batch_bus_fault_expansion_all_remaining/candidate_label_export/"
            "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv"
        ),
    )
    parser.add_argument(
        "--composition-review",
        type=Path,
        default=Path(
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
            "batch_bus_fault_expansion_all_remaining/no_training_composition_review/"
            "v2_plus_all_bus_fault_composition_review.json"
        ),
    )
    parser.add_argument(
        "--leakage-review",
        type=Path,
        default=Path(
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
            "batch_bus_fault_expansion_all_remaining/no_training_composition_review/"
            "leakage_risk_and_training_boundary_check.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview"),
    )
    parser.add_argument("--random-seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    run_preview(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
