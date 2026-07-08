from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

LABEL_COLUMNS = {
    "critical",
    "critical_mechanism",
    "has_overload_cascade",
    "relay_cascade",
    "total_load_shed_mw",
    "num_relay_trips",
    "max_event_loading_ratio",
    "label_critical",
    "label_relay_cascade",
    "label_load_shed_positive",
}

INPUT_FEATURE_COLUMNS = [
    "first_line_loading_ratio",
    "candidate_second_line_loading_ratio",
    "candidate_second_line_rate_a",
    "candidate_second_line_pf",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a lightweight IEEE118 Step2-State GCN/PIO-GCN smoke scorer.")
    parser.add_argument(
        "--step2-csv",
        type=Path,
        default=ROOT
        / "results"
        / "gcn_search"
        / "ieee118_flow_scaled_800_step2_state"
        / "ieee118_step2_state_samples.csv",
    )
    parser.add_argument("--target", choices=["label_critical", "label_relay_cascade"], default="label_critical")
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--hidden-dim", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260708)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_gcn_smoke",
    )
    return parser.parse_args()


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing IEEE118 Step2-State CSV: {path}. Generate it locally first; this script will not regenerate large datasets."
        )


def input_feature_columns() -> list[str]:
    leakage = LABEL_COLUMNS.intersection(INPUT_FEATURE_COLUMNS)
    if leakage:
        raise RuntimeError(f"Label leakage in GCN smoke input feature list: {sorted(leakage)}")
    return list(INPUT_FEATURE_COLUMNS)


def load_step2_table(path: Path, target: str, max_samples: int | None = None) -> pd.DataFrame:
    require_file(path)
    columns = ["path", "first_line", "second_line", target] + input_feature_columns()
    table = pd.read_csv(path, usecols=columns, nrows=max_samples)
    missing = sorted(set(columns) - set(table.columns))
    if missing:
        raise ValueError(f"Step2-State CSV missing required columns: {missing}")
    return table


def make_splits(num_rows: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    indices = np.arange(num_rows)
    rng.shuffle(indices)
    train_end = max(1, int(0.7 * num_rows))
    val_end = max(train_end + 1, int(0.85 * num_rows)) if num_rows >= 3 else train_end
    return indices[:train_end], indices[train_end:val_end], indices[val_end:]


def standardize_features(x: np.ndarray, train_idx: np.ndarray) -> tuple[np.ndarray, dict]:
    mean = x[train_idx].mean(axis=0)
    std = x[train_idx].std(axis=0)
    std = np.where(std < 1e-8, 1.0, std)
    return (x - mean) / std, {"mean": mean.tolist(), "std": std.tolist(), "feature_columns": input_feature_columns()}


def binary_metrics(y_true: np.ndarray, score: np.ndarray) -> dict:
    pred = score >= 0.5
    positives = y_true == 1
    tp = int((pred & positives).sum())
    fp = int((pred & ~positives).sum())
    fn = int((~pred & positives).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "num_rows": int(len(y_true)),
        "positive_count": int(positives.sum()),
        "positive_ratio": float(positives.mean()) if len(y_true) else 0.0,
        "precision_at_0_5": float(precision),
        "recall_at_0_5": float(recall),
        "average_score_positive": float(score[positives].mean()) if positives.any() else 0.0,
        "average_score_negative": float(score[~positives].mean()) if (~positives).any() else 0.0,
    }


def sigmoid(value: np.ndarray) -> np.ndarray:
    clipped = np.clip(value, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def fit_logistic_smoke(
    x: np.ndarray,
    y: np.ndarray,
    train_idx: np.ndarray,
    *,
    epochs: int,
    learning_rate: float,
) -> tuple[np.ndarray, float, list[dict]]:
    weights = np.zeros(x.shape[1], dtype=np.float64)
    bias = 0.0
    y_train = y[train_idx].astype(np.float64)
    pos = max(float(y_train.sum()), 1.0)
    neg = max(float(len(y_train) - y_train.sum()), 1.0)
    pos_weight = neg / pos
    history = []
    for epoch in range(1, epochs + 1):
        logits = x[train_idx] @ weights + bias
        probs = sigmoid(logits)
        sample_weight = np.where(y_train > 0.5, pos_weight, 1.0)
        error = (probs - y_train) * sample_weight
        grad_w = (x[train_idx].T @ error) / max(len(train_idx), 1)
        grad_b = float(error.mean()) if len(error) else 0.0
        weights -= learning_rate * grad_w
        bias -= learning_rate * grad_b
        eps = 1e-9
        loss = -np.mean(sample_weight * (y_train * np.log(probs + eps) + (1.0 - y_train) * np.log(1.0 - probs + eps)))
        history.append({"epoch": epoch, "train_loss": float(loss)})
    return weights, bias, history


def train_smoke(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(args.seed)
    table = load_step2_table(args.step2_csv, args.target, args.max_samples)
    x_raw = table[input_feature_columns()].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=np.float32)
    y = pd.to_numeric(table[args.target], errors="coerce").fillna(0).to_numpy(dtype=np.float32)
    train_idx, val_idx, test_idx = make_splits(len(table), args.seed)
    x, normalizer = standardize_features(x_raw, train_idx)
    weights, bias, history = fit_logistic_smoke(
        x.astype(np.float64),
        y.astype(np.float64),
        train_idx,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
    )
    scores = sigmoid(x.astype(np.float64) @ weights + bias)

    predictions = table[["path", "first_line", "second_line", args.target]].copy()
    predictions.rename(columns={args.target: "target_label"}, inplace=True)
    predictions["gcn_score"] = scores
    predictions.sort_values(["gcn_score", "path"], ascending=[False, True]).to_csv(
        args.output_dir / "gcn_smoke_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )
    predictions.sort_values(["gcn_score", "path"], ascending=[False, True]).head(500).to_csv(
        args.output_dir / "gcn_smoke_top_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )
    metrics = {
        "target": args.target,
        "step2_csv": str(args.step2_csv),
        "max_samples": args.max_samples,
        "num_samples": int(len(table)),
        "feature_columns": input_feature_columns(),
        "excluded_label_columns": sorted(LABEL_COLUMNS),
        "train": binary_metrics(y[train_idx].astype(int), scores[train_idx]),
        "val": binary_metrics(y[val_idx].astype(int), scores[val_idx]) if len(val_idx) else {},
        "test": binary_metrics(y[test_idx].astype(int), scores[test_idx]) if len(test_idx) else {},
        "normalizer": normalizer,
        "model": {"type": "numpy_logistic_smoke", "weights": weights.tolist(), "bias": float(bias)},
        "history": history,
        "notes": "Lightweight smoke scorer over Step2-State graph-derived scalar features; not a final tuned GCN.",
    }
    (args.output_dir / "gcn_smoke_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (args.output_dir / "gcn_smoke_readme.md").write_text(
        "# IEEE118 GCN Smoke\n\n"
        "This is a lightweight smoke scorer for the IEEE118 Step2-State pipeline. It excludes label/leakage columns and is not a final tuned GCN result.\n",
        encoding="utf-8",
    )
    return metrics


def main() -> None:
    args = parse_args()
    metrics = train_smoke(args)
    print(f"IEEE118 GCN smoke outputs written to {args.output_dir}")
    print(json.dumps({key: metrics[key] for key in ["target", "num_samples", "feature_columns"]}, indent=2))


if __name__ == "__main__":
    main()
