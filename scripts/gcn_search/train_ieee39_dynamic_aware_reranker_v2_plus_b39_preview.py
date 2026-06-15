"""Run IEEE39 v2-plus-B39 dynamic-aware reranker preview training.

This is a lightweight preview/sanity-check trainer. It does not run Simulink,
does not train GCN, and does not write model checkpoints.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DYNAMIC_MEASUREMENT_COLUMNS = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
]
BOOLEAN_FEATURES = [
    "physical_fault_or_breaker_action_executed",
    "breaker_opened",
    "formal_line_trip_label",
    "handwired_line_trip_label",
    "non_line_trip_label",
    "bus_fault_label",
    "temporary_smoke_candidate",
    "candidate_not_formal_label",
    "provenance_check_required",
    "not_independent_physical_sample_until_verified",
]
NUMERIC_BASE_FEATURES = [
    "duration_s",
    "fault_start_s",
    "fault_clear_s",
    "line_id_numeric",
    "target_bus_numeric",
]
CATEGORICAL_FEATURES = [
    "line_id",
    "target_bus",
    "target_bus_or_component",
    "fault_type",
    "label_family",
    "trip_implementation",
    "source_model_type",
    "duplicate_measurement_group",
]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if math.isnan(float(value)):
            return None
        return float(value)
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _line_id_to_number(value: Any) -> float:
    text = str(value)
    if text.startswith("L") and text[1:].isdigit():
        return float(text[1:])
    return 0.0


def _bus_to_number(value: Any) -> float:
    text = str(value)
    if text.startswith("B") and text[1:].isdigit():
        return float(text[1:])
    return 0.0


def compute_dynamic_stress_score(table: pd.DataFrame) -> pd.Series:
    voltage_sag = (1.0 - pd.to_numeric(table["min_voltage_pu"], errors="coerce")).clip(lower=0.0)
    frequency_excursion_hz = pd.concat(
        [
            (pd.to_numeric(table["min_frequency_hz"], errors="coerce") - 50.0).abs(),
            (pd.to_numeric(table["max_frequency_hz"], errors="coerce") - 50.0).abs(),
        ],
        axis=1,
    ).max(axis=1)
    speed = pd.to_numeric(table["max_speed_deviation"], errors="coerce").clip(lower=0.0)
    angle = pd.to_numeric(table["max_rotor_angle_separation_deg"], errors="coerce").clip(lower=0.0)
    return 0.35 * voltage_sag + 0.25 * frequency_excursion_hz + 0.20 * (speed * 100.0) + 0.20 * (angle / 180.0)


def prepare_dataset(raw: pd.DataFrame, exclude_provenance_required: bool = False) -> pd.DataFrame:
    work = raw.copy()
    work = work[work["training_ready_label_v2"].map(_boolish)].copy()
    work = work[work["measurement_extraction_status"].astype(str).eq("voltage_speed_angle")].copy()
    if exclude_provenance_required:
        work = work[~work["provenance_check_required"].map(_boolish)].copy()
    if "l12" in work.to_json().lower():
        raise ValueError("L12 must remain excluded from v2-plus-B39 preview dataset.")
    for col in ["line_id", "target_bus", "target_bus_or_component", "source_model_type"]:
        if col not in work.columns:
            work[col] = ""
        work[col] = work[col].fillna("").astype(str)
    work.loc[work["line_id"].eq(""), "line_id"] = work["target_bus_or_component"]
    work.loc[work["line_id"].eq("B39"), "line_id"] = "NO_LINE"
    work.loc[work["line_id"].eq(""), "line_id"] = "NO_LINE"
    work["target_bus"] = work["target_bus"].fillna("").astype(str)
    work.loc[work["scenario_id"].astype(str).eq("BF_B39_TEMP_SMOKE"), "target_bus"] = "B39"
    work["line_id_numeric"] = work["line_id"].map(_line_id_to_number)
    work["target_bus_numeric"] = work["target_bus"].map(_bus_to_number)
    for col in BOOLEAN_FEATURES:
        if col not in work.columns:
            work[col] = False
        work[col] = work[col].map(_boolish).astype(float)
    for col in NUMERIC_BASE_FEATURES + DYNAMIC_MEASUREMENT_COLUMNS:
        if col not in work.columns:
            work[col] = 0.0
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
    for col in CATEGORICAL_FEATURES:
        if col not in work.columns:
            work[col] = "unknown"
        work[col] = work[col].replace("", "unknown").fillna("unknown").astype(str)
    work["unstable_flag"] = work["unstable_flag"].map(_boolish).astype(int)
    work["dynamic_stress_score"] = compute_dynamic_stress_score(work)
    return work.reset_index(drop=True)


def build_features(dataset: pd.DataFrame, feature_set: str) -> tuple[pd.DataFrame, list[str]]:
    numeric_columns = NUMERIC_BASE_FEATURES + BOOLEAN_FEATURES
    if feature_set != "no_dynamic_measurement_features":
        numeric_columns = numeric_columns + DYNAMIC_MEASUREMENT_COLUMNS
    numeric = dataset[numeric_columns].copy()
    one_hot = pd.get_dummies(dataset[CATEGORICAL_FEATURES], prefix=CATEGORICAL_FEATURES, dtype=float)
    features = pd.concat([numeric, one_hot], axis=1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return features, list(features.columns)


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    x_aug = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(x_aug.shape[1]) * alpha
    penalty[0, 0] = 0.0
    return np.linalg.pinv(x_aug.T @ x_aug + penalty) @ x_aug.T @ y


def predict_linear(coef: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x]) @ coef


def standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std < 1e-8] = 1.0
    return (x - mean) / std, mean, std


def fit_logistic(x: np.ndarray, y: np.ndarray, random_seed: int, epochs: int = 500) -> dict[str, Any]:
    rng = np.random.default_rng(random_seed)
    x_scaled, mean, std = standardize(x)
    weight = rng.normal(0.0, 0.02, size=x_scaled.shape[1])
    bias = 0.0
    pos_weight = float((len(y) - y.sum()) / max(float(y.sum()), 1.0))
    for _ in range(epochs):
        logits = np.clip(x_scaled @ weight + bias, -30, 30)
        prob = 1.0 / (1.0 + np.exp(-logits))
        sample_weight = np.where(y > 0.5, pos_weight, 1.0)
        grad = (prob - y) * sample_weight
        weight -= 0.2 * ((x_scaled.T @ grad) / len(y) + 0.1 * weight)
        bias -= 0.2 * float(grad.mean())
    return {"weight": weight, "bias": bias, "mean": mean, "std": std}


def predict_logistic(model: dict[str, Any], x: np.ndarray) -> np.ndarray:
    x_scaled = (x - np.asarray(model["mean"])) / np.asarray(model["std"])
    logits = np.clip(x_scaled @ np.asarray(model["weight"]) + float(model["bias"]), -30, 30)
    return 1.0 / (1.0 + np.exp(-logits))


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    residual = y_true - y_pred
    return {
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "pearson": safe_corr(y_true, y_pred, "pearson"),
        "spearman": safe_corr(y_true, y_pred, "spearman"),
    }


def classification_metrics(y_true: np.ndarray, score: np.ndarray) -> dict[str, Any]:
    pred = (score >= 0.5).astype(int)
    tp = int(((pred == 1) & (y_true == 1)).sum())
    tn = int(((pred == 0) & (y_true == 0)).sum())
    fp = int(((pred == 1) & (y_true == 0)).sum())
    fn = int(((pred == 0) & (y_true == 1)).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    return {
        "accuracy": float((tp + tn) / max(len(y_true), 1)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": binary_auc(y_true, score),
    }


def binary_auc(y_true: np.ndarray, score: np.ndarray) -> float | None:
    pos = y_true == 1
    neg = y_true == 0
    if pos.sum() == 0 or neg.sum() == 0:
        return None
    order = np.argsort(score)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(score) + 1, dtype=float)
    return float((ranks[pos].sum() - pos.sum() * (pos.sum() + 1) / 2.0) / (pos.sum() * neg.sum()))


def safe_corr(y_true: np.ndarray, y_pred: np.ndarray, method: str) -> float | None:
    if len(y_true) < 2 or np.std(y_true) < 1e-12 or np.std(y_pred) < 1e-12:
        return None
    return float(pd.Series(y_true).corr(pd.Series(y_pred), method=method))


def evaluate_folds(dataset: pd.DataFrame, features: pd.DataFrame, folds: list[tuple[str, np.ndarray, np.ndarray]], random_seed: int) -> tuple[dict[str, Any], pd.DataFrame]:
    x = features.to_numpy(dtype=float)
    y_reg = dataset["dynamic_stress_score"].to_numpy(dtype=float)
    y_cls = dataset["unstable_flag"].to_numpy(dtype=int)
    pred_reg = np.full(len(dataset), np.nan)
    pred_cls = np.full(len(dataset), np.nan)
    fold_rows = []
    skipped_cls_reasons: list[str] = []
    for fold_num, (fold_id, train_idx, test_idx) in enumerate(folds):
        coef = fit_ridge(x[train_idx], y_reg[train_idx])
        pred_reg[test_idx] = predict_linear(coef, x[test_idx])
        if len(np.unique(y_cls[train_idx])) >= 2:
            model = fit_logistic(x[train_idx], y_cls[train_idx], random_seed + fold_num)
            pred_cls[test_idx] = predict_logistic(model, x[test_idx])
        else:
            skipped_cls_reasons.append("Training fold has only one unstable_flag class.")
        fold_rows.append({"fold_id": fold_id, "num_train": int(len(train_idx)), "num_test": int(len(test_idx))})
    valid = ~np.isnan(pred_reg)
    cls_valid = ~np.isnan(pred_cls)
    y_cls_valid = y_cls[cls_valid]
    metrics = {
        "regression": regression_metrics(y_reg[valid], pred_reg[valid]),
        "classification": classification_metrics(y_cls_valid, pred_cls[cls_valid]) if cls_valid.any() and len(np.unique(y_cls_valid)) >= 2 else {},
        "classification_skipped_reason": "" if cls_valid.any() and len(np.unique(y_cls_valid)) >= 2 else ("; ".join(sorted(set(skipped_cls_reasons))) or "Test predictions contain only one unstable_flag class."),
        "num_predictions": int(valid.sum()),
        "num_folds": int(len(folds)),
        "folds": fold_rows,
    }
    predictions = dataset[["scenario_id", "label_family", "fault_type", "line_id", "target_bus", "target_bus_or_component"]].copy()
    predictions["y_true_dynamic_stress_score"] = y_reg
    predictions["y_pred_dynamic_stress_score"] = pred_reg
    predictions["absolute_error"] = np.abs(y_reg - pred_reg)
    predictions["y_true_unstable_flag"] = y_cls
    predictions["y_pred_unstable_probability"] = pred_cls
    return metrics, predictions


def leave_one_out_folds(n: int) -> list[tuple[str, np.ndarray, np.ndarray]]:
    idx = np.arange(n)
    return [(f"loo_{i}", np.setdiff1d(idx, [i]), np.array([i])) for i in range(n)]


def label_family_holdout_folds(dataset: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    family = dataset["label_family"].astype(str)
    return [("holdout_non_line_trip", np.where(family.eq("existing_formal_dynamic"))[0], np.where(family.eq("non_line_trip"))[0])]


def bus_fault_holdout_folds(dataset: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    is_b39 = dataset["scenario_id"].astype(str).eq("BF_B39_TEMP_SMOKE").to_numpy()
    return [("holdout_b39_bus_fault", np.where(~is_b39)[0], np.where(is_b39)[0])]


def run_one_mode(name: str, dataset: pd.DataFrame, feature_set: str, split_strategy: str, out_dir: Path, random_seed: int, extra: dict[str, Any]) -> dict[str, Any]:
    features, feature_columns = build_features(dataset, feature_set)
    if split_strategy == "leave_one_out":
        folds = leave_one_out_folds(len(dataset))
    elif split_strategy == "label_family_holdout":
        folds = label_family_holdout_folds(dataset)
    elif split_strategy == "bus_fault_holdout":
        folds = bus_fault_holdout_folds(dataset)
    else:
        raise ValueError(f"Unsupported split strategy: {split_strategy}")
    metrics, predictions = evaluate_folds(dataset, features, folds, random_seed)
    b39_rows = dataset["scenario_id"].astype(str).eq("BF_B39_TEMP_SMOKE")
    nf06_rows = dataset["scenario_id"].astype(str).eq("NF06")
    payload = {
        "preview_only": True,
        "final_performance_conclusion": False,
        "mode": name,
        "feature_set": feature_set,
        "split_strategy": split_strategy,
        "model_regression": "Ridge Regression",
        "model_classification": "Logistic Regression",
        "random_seed": int(random_seed),
        "num_samples": int(len(dataset)),
        "contains_b39": bool(b39_rows.any()),
        "contains_nf06": bool(nf06_rows.any()),
        "num_bus_fault_candidates": int(dataset["bus_fault_label"].sum()),
        "num_non_line_trip_candidates": int(dataset["label_family"].astype(str).eq("non_line_trip").sum()),
        "num_formal_v1_rows": int(dataset["label_family"].astype(str).eq("existing_formal_dynamic").sum()),
        "num_handwired_line_trip": int(dataset["handwired_line_trip_label"].sum()),
        "dynamic_stress_score_is_proxy_target": True,
        "target_feature_leakage_risk": feature_set != "no_dynamic_measurement_features",
        "leakage_reduced": feature_set == "no_dynamic_measurement_features",
        "feature_columns": feature_columns,
        "regression_metrics": metrics["regression"],
        "classification_metrics": metrics["classification"],
        "classification_skipped_reason": metrics["classification_skipped_reason"],
        "folds": metrics["folds"],
        "notes": [
            "preview-only / sanity check",
            "not GCN training",
            "phasor_RMS is not EMT",
            "generator_speed_proxy is not direct frequency",
            "temporary bus-fault injection is not engineering-grade protection",
        ],
        **extra,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "preview_training_metrics.json", payload)
    predictions.to_csv(out_dir / "preview_training_predictions.csv", index=False, encoding="utf-8-sig")
    return payload


def render_comparison_md(comparison: dict[str, Any]) -> str:
    return f"""# IEEE39 v2-plus-B39 Dynamic-Aware Reranker Preview Training

This is preview-only and `final_performance_conclusion = false`. It is dynamic-aware reranker preview training, not GCN training. It does not run Simulink and does not submit `.slx`.

## Counts

- previous_v2_candidate_count: `{comparison['previous_v2_candidate_count']}`
- v2_plus_b39_candidate_count: `{comparison['v2_plus_b39_candidate_count']}`
- b39_candidate_count: `{comparison['b39_candidate_count']}`
- old_formal_gate: `{comparison['old_formal_gate']}`
- L12 excluded: `{str(comparison['l12_excluded']).lower()}`
- NF06 provenance warning preserved: `{str(comparison['nf06_provenance_warning_preserved']).lower()}`

## Metrics Summary

| mode | samples | regression RMSE | classification F1 | note |
| --- | ---: | ---: | ---: | --- |
| include_all_41_candidates | {comparison['include_all_41_metrics']['num_samples']} | {comparison['include_all_41_metrics']['regression_metrics']['rmse']:.6f} | {comparison['include_all_41_metrics']['classification_metrics'].get('f1')} | compact dynamic measurements included |
| exclude_provenance_required | {comparison['exclude_provenance_metrics']['num_samples']} | {comparison['exclude_provenance_metrics']['regression_metrics']['rmse']:.6f} | {comparison['exclude_provenance_metrics']['classification_metrics'].get('f1')} | NF06 removed |
| no_dynamic_measurement_features | {comparison['no_dynamic_measurement_features_metrics']['num_samples']} | {comparison['no_dynamic_measurement_features_metrics']['regression_metrics']['rmse']:.6f} | {comparison['no_dynamic_measurement_features_metrics']['classification_metrics'].get('f1')} | leakage reduced |
| label_family_holdout | {comparison['label_family_holdout_metrics']['num_samples']} | {comparison['label_family_holdout_metrics']['regression_metrics']['rmse']:.6f} | {comparison['label_family_holdout_metrics']['classification_metrics'].get('f1')} | train formal, test non-line-trip |
| bus_fault_holdout | {comparison['bus_fault_holdout_metrics']['num_samples']} | {comparison['bus_fault_holdout_metrics']['regression_absolute_error']:.6f} | {comparison['bus_fault_holdout_metrics'].get('classification_probability_if_available')} | B39-only test |

## Interpretation

- `dynamic_stress_score` is a proxy target synthesized from compact dynamic measurements.
- Strong include-all metrics can reflect target-feature leakage because compact dynamic measurements are also input features.
- The no_dynamic_measurement_features mode is the no-leakage sanity check.
- B39 is only one bus-fault sample, so the B39 holdout result cannot represent all bus faults.
- NF06 provenance warning remains.
- Label-family holdout remains important.

## Boundaries

The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency. The temporary bus-fault injection is not engineering-grade protection.
"""


def run_preview(args: argparse.Namespace) -> dict[str, Any]:
    raw = pd.read_csv(args.combined_candidates)
    review = json.loads(args.composition_review.read_text(encoding="utf-8"))
    if not (review.get("b39_schema_consistency_passed") and review.get("count_consistency_passed") and review.get("export_boundary_passed")):
        raise ValueError("v2-plus-B39 composition review must pass before preview training.")
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    all_dataset = prepare_dataset(raw, exclude_provenance_required=False)
    exclude_dataset = prepare_dataset(raw, exclude_provenance_required=True)
    include_metrics = run_one_mode(
        "include_all_41_candidates",
        all_dataset,
        "with_dynamic_measurement_features",
        "leave_one_out",
        out_dir / "include_all_41_candidates",
        args.random_seed,
        {"cv_strategy": "leave_one_out"},
    )
    exclude_metrics = run_one_mode(
        "exclude_provenance_required",
        exclude_dataset,
        "with_dynamic_measurement_features",
        "leave_one_out",
        out_dir / "exclude_provenance_required",
        args.random_seed,
        {"excluded_provenance_required": True, "cv_strategy": "leave_one_out"},
    )
    no_dynamic_metrics = run_one_mode(
        "no_dynamic_measurement_features",
        all_dataset,
        "no_dynamic_measurement_features",
        "leave_one_out",
        out_dir / "no_dynamic_measurement_features",
        args.random_seed,
        {"cv_strategy": "leave_one_out"},
    )
    label_holdout_metrics = run_one_mode(
        "label_family_holdout",
        all_dataset,
        "with_dynamic_measurement_features",
        "label_family_holdout",
        out_dir / "label_family_holdout",
        args.random_seed,
        {
            "train_label_family": "existing_formal_dynamic",
            "test_label_family": "non_line_trip",
            "num_test_non_line_trip": int(all_dataset["label_family"].astype(str).eq("non_line_trip").sum()),
            "num_test_bus_fault": int(all_dataset["bus_fault_label"].sum()),
        },
    )
    bus_holdout_metrics = run_one_mode(
        "bus_fault_holdout",
        all_dataset,
        "with_dynamic_measurement_features",
        "bus_fault_holdout",
        out_dir / "bus_fault_holdout",
        args.random_seed,
        {
            "num_test": 1,
            "test_scenario_id": "BF_B39_TEMP_SMOKE",
            "target_bus": "B39",
        },
    )
    b39_pred = pd.read_csv(out_dir / "bus_fault_holdout" / "preview_training_predictions.csv")
    b39_pred = b39_pred[b39_pred["scenario_id"].astype(str).eq("BF_B39_TEMP_SMOKE")].iloc[0]
    bus_holdout_metrics.update(
        {
            "true_dynamic_stress_score": float(b39_pred["y_true_dynamic_stress_score"]),
            "predicted_dynamic_stress_score": float(b39_pred["y_pred_dynamic_stress_score"]),
            "regression_absolute_error": float(b39_pred["absolute_error"]),
            "true_unstable_flag": int(b39_pred["y_true_unstable_flag"]),
            "classification_probability_if_available": None if pd.isna(b39_pred["y_pred_unstable_probability"]) else float(b39_pred["y_pred_unstable_probability"]),
            "skipped_metrics_reason": "Only one B39 bus-fault test sample; aggregate Pearson/Spearman/ROC-AUC/F1 are not meaningful.",
        }
    )
    _write_json(out_dir / "bus_fault_holdout" / "preview_training_metrics.json", bus_holdout_metrics)

    comparison = {
        "preview_only": True,
        "final_performance_conclusion": False,
        "previous_v2_candidate_count": 40,
        "v2_plus_b39_candidate_count": int(len(all_dataset)),
        "b39_candidate_count": int(all_dataset["scenario_id"].astype(str).eq("BF_B39_TEMP_SMOKE").sum()),
        "old_formal_gate": "35 / 33 / 33",
        "l12_excluded": True,
        "nf06_provenance_warning_preserved": True,
        "b39_schema_consistency_passed": True,
        "include_all_41_metrics": include_metrics,
        "exclude_provenance_metrics": exclude_metrics,
        "no_dynamic_measurement_features_metrics": no_dynamic_metrics,
        "label_family_holdout_metrics": label_holdout_metrics,
        "bus_fault_holdout_metrics": bus_holdout_metrics,
        "leakage_interpretation": "include_all uses compact dynamic measurements that also define the proxy target; no_dynamic_measurement_features is the reduced-leakage sanity check.",
        "b39_holdout_interpretation": "B39 holdout is a one-sample bus-fault sanity check only, not final bus-fault generalization.",
        "recommended_next_step": "Use bus_fault_holdout and no-leakage comparison to decide whether to collect more bus-fault labels before connecting dynamic labels back to the main GCN/reranker workflow.",
        "caveats": [
            "B39 is candidate label only, not formal label",
            "B39 is only one bus-fault sample",
            "NF06 provenance warning remains",
            "label-family holdout remains important",
            "phasor_RMS is not EMT",
            "generator_speed_proxy is not direct frequency",
            "temporary bus-fault injection is not engineering-grade protection",
        ],
    }
    _write_json(out_dir / "v2_plus_b39_preview_comparison.json", comparison)
    (out_dir / "v2_plus_b39_preview_comparison.md").write_text(render_comparison_md(comparison), encoding="utf-8")
    print(json.dumps(_json_safe({"comparison": str(out_dir / "v2_plus_b39_preview_comparison.json")}), indent=2))
    return comparison


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combined-candidates", type=Path, required=True)
    parser.add_argument("--composition-review", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--random-seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    run_preview(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
