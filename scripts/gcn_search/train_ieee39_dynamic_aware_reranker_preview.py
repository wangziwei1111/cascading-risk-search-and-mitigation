from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_DYNAMIC_LABEL_SUMMARY = "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json"
DEFAULT_TRAINING_READINESS = "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json"
DEFAULT_FAULT_SUMMARY = (
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/"
    "ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08.csv"
)
DEFAULT_OUTPUT_DIR = "results/gcn_search/ieee39_dynamic_aware_reranker_preview"

BASE_NUMERIC_FEATURES = [
    "line_id_numeric",
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "breaker_opened",
    "physical_fault_or_breaker_action_executed",
]
CATEGORICAL_FEATURES = ["line_id", "fault_type", "trip_implementation"]
TARGET_COLUMNS = ["dynamic_stress_score", "unstable_flag"]


@dataclass(frozen=True)
class PreviewTrainingConfig:
    dynamic_label_summary: str = DEFAULT_DYNAMIC_LABEL_SUMMARY
    training_readiness: str = DEFAULT_TRAINING_READINESS
    fault_summary_csv: str = DEFAULT_FAULT_SUMMARY
    output_dir: str = DEFAULT_OUTPUT_DIR
    random_seed: int = 42
    ridge_alpha: float = 1.0
    logistic_l2: float = 0.1
    logistic_learning_rate: float = 0.2
    logistic_epochs: int = 800


def run_preview_training(config: PreviewTrainingConfig) -> dict[str, str]:
    quality = _read_json(Path(config.dynamic_label_summary))
    readiness = _read_json(Path(config.training_readiness))
    _assert_gate_open(quality, readiness)

    out_dir = Path(config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(config.fault_summary_csv)
    dataset = build_preview_dataset(raw)
    if dataset.empty:
        raise RuntimeError("No preview training rows after applying training_ready and measurement filters.")

    feature_table, feature_columns = build_feature_matrix(dataset)
    y_reg = dataset["dynamic_stress_score"].to_numpy(dtype=float)
    y_cls = dataset["unstable_flag"].to_numpy(dtype=int)

    regression = leave_one_out_ridge(feature_table.to_numpy(dtype=float), y_reg, alpha=config.ridge_alpha)
    classification = leave_one_out_logistic(
        feature_table.to_numpy(dtype=float),
        y_cls,
        l2=config.logistic_l2,
        learning_rate=config.logistic_learning_rate,
        epochs=config.logistic_epochs,
        random_seed=config.random_seed,
    )

    predictions = dataset[
        [
            "line_id",
            "test_case",
            "source_model",
            "fault_type",
            "trip_implementation",
            "unstable_flag",
            "dynamic_stress_score",
        ]
    ].copy()
    predictions = predictions.rename(
        columns={
            "dynamic_stress_score": "y_true_dynamic_stress_score",
            "unstable_flag": "y_true_unstable_flag",
        }
    )
    predictions["y_pred_dynamic_stress_score"] = regression["predictions"]
    predictions["residual"] = predictions["y_true_dynamic_stress_score"] - predictions["y_pred_dynamic_stress_score"]
    predictions["fold_id"] = np.arange(len(predictions), dtype=int)
    predictions["note"] = "leave-one-out preview prediction; not a final dynamic performance result"
    if classification["trained"]:
        predictions["y_pred_unstable_score"] = classification["probabilities"]
    else:
        predictions["y_pred_unstable_score"] = np.nan

    regression_metrics = regression["metrics"]
    classification_metrics = classification["metrics"] if classification["trained"] else {}
    skipped_reason = "" if classification["trained"] else classification["skipped_classification_reason"]
    metrics = {
        "preview_only": True,
        "allowed_for_dynamic_aware_training": bool(readiness.get("allowed_for_dynamic_aware_training")),
        "ready_for_preview_training": bool(readiness.get("ready_for_preview_training")),
        "num_samples": int(len(dataset)),
        "num_training_ready_labels": int(quality.get("num_training_ready_labels", 0)),
        "num_handwired_line_trip_labels": int(quality.get("num_training_ready_handwired_line_trip_labels", 0)),
        "num_unique_handwired_line_ids": int(quality.get("num_unique_handwired_line_ids", 0)),
        "target_columns": TARGET_COLUMNS,
        "feature_columns": feature_columns,
        "cv_strategy": "leave_one_out",
        "random_seed": int(config.random_seed),
        "regression_metrics": regression_metrics,
        "classification_metrics": classification_metrics,
        "skipped_metrics_reason": skipped_reason,
        "notes": [
            "Preview-only small-sample sanity check.",
            "phasor_RMS, not EMT.",
            "generator_speed_proxy is not direct frequency.",
            "handwired breaker is pilot breaker-like validation, not engineering-grade protection.",
        ],
    }

    coefficients = fit_ridge(feature_table.to_numpy(dtype=float), y_reg, alpha=config.ridge_alpha)
    coefficient_table = pd.DataFrame(
        {
            "feature": ["intercept"] + feature_columns,
            "coefficient": coefficients.tolist(),
            "abs_coefficient": np.abs(coefficients).tolist(),
        }
    ).sort_values("abs_coefficient", ascending=False)

    model_summary = {
        "model_type": "ridge_regression_preview",
        "feature_columns": feature_columns,
        "target_columns": TARGET_COLUMNS,
        "ridge_coefficients": dict(zip(["intercept"] + feature_columns, coefficients.tolist())),
        "logistic_available": bool(classification["trained"]),
        "preview_only": True,
    }

    dataset_path = out_dir / "preview_training_dataset.csv"
    config_path = out_dir / "preview_training_config.json"
    metrics_path = out_dir / "preview_training_metrics.json"
    predictions_path = out_dir / "preview_training_predictions.csv"
    coefficients_path = out_dir / "preview_model_coefficients.csv"
    model_path = out_dir / "preview_dynamic_aware_reranker_model.json"
    readme_path = out_dir / "preview_training_readme.md"

    dataset.to_csv(dataset_path, index=False, encoding="utf-8-sig")
    config_path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    metrics_path.write_text(json.dumps(_json_safe(metrics), ensure_ascii=False, indent=2), encoding="utf-8")
    predictions.to_csv(predictions_path, index=False, encoding="utf-8-sig")
    coefficient_table.to_csv(coefficients_path, index=False, encoding="utf-8-sig")
    model_path.write_text(json.dumps(_json_safe(model_summary), ensure_ascii=False, indent=2), encoding="utf-8")
    readme_path.write_text(make_readme(metrics, dataset_path, predictions_path, metrics_path), encoding="utf-8")

    return {
        "output_dir": str(out_dir),
        "dataset": str(dataset_path),
        "config": str(config_path),
        "metrics": str(metrics_path),
        "predictions": str(predictions_path),
        "coefficients": str(coefficients_path),
        "model": str(model_path),
        "readme": str(readme_path),
    }


def build_preview_dataset(raw: pd.DataFrame) -> pd.DataFrame:
    work = raw.copy()
    ready = work["training_ready_candidate"].astype(str).str.lower().isin({"1", "true"})
    measured = work["measurement_extraction_status"].astype(str).eq("voltage_speed_angle")
    work = work.loc[ready & measured].copy()
    numeric_columns = [
        "min_voltage_pu",
        "max_voltage_pu",
        "min_frequency_hz",
        "max_frequency_hz",
        "max_speed_deviation",
        "max_rotor_angle_separation_deg",
        "breaker_opened",
        "physical_fault_or_breaker_action_executed",
    ]
    for column in numeric_columns:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna(subset=["min_voltage_pu", "max_frequency_hz", "max_speed_deviation", "max_rotor_angle_separation_deg"]).copy()
    work["line_id"] = work["tripped_line"].fillna("NO_LINE").astype(str)
    work["source_model"] = work["source_model"].fillna("unknown").astype(str)
    work["fault_type"] = work["fault_type"].fillna("unknown").astype(str)
    work["trip_implementation"] = work["trip_implementation"].fillna("unknown").astype(str)
    work["line_id_numeric"] = work["line_id"].map(_line_id_to_number).astype(float)
    work["unstable_flag"] = pd.to_numeric(work["unstable_flag"], errors="coerce").fillna(0).astype(int)
    work["dynamic_stress_score"] = compute_dynamic_stress_score(work)
    return work.reset_index(drop=True)


def build_feature_matrix(dataset: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    features = dataset[BASE_NUMERIC_FEATURES].copy()
    one_hot = pd.get_dummies(dataset[CATEGORICAL_FEATURES].astype(str), prefix=CATEGORICAL_FEATURES, dtype=float)
    features = pd.concat([features, one_hot], axis=1)
    features = features.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return features, list(features.columns)


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
    return (
        0.35 * voltage_sag
        + 0.25 * (frequency_excursion_hz / 1.0)
        + 0.20 * (speed * 100.0)
        + 0.20 * (angle / 180.0)
    )


def leave_one_out_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> dict[str, Any]:
    preds = np.zeros(len(y), dtype=float)
    for idx in range(len(y)):
        mask = np.ones(len(y), dtype=bool)
        mask[idx] = False
        coef = fit_ridge(x[mask], y[mask], alpha=alpha)
        preds[idx] = predict_linear(coef, x[idx : idx + 1])[0]
    return {"predictions": preds, "metrics": regression_metrics(y, preds)}


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_aug = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(x_aug.shape[1]) * float(alpha)
    penalty[0, 0] = 0.0
    return np.linalg.pinv(x_aug.T @ x_aug + penalty) @ x_aug.T @ y


def predict_linear(coef: np.ndarray, x: np.ndarray) -> np.ndarray:
    x_aug = np.column_stack([np.ones(len(x)), x])
    return x_aug @ coef


def leave_one_out_logistic(
    x: np.ndarray,
    y: np.ndarray,
    l2: float,
    learning_rate: float,
    epochs: int,
    random_seed: int,
) -> dict[str, Any]:
    unique = np.unique(y)
    if len(unique) < 2:
        return {
            "trained": False,
            "probabilities": np.full(len(y), np.nan),
            "metrics": {},
            "skipped_classification_reason": "Only one unstable_flag class is present.",
        }
    preds = np.zeros(len(y), dtype=float)
    for idx in range(len(y)):
        mask = np.ones(len(y), dtype=bool)
        mask[idx] = False
        if len(np.unique(y[mask])) < 2:
            return {
                "trained": False,
                "probabilities": np.full(len(y), np.nan),
                "metrics": {},
                "skipped_classification_reason": "Leave-one-out fold has only one unstable_flag class.",
            }
        model = fit_logistic(x[mask], y[mask], l2=l2, learning_rate=learning_rate, epochs=epochs, random_seed=random_seed + idx)
        preds[idx] = predict_logistic(model, x[idx : idx + 1])[0]
    return {
        "trained": True,
        "probabilities": preds,
        "metrics": classification_metrics(y, preds),
        "skipped_classification_reason": "",
    }


def fit_logistic(x: np.ndarray, y: np.ndarray, l2: float, learning_rate: float, epochs: int, random_seed: int) -> dict[str, np.ndarray | float]:
    rng = np.random.default_rng(random_seed)
    x_scaled, mean, std = standardize(x)
    weight = rng.normal(0.0, 0.02, size=x_scaled.shape[1])
    bias = 0.0
    pos_weight = float((len(y) - y.sum()) / max(float(y.sum()), 1.0))
    for _ in range(int(epochs)):
        logits = np.clip(x_scaled @ weight + bias, -30.0, 30.0)
        prob = 1.0 / (1.0 + np.exp(-logits))
        sample_weight = np.where(y > 0.5, pos_weight, 1.0)
        grad = (prob - y) * sample_weight
        weight -= learning_rate * ((x_scaled.T @ grad) / len(y) + l2 * weight)
        bias -= learning_rate * float(grad.mean())
    return {"weight": weight, "bias": bias, "mean": mean, "std": std}


def predict_logistic(model: dict[str, np.ndarray | float], x: np.ndarray) -> np.ndarray:
    x_scaled = (x - np.asarray(model["mean"])) / np.asarray(model["std"])
    logits = np.clip(x_scaled @ np.asarray(model["weight"]) + float(model["bias"]), -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-logits))


def standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std < 1e-8] = 1.0
    return (x - mean) / std, mean, std


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    residual = y_true - y_pred
    result = {
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "pearson": safe_corr(y_true, y_pred, method="pearson"),
        "spearman": safe_corr(y_true, y_pred, method="spearman"),
    }
    return result


def classification_metrics(y_true: np.ndarray, score: np.ndarray) -> dict[str, float | None]:
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


def make_readme(metrics: dict[str, Any], dataset_path: Path, predictions_path: Path, metrics_path: Path) -> str:
    return f"""# IEEE39 Dynamic-Aware Reranker Preview Training

This is a preview-only sanity check, not a final dynamic performance conclusion.

- Model family: lightweight ridge regression with leave-one-out preview validation.
- Dataset: `{dataset_path.as_posix()}`
- Predictions: `{predictions_path.as_posix()}`
- Metrics: `{metrics_path.as_posix()}`
- num_samples: {metrics['num_samples']}
- num_training_ready_labels: {metrics['num_training_ready_labels']}
- allowed_for_dynamic_aware_training: {str(metrics['allowed_for_dynamic_aware_training']).lower()}
- ready_for_preview_training: {str(metrics['ready_for_preview_training']).lower()}

Boundaries:

- The IEEE39 model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker workflow is pilot breaker-like validation, not engineering-grade protection.
- The current sample count is small, so metrics are workflow/sanity-check evidence only.
"""


def _line_id_to_number(value: str) -> int:
    if value.startswith("L") and value[1:].isdigit():
        return int(value[1:])
    return 0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_gate_open(quality: dict[str, Any], readiness: dict[str, Any]) -> None:
    if int(quality.get("num_training_ready_labels", 0)) < 10:
        raise RuntimeError("Refusing preview training: num_training_ready_labels < 10.")
    if readiness.get("allowed_for_dynamic_aware_training") is not True:
        raise RuntimeError("Refusing preview training: allowed_for_dynamic_aware_training is not true.")
    if readiness.get("ready_for_preview_training") is not True:
        raise RuntimeError("Refusing preview training: ready_for_preview_training is not true.")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IEEE39 dynamic-aware reranker preview training.")
    parser.add_argument("--dynamic-label-summary", default=DEFAULT_DYNAMIC_LABEL_SUMMARY)
    parser.add_argument("--training-readiness", default=DEFAULT_TRAINING_READINESS)
    parser.add_argument("--fault-summary-csv", default=DEFAULT_FAULT_SUMMARY)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--random-seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_preview_training(
        PreviewTrainingConfig(
            dynamic_label_summary=args.dynamic_label_summary,
            training_readiness=args.training_readiness,
            fault_summary_csv=args.fault_summary_csv,
            output_dir=args.output_dir,
            random_seed=args.random_seed,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
