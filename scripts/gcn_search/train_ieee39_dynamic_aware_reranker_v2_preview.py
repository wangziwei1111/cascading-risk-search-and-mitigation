"""Run IEEE39 v2 dynamic-aware reranker preview training.

This is a lightweight preview/sanity-check trainer. It uses the v2 combined
candidate schema, supports excluding provenance-required rows, and writes
preview-only metrics. It does not run Simulink and does not create checkpoints.
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
TARGET_COLUMNS = ["dynamic_stress_score", "unstable_flag"]
NUMERIC_FEATURES = [
    "line_id_numeric",
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "breaker_opened",
    "physical_fault_or_breaker_action_executed",
    "duration_s",
    "fault_start_s",
    "fault_clear_s",
    "formal_line_trip_label",
    "handwired_line_trip_label",
    "non_line_trip_label",
    "provenance_check_required",
]
CATEGORICAL_FEATURES = ["label_family", "fault_type", "trip_implementation", "line_id"]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_json_safe(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _line_id_to_number(value: Any) -> int:
    text = str(value)
    if text.startswith("L") and text[1:].isdigit():
        return int(text[1:])
    return 0


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


def build_dataset(raw: pd.DataFrame, exclude_provenance_required: bool) -> pd.DataFrame:
    work = raw.copy()
    work = work[work["training_ready_label_v2"].map(_boolish)].copy()
    if exclude_provenance_required:
        work = work[~work["provenance_check_required"].map(_boolish)].copy()
    work = work[work["measurement_extraction_status"].astype(str).eq("voltage_speed_angle")].copy()
    joined = work.to_json().lower()
    if "l12" in joined:
        raise ValueError("L12 must remain excluded from v2 preview dataset.")
    if work.empty:
        raise ValueError("No rows available for v2 preview training.")
    if "line_id" not in work.columns:
        work["line_id"] = ""
    work["line_id"] = work["line_id"].fillna("").replace("", "NO_LINE").astype(str)
    no_line = work["line_id"].eq("NO_LINE")
    if "target_bus_or_component" in work.columns:
        target = work["target_bus_or_component"].fillna("").astype(str)
        work.loc[no_line & target.str.startswith("L"), "line_id"] = target[no_line & target.str.startswith("L")]
    if "source_smoke_scenario_id" in work.columns:
        smoke_id = work["source_smoke_scenario_id"].fillna("").astype(str)
        work.loc[smoke_id.ne(""), "line_id"] = "NO_LINE"
    work["line_id_numeric"] = work["line_id"].map(_line_id_to_number).astype(float)
    for col in NUMERIC_FEATURES:
        if col not in work.columns:
            work[col] = 0.0
        if col in {"formal_line_trip_label", "handwired_line_trip_label", "non_line_trip_label", "provenance_check_required", "breaker_opened", "physical_fault_or_breaker_action_executed"}:
            work[col] = work[col].map(_boolish).astype(float)
        else:
            work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
    for col in CATEGORICAL_FEATURES:
        if col not in work.columns:
            work[col] = "unknown"
        work[col] = work[col].fillna("unknown").astype(str)
    work["unstable_flag"] = work["unstable_flag"].map(_boolish).astype(int)
    work["dynamic_stress_score"] = compute_dynamic_stress_score(work)
    work["preview_only"] = True
    work["final_performance_conclusion"] = False
    return work.reset_index(drop=True)


def build_features(dataset: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    numeric = dataset[NUMERIC_FEATURES].copy()
    one_hot = pd.get_dummies(dataset[CATEGORICAL_FEATURES], prefix=CATEGORICAL_FEATURES, dtype=float)
    features = pd.concat([numeric, one_hot], axis=1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return features, list(features.columns)


def _numeric_true_count(series: pd.Series) -> int:
    return int(pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float).round().clip(lower=0.0).sum())


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


def fit_logistic(x: np.ndarray, y: np.ndarray, random_seed: int, l2: float = 0.1, lr: float = 0.2, epochs: int = 800) -> dict[str, Any]:
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
        weight -= lr * ((x_scaled.T @ grad) / len(y) + l2 * weight)
        bias -= lr * float(grad.mean())
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
    return {"accuracy": float((tp + tn) / max(len(y_true), 1)), "f1": float(f1), "roc_auc": binary_auc(y_true, score)}


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


def evaluate_splits(dataset: pd.DataFrame, features: pd.DataFrame, random_seed: int) -> tuple[dict[str, Any], pd.DataFrame]:
    x = features.to_numpy(dtype=float)
    y_reg = dataset["dynamic_stress_score"].to_numpy(dtype=float)
    y_cls = dataset["unstable_flag"].to_numpy(dtype=int)
    split_defs = {
        "leave_one_out": [(f"loo_{i}", np.setdiff1d(np.arange(len(dataset)), [i]), np.array([i])) for i in range(len(dataset))],
        "random_kfold_baseline": random_kfold_indices(len(dataset), 5, random_seed),
        "label_family_holdout": label_family_holdout_indices(dataset),
    }
    all_predictions = []
    metrics: dict[str, Any] = {}
    for split_name, folds in split_defs.items():
        pred_reg = np.full(len(dataset), np.nan)
        pred_cls = np.full(len(dataset), np.nan)
        fold_rows = []
        skipped_cls = ""
        for fold_id, train_idx, test_idx in folds:
            coef = fit_ridge(x[train_idx], y_reg[train_idx])
            pred_reg[test_idx] = predict_linear(coef, x[test_idx])
            if len(np.unique(y_cls[train_idx])) >= 2:
                model = fit_logistic(x[train_idx], y_cls[train_idx], random_seed + len(fold_rows))
                pred_cls[test_idx] = predict_logistic(model, x[test_idx])
            else:
                skipped_cls = "Training fold has only one unstable_flag class."
            fold_rows.append({"fold_id": fold_id, "num_train": int(len(train_idx)), "num_test": int(len(test_idx))})
        valid = ~np.isnan(pred_reg)
        cls_valid = ~np.isnan(pred_cls)
        split_metrics = {
            "regression": regression_metrics(y_reg[valid], pred_reg[valid]),
            "classification": classification_metrics(y_cls[cls_valid], pred_cls[cls_valid]) if cls_valid.any() and len(np.unique(y_cls[cls_valid])) >= 2 else {},
            "classification_skipped_reason": "" if cls_valid.any() and len(np.unique(y_cls[cls_valid])) >= 2 else (skipped_cls or "Test predictions contain only one unstable_flag class."),
            "num_predictions": int(valid.sum()),
            "num_folds": int(len(folds)),
            "folds": fold_rows,
        }
        metrics[split_name] = split_metrics
        pred_table = dataset[["scenario_id", "label_family", "fault_type", "line_id", "provenance_check_required", "duplicate_measurement_group"]].copy()
        pred_table["split_strategy"] = split_name
        pred_table["y_true_dynamic_stress_score"] = y_reg
        pred_table["y_pred_dynamic_stress_score"] = pred_reg
        pred_table["residual"] = y_reg - pred_reg
        pred_table["y_true_unstable_flag"] = y_cls
        pred_table["y_pred_unstable_score"] = pred_cls
        all_predictions.append(pred_table)
    return metrics, pd.concat(all_predictions, ignore_index=True)


def random_kfold_indices(n: int, k: int, seed: int) -> list[tuple[str, np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(seed)
    indices = np.arange(n)
    rng.shuffle(indices)
    folds = np.array_split(indices, k)
    result = []
    for i, test_idx in enumerate(folds):
        train_idx = np.setdiff1d(indices, test_idx)
        result.append((f"kfold_{i}", train_idx, test_idx))
    return result


def label_family_holdout_indices(dataset: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    family = dataset["label_family"].astype(str)
    folds = []
    if family.eq("non_line_trip").any() and family.eq("existing_formal_dynamic").any():
        test_idx = np.where(family.eq("non_line_trip"))[0]
        train_idx = np.where(family.eq("existing_formal_dynamic"))[0]
        folds.append(("holdout_non_line_trip", train_idx, test_idx))
    return folds


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


def validate_v2_gate(quality: dict[str, Any], readiness: dict[str, Any], duplicate: dict[str, Any]) -> None:
    required = {
        "original_formal_gate_preserved": True,
        "original_num_training_ready_labels": 35,
        "original_num_training_ready_handwired_line_trip_labels": 33,
        "original_num_unique_handwired_line_ids": 33,
        "num_non_line_trip_candidate_labels": 5,
        "num_training_ready_labels_v2_combined_candidate": 40,
    }
    for key, expected in required.items():
        if quality.get(key) != expected:
            raise ValueError(f"Unexpected v2 quality field {key}: {quality.get(key)}")
    if readiness.get("ready_for_v2_preview_training") is not True:
        raise ValueError("v2 readiness must set ready_for_v2_preview_training=true.")
    if readiness.get("should_train_now") is not False:
        raise ValueError("v2 readiness must preserve should_train_now=false.")
    if duplicate.get("provenance_check_required_scenarios") != ["NF06"]:
        raise ValueError("Duplicate/provenance report must mark NF06.")


def run_training(args: argparse.Namespace) -> dict[str, str]:
    quality = _read_json(args.v2_quality_summary)
    readiness = _read_json(args.v2_readiness)
    duplicate = _read_json(args.duplicate_provenance_report)
    validate_v2_gate(quality, readiness, duplicate)
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(args.combined_candidates)
    dataset = build_dataset(raw, args.exclude_provenance_required)
    expected_n = 39 if args.exclude_provenance_required else 40
    if len(dataset) != expected_n:
        raise ValueError(f"Expected {expected_n} samples, got {len(dataset)}")
    features, feature_columns = build_features(dataset)
    metrics_by_split, predictions = evaluate_splits(dataset, features, args.random_seed)
    coef = fit_ridge(features.to_numpy(dtype=float), dataset["dynamic_stress_score"].to_numpy(dtype=float))
    coefficients = pd.DataFrame(
        {"feature": ["intercept"] + feature_columns, "coefficient": coef, "abs_coefficient": np.abs(coef)}
    ).sort_values("abs_coefficient", ascending=False)
    include_nf06 = bool(dataset["scenario_id"].astype(str).eq("NF06").any())
    num_formal_v1_rows = int(dataset["label_family"].astype(str).eq("existing_formal_dynamic").sum())
    num_handwired_line_trip_rows = _numeric_true_count(dataset["handwired_line_trip_label"])
    provenance_check_required_rows = _numeric_true_count(dataset["provenance_check_required"])
    metrics = {
        "preview_only": True,
        "final_performance_conclusion": False,
        "mode": "exclude_provenance_required" if args.exclude_provenance_required else "include_all_candidates",
        "num_samples": int(len(dataset)),
        "contains_nf06": include_nf06,
        "excluded_provenance_required": bool(args.exclude_provenance_required),
        "num_formal_v1_rows": num_formal_v1_rows,
        "num_existing_formal_dynamic_rows": num_formal_v1_rows,
        "num_handwired_line_trip_rows": num_handwired_line_trip_rows,
        "num_non_line_trip_candidate_rows": int(dataset["label_family"].astype(str).eq("non_line_trip").sum()),
        "num_duplicate_measurement_groups": int(quality.get("num_duplicate_measurement_groups", 0)),
        "provenance_check_required_rows": provenance_check_required_rows,
        "num_provenance_check_required_rows": provenance_check_required_rows,
        "target_columns": TARGET_COLUMNS,
        "feature_columns": feature_columns,
        "random_seed": int(args.random_seed),
        "metrics_by_split": metrics_by_split,
        "regression_metrics": metrics_by_split["leave_one_out"]["regression"],
        "classification_metrics": metrics_by_split["leave_one_out"]["classification"],
        "label_family_holdout_metrics": metrics_by_split.get("label_family_holdout", {}),
        "notes": [
            "preview-only / sanity check",
            "phasor_RMS, not EMT",
            "generator_speed_proxy is not direct frequency",
            "relay proxy is not engineering-grade protection",
            "duplicate smoke candidates are not necessarily independent physical samples",
        ],
    }
    config = {
        "combined_candidates": str(args.combined_candidates),
        "v2_quality_summary": str(args.v2_quality_summary),
        "v2_readiness": str(args.v2_readiness),
        "duplicate_provenance_report": str(args.duplicate_provenance_report),
        "exclude_provenance_required": bool(args.exclude_provenance_required),
        "random_seed": int(args.random_seed),
    }
    model = {
        "model_type": "ridge_regression_preview",
        "preview_only": True,
        "final_performance_conclusion": False,
        "feature_columns": feature_columns,
        "ridge_coefficients": dict(zip(["intercept"] + feature_columns, coef.tolist())),
    }
    dataset.to_csv(out_dir / "preview_training_dataset.csv", index=False, encoding="utf-8-sig")
    _write_json(out_dir / "preview_training_config.json", config)
    _write_json(out_dir / "preview_training_metrics.json", metrics)
    predictions.to_csv(out_dir / "preview_training_predictions.csv", index=False, encoding="utf-8-sig")
    coefficients.to_csv(out_dir / "preview_model_coefficients.csv", index=False, encoding="utf-8-sig")
    _write_json(out_dir / "preview_dynamic_aware_reranker_model.json", model)
    (out_dir / "preview_training_readme.md").write_text(render_readme(metrics), encoding="utf-8")
    return {"output_dir": str(out_dir), "metrics": str(out_dir / "preview_training_metrics.json")}


def render_readme(metrics: dict[str, Any]) -> str:
    return f"""# IEEE39 v2 Dynamic-Aware Reranker Preview

This is preview-only and final_performance_conclusion=false.

- mode: `{metrics['mode']}`
- num_samples: `{metrics['num_samples']}`
- contains_nf06: `{metrics['contains_nf06']}`
- label_family_holdout is the key generalization smoke check.
- phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- relay proxy is not engineering-grade protection.
- duplicate smoke candidates are not necessarily independent physical samples.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combined-candidates", type=Path, required=True)
    parser.add_argument("--v2-quality-summary", type=Path, required=True)
    parser.add_argument("--v2-readiness", type=Path, required=True)
    parser.add_argument("--duplicate-provenance-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--exclude-provenance-required", action="store_true")
    return parser.parse_args()


def main() -> int:
    result = run_training(parse_args())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
