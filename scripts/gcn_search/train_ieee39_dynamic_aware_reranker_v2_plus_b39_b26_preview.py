"""Run IEEE39 v2-plus-B39+B26 preview/no-leakage comparison.

This is a lightweight preview-only sanity check. It does not run Simulink,
does not export labels, does not train GCN, and does not retrain the formal
reranker.
"""

from __future__ import annotations

import argparse
import json
import math
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
B39_ID = "BF_B39_TEMP_SMOKE"
B26_ID = "BF_B26_TEMP_SMOKE"


def _as_abs(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _scenario_holdout_folds(dataset: pd.DataFrame, scenario_ids: set[str], fold_id: str) -> list[tuple[str, np.ndarray, np.ndarray]]:
    scenario = dataset["scenario_id"].astype(str)
    test_mask = scenario.isin(scenario_ids).to_numpy()
    train_idx = np.where(~test_mask)[0]
    test_idx = np.where(test_mask)[0]
    if len(test_idx) == 0:
        raise ValueError(f"No holdout rows found for {sorted(scenario_ids)}.")
    return [(fold_id, train_idx, test_idx)]


def _label_family_holdout_folds(dataset: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    family = dataset["label_family"].astype(str)
    train_idx = np.where(family.eq("existing_formal_dynamic"))[0]
    test_idx = np.where(family.eq("non_line_trip"))[0]
    if len(train_idx) == 0 or len(test_idx) == 0:
        raise ValueError("label_family_holdout requires both formal and non-line-trip rows.")
    return [("holdout_non_line_trip", train_idx, test_idx)]


def _bus_fault_holdout_folds(dataset: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    bus_fault = dataset["bus_fault_label"].astype(float).to_numpy() > 0.5
    train_idx = np.where(~bus_fault)[0]
    test_idx = np.where(bus_fault)[0]
    if len(test_idx) == 0:
        raise ValueError("bus_fault_holdout requires at least one bus-fault row.")
    return [("holdout_b39_b26_bus_faults", train_idx, test_idx)]


def _leave_one_out_folds(dataset: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    idx = np.arange(len(dataset))
    return [(f"loo_{i}", np.setdiff1d(idx, [i]), np.array([i])) for i in range(len(dataset))]


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
        "true_dynamic_stress_score": _finite_or_none(record["y_true_dynamic_stress_score"]),
        "predicted_dynamic_stress_score": _finite_or_none(record["y_pred_dynamic_stress_score"]),
        "absolute_error": _finite_or_none(record["absolute_error"]),
        "true_unstable_flag": int(record["y_true_unstable_flag"]),
        "unstable_probability": _finite_or_none(record["y_pred_unstable_probability"]),
    }


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
    payload = {
        "preview_only": True,
        "final_performance_conclusion": False,
        "simulink_run": False,
        "labels_exported": False,
        "gcn_trained": False,
        "gcn_usefulness_audit_run": False,
        "formal_reranker_retrained": False,
        "mode": name,
        "feature_set": feature_set,
        "model_regression": "Ridge Regression",
        "model_classification": "Logistic Regression",
        "random_seed": int(random_seed),
        "num_samples": int(len(dataset)),
        "num_predictions": int(metrics["num_predictions"]),
        "num_bus_fault_candidates": int(dataset["bus_fault_label"].sum()),
        "contains_b39": bool(dataset["scenario_id"].astype(str).eq(B39_ID).any()),
        "contains_b26": bool(dataset["scenario_id"].astype(str).eq(B26_ID).any()),
        "target_feature_leakage_risk": feature_set != "no_dynamic_measurement_features",
        "leakage_reduced": feature_set == "no_dynamic_measurement_features",
        "dynamic_stress_score_is_proxy_target": True,
        "feature_columns": feature_columns,
        "regression_metrics": metrics["regression"],
        "classification_metrics": metrics["classification"],
        "classification_skipped_reason": metrics["classification_skipped_reason"],
        "folds": metrics["folds"],
        "notes": [
            "preview-only / sanity check",
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


def _format_float(value: Any) -> str:
    value = _finite_or_none(value)
    return "n/a" if value is None else f"{value:.6f}"


def _recommended_next_step(comparison: dict[str, Any]) -> str:
    include_rmse = comparison["include_all_42_rmse"]
    no_dynamic_rmse = comparison["no_dynamic_measurement_rmse"]
    label_rmse = comparison["label_family_holdout_rmse"]
    bus_rmse = comparison["bus_fault_holdout_rmse"]
    b39_err = comparison["b39_holdout_absolute_error"]
    b26_err = comparison["b26_holdout_absolute_error"]
    if no_dynamic_rmse > include_rmse * 1.25 or label_rmse > include_rmse * 2.0:
        if bus_rmse > 0.1 or max(b39_err, b26_err) > 0.1:
            return "collect more bus-fault candidates before GCN usefulness audit"
        return "keep status inconclusive_small_sample and avoid GCN claims"
    if bus_rmse > 0.1 or max(b39_err, b26_err) > 0.1:
        return "collect more bus-fault candidates before GCN usefulness audit"
    return "prepare GCN usefulness audit in a separate future round"


def _render_md(comparison: dict[str, Any]) -> str:
    return f"""# IEEE39 v2-plus-B39+B26 Preview/No-Leakage Comparison

This round is preview-only. It does not run Simulink, does not export labels,
does not train GCN, does not run a GCN usefulness audit, and does not retrain
the formal reranker.

## Plain-Language Meaning

B39 and B26 are now both temporary bus-fault candidate labels. This comparison
uses only small preview models to check whether the compact dynamic measurement
features create target-feature leakage risk and whether B39/B26 holdout
generalization is still weak.

## Boundary Flags

- preview_only: `{str(comparison['preview_only']).lower()}`
- final_performance_conclusion: `{str(comparison['final_performance_conclusion']).lower()}`
- simulink_run: `{str(comparison['simulink_run']).lower()}`
- labels_exported: `{str(comparison['labels_exported']).lower()}`
- gcn_trained: `{str(comparison['gcn_trained']).lower()}`
- gcn_usefulness_audit_run: `{str(comparison['gcn_usefulness_audit_run']).lower()}`
- formal_reranker_retrained: `{str(comparison['formal_reranker_retrained']).lower()}`
- old formal gate: `{comparison['old_formal_gate']}`
- candidate count: `{comparison['v2_plus_b39_b26_candidate_count']}`
- bus-fault candidates: `{comparison['num_bus_fault_candidates']}`

## Metrics Summary

| mode | RMSE | leakage note |
| --- | ---: | --- |
| include_all_42_candidates | {_format_float(comparison['include_all_42_rmse'])} | leaky upper-bound |
| exclude_provenance_required | {_format_float(comparison['exclude_provenance_required_rmse'])} | NF06/provenance-required row excluded |
| no_dynamic_measurement_features | {_format_float(comparison['no_dynamic_measurement_rmse'])} | leakage-reduced sanity check |
| label_family_holdout | {_format_float(comparison['label_family_holdout_rmse'])} | train formal, test non-line-trip |
| bus_fault_holdout | {_format_float(comparison['bus_fault_holdout_rmse'])} | train non-bus-fault, test B39+B26 |
| B39 holdout | {_format_float(comparison['b39_holdout_absolute_error'])} | one-sample absolute error |
| B26 holdout | {_format_float(comparison['b26_holdout_absolute_error'])} | one-sample absolute error |

## B39/B26 Holdout Detail

| target | true stress | predicted stress | absolute error | unstable probability |
| --- | ---: | ---: | ---: | ---: |
| B39 | {_format_float(comparison['b39_true_dynamic_stress_score'])} | {_format_float(comparison['b39_predicted_dynamic_stress_score'])} | {_format_float(comparison['b39_holdout_absolute_error'])} | {_format_float(comparison['b39_unstable_probability'])} |
| B26 | {_format_float(comparison['b26_true_dynamic_stress_score'])} | {_format_float(comparison['b26_predicted_dynamic_stress_score'])} | {_format_float(comparison['b26_holdout_absolute_error'])} | {_format_float(comparison['b26_unstable_probability'])} |

## Conservative Interpretation

The include-all mode uses post-fault compact dynamic measurements, while
`dynamic_stress_score` is also synthesized from compact dynamic measurements.
Therefore include-all should be read as a leaky upper-bound rather than a
formal performance result. The no_dynamic_measurement_features and holdout
modes are more important for judging leakage and small-sample generalization.

This round cannot directly validate GCN because no GCN usefulness audit was
run. B39 and B26 are candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.

## Recommended Next Step

`{comparison['recommended_next_step']}`
"""


def run_preview(args: argparse.Namespace) -> dict[str, Any]:
    candidate_path = _as_abs(args.combined_candidates)
    review_path = _as_abs(args.composition_review)
    out_dir = _as_abs(args.output_dir)
    raw = pd.read_csv(candidate_path)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    required_review_flags = [
        "all_no_training_composition_checks_passed",
        "b39_b26_schema_consistency_passed",
        "count_consistency_passed",
        "export_boundary_passed",
        "leakage_risk_reviewed",
        "target_feature_leakage_risk_if_used_as_inputs",
    ]
    missing = [key for key in required_review_flags if review.get(key) is not True]
    if missing:
        raise ValueError(f"Composition review is not ready for preview comparison: {missing}")

    if "line_id" in raw.columns and raw["line_id"].fillna("").astype(str).str.upper().eq("L12").any():
        raise ValueError("L12 must remain excluded from v2-plus-B39+B26 preview dataset.")
    prepare_raw = raw.drop(columns=[col for col in raw.columns if col.lower() == "l12_excluded"], errors="ignore")
    all_dataset = prepare_dataset(prepare_raw, exclude_provenance_required=False)
    exclude_dataset = prepare_dataset(prepare_raw, exclude_provenance_required=True)
    if len(all_dataset) != 42:
        raise ValueError(f"Expected 42 candidate rows after preparation, got {len(all_dataset)}.")
    if int(all_dataset["bus_fault_label"].sum()) != 2:
        raise ValueError("Expected exactly two bus-fault candidate rows.")

    include_metrics, _ = _run_mode(
        "include_all_42_candidates",
        all_dataset,
        "with_dynamic_measurement_features",
        _leave_one_out_folds(all_dataset),
        out_dir / "include_all_42_candidates",
        args.random_seed,
        {"leakage_risk": "high", "interpretation": "leaky upper-bound, not formal conclusion"},
    )
    exclude_metrics, _ = _run_mode(
        "exclude_provenance_required",
        exclude_dataset,
        "with_dynamic_measurement_features",
        _leave_one_out_folds(exclude_dataset),
        out_dir / "exclude_provenance_required",
        args.random_seed,
        {"excluded_provenance_required": True},
    )
    no_dynamic_metrics, _ = _run_mode(
        "no_dynamic_measurement_features",
        all_dataset,
        "no_dynamic_measurement_features",
        _leave_one_out_folds(all_dataset),
        out_dir / "no_dynamic_measurement_features",
        args.random_seed,
        {"leakage_risk": "reduced", "interpretation": "more important sanity check than include-all"},
    )
    label_holdout_metrics, label_predictions = _run_mode(
        "label_family_holdout",
        all_dataset,
        "with_dynamic_measurement_features",
        _label_family_holdout_folds(all_dataset),
        out_dir / "label_family_holdout",
        args.random_seed,
        {"train_label_family": "existing_formal_dynamic", "test_label_family": "non_line_trip"},
    )
    bus_holdout_metrics, bus_predictions = _run_mode(
        "bus_fault_holdout",
        all_dataset,
        "with_dynamic_measurement_features",
        _bus_fault_holdout_folds(all_dataset),
        out_dir / "bus_fault_holdout",
        args.random_seed,
        {"train_rows": "non-bus-fault", "test_rows": "B39+B26 bus-fault candidates"},
    )
    b39_holdout_metrics, b39_predictions = _run_mode(
        "b39_holdout",
        all_dataset,
        "with_dynamic_measurement_features",
        _scenario_holdout_folds(all_dataset, {B39_ID}, "holdout_b39"),
        out_dir / "b39_holdout",
        args.random_seed,
        {"test_scenario_id": B39_ID},
    )
    b26_holdout_metrics, b26_predictions = _run_mode(
        "b26_holdout",
        all_dataset,
        "with_dynamic_measurement_features",
        _scenario_holdout_folds(all_dataset, {B26_ID}, "holdout_b26"),
        out_dir / "b26_holdout",
        args.random_seed,
        {"test_scenario_id": B26_ID},
    )

    bus_b39 = _selected_prediction(bus_predictions, B39_ID)
    bus_b26 = _selected_prediction(bus_predictions, B26_ID)
    b39 = _selected_prediction(b39_predictions, B39_ID)
    b26 = _selected_prediction(b26_predictions, B26_ID)
    label_b39 = _selected_prediction(label_predictions, B39_ID)
    label_b26 = _selected_prediction(label_predictions, B26_ID)

    comparison = {
        "preview_only": True,
        "final_performance_conclusion": False,
        "gcn_trained": False,
        "gcn_usefulness_audit_run": False,
        "formal_reranker_retrained": False,
        "simulink_run": False,
        "labels_exported": False,
        "old_formal_gate": review.get("old_formal_gate", "35 / 33 / 33"),
        "v2_plus_b39_b26_candidate_count": int(review.get("v2_plus_b39_b26_candidate_count", len(all_dataset))),
        "previous_v2_plus_b39_count": int(review.get("previous_v2_plus_b39_count", 41)),
        "num_bus_fault_candidates": int(review.get("num_bus_fault_candidates", all_dataset["bus_fault_label"].sum())),
        "b39_status": review.get("b39_status", "candidate_label_not_formal"),
        "b26_status": review.get("b26_status", "candidate_label_not_formal"),
        "l12_excluded": bool(review.get("l12_excluded", True)),
        "nf06_provenance_warning_preserved": bool(review.get("nf06_provenance_warning_preserved", True)),
        "leakage_risk_reviewed": bool(review.get("leakage_risk_reviewed", True)),
        "target_feature_leakage_risk_if_dynamic_measurements_used": True,
        "include_all_42_rmse": include_metrics["regression_metrics"]["rmse"],
        "exclude_provenance_required_rmse": exclude_metrics["regression_metrics"]["rmse"],
        "no_dynamic_measurement_rmse": no_dynamic_metrics["regression_metrics"]["rmse"],
        "label_family_holdout_rmse": label_holdout_metrics["regression_metrics"]["rmse"],
        "bus_fault_holdout_rmse": bus_holdout_metrics["regression_metrics"]["rmse"],
        "b39_holdout_absolute_error": b39["absolute_error"],
        "b26_holdout_absolute_error": b26["absolute_error"],
        "b39_true_dynamic_stress_score": b39["true_dynamic_stress_score"],
        "b39_predicted_dynamic_stress_score": b39["predicted_dynamic_stress_score"],
        "b26_true_dynamic_stress_score": b26["true_dynamic_stress_score"],
        "b26_predicted_dynamic_stress_score": b26["predicted_dynamic_stress_score"],
        "b39_unstable_probability": b39["unstable_probability"],
        "b26_unstable_probability": b26["unstable_probability"],
        "bus_fault_holdout_b39": bus_b39,
        "bus_fault_holdout_b26": bus_b26,
        "label_family_holdout_b39": label_b39,
        "label_family_holdout_b26": label_b26,
        "mode_metrics": {
            "include_all_42_candidates": include_metrics,
            "exclude_provenance_required": exclude_metrics,
            "no_dynamic_measurement_features": no_dynamic_metrics,
            "label_family_holdout": label_holdout_metrics,
            "bus_fault_holdout": bus_holdout_metrics,
            "b39_holdout": b39_holdout_metrics,
            "b26_holdout": b26_holdout_metrics,
        },
        "leakage_risk_conclusion": "include_all_42_candidates is a leaky upper-bound; no_dynamic_measurement_features and holdout modes are the more important checks.",
        "can_directly_validate_gcn": False,
        "gcn_claim_boundary": "No GCN usefulness audit ran, so this round cannot conclude whether GCN is useful.",
    }
    comparison["recommended_next_step"] = _recommended_next_step(comparison)

    _write_json(out_dir / "v2_plus_b39_b26_preview_comparison.json", comparison)
    (out_dir / "v2_plus_b39_b26_preview_comparison.md").write_text(_render_md(comparison), encoding="utf-8")
    print(json.dumps(_json_safe({"comparison": str(out_dir / "v2_plus_b39_b26_preview_comparison.json")}), indent=2))
    return comparison


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--combined-candidates",
        type=Path,
        default=Path(
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
            "b26_candidate_label_export/ieee39_dynamic_label_schema_v2_plus_b39_b26_candidate.csv"
        ),
    )
    parser.add_argument(
        "--composition-review",
        type=Path,
        default=Path(
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
            "b26_candidate_label_export/no_training_composition_review/"
            "ieee39_v2_plus_b39_b26_composition_review.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview"),
    )
    parser.add_argument("--random-seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    run_preview(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
