from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


FORBIDDEN_LABEL_COLUMNS = {
    "opa_is_critical",
    "is_critical",
    "total_load_shed_mw",
    "opa_total_load_shed_mw",
    "oracle_rank",
    "truth_rank",
    "y_critical",
    "y_load_shed",
}

FEATURE_COLUMNS = [
    "rank_in_pio",
    "rank_in_paper",
    "rank_in_lodf",
    "pio_score",
    "paper_score",
    "lodf_score",
    "first_loading_ratio",
    "second_loading_ratio",
    "max_endpoint_loading_ratio",
    "min_security_margin",
    "min_relay_margin",
    "first_outage_num_overloaded_lines",
    "first_outage_max_loading_ratio",
    "candidate_position_min_rank",
]


@dataclass(frozen=True)
class TrainPathRerankerConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    output_dir: str = "results/gcn_search/path_reranker_models"
    model_type: str = "mlp"
    epochs: int = 120
    learning_rate: float = 0.08
    random_seed: int = 20260801


def train_path_reranker(config: TrainPathRerankerConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(Path(config.dataset_dir) / "path_reranker_train.csv")
    val = pd.read_csv(Path(config.dataset_dir) / "path_reranker_val.csv")
    test = pd.read_csv(Path(config.dataset_dir) / "path_reranker_test.csv")
    feature_columns = [col for col in FEATURE_COLUMNS if col in train.columns and col not in FORBIDDEN_LABEL_COLUMNS]
    model = _fit_logistic(train, feature_columns, config)
    model["model_type"] = config.model_type
    model["feature_columns"] = feature_columns
    model_path = out / "path_reranker_model.pkl"
    with model_path.open("wb") as handle:
        pickle.dump(model, handle)
    (out / "path_reranker_feature_columns.json").write_text(json.dumps({"feature_columns": feature_columns}, indent=2), encoding="utf-8")
    (out / "path_reranker_train_config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    predictions = pd.concat(
        [
            _predict_table(model, train, "train"),
            _predict_table(model, val, "val"),
            _predict_table(model, test, "test"),
        ],
        ignore_index=True,
    )
    predictions.to_csv(out / "path_reranker_validation_predictions.csv", index=False, encoding="utf-8-sig")
    metrics = pd.DataFrame([_metrics(predictions[predictions["split"] == split], split, config.model_type) for split in ["train", "val", "test"]])
    metrics.to_csv(out / "path_reranker_metrics.csv", index=False, encoding="utf-8-sig")
    return {"output_dir": str(out), "model_path": str(model_path), "metrics": str(out / "path_reranker_metrics.csv")}


def _fit_logistic(train: pd.DataFrame, feature_columns: list[str], config: TrainPathRerankerConfig) -> dict:
    rng = np.random.default_rng(config.random_seed)
    x_raw = train[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=float)
    y = train["y_critical"].to_numpy(dtype=float)
    mean = x_raw.mean(axis=0)
    std = x_raw.std(axis=0)
    std[std < 1e-8] = 1.0
    x = (x_raw - mean) / std
    weight = rng.normal(0.0, 0.05, size=x.shape[1])
    bias = 0.0
    pos_weight = float((len(y) - y.sum()) / max(y.sum(), 1.0))
    for _ in range(config.epochs):
        logits = x @ weight + bias
        prob = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
        sample_weight = np.where(y > 0.5, pos_weight, 1.0)
        grad = (prob - y) * sample_weight
        weight -= config.learning_rate * (x.T @ grad / len(y))
        bias -= config.learning_rate * float(grad.mean())
    return {"weight": weight, "bias": bias, "mean": mean, "std": std}


def _predict_table(model: dict, table: pd.DataFrame, split: str) -> pd.DataFrame:
    features = model["feature_columns"]
    x_raw = table[features].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=float)
    x = (x_raw - model["mean"]) / model["std"]
    score = 1.0 / (1.0 + np.exp(-np.clip(x @ model["weight"] + model["bias"], -30, 30)))
    keep = [
        "source_seed",
        "seed",
        "split",
        "path",
        "first_line",
        "second_line",
        "pio_score",
        "paper_score",
        "lodf_score",
        "opa_is_critical",
        "opa_total_load_shed_mw",
        "y_critical",
        "y_load_shed",
    ]
    result = table[[col for col in keep if col in table.columns]].copy()
    result["split"] = split
    result["model_type"] = model.get("model_type", "mlp")
    result["learned_score"] = score
    return result


def _metrics(predictions: pd.DataFrame, split: str, model_type: str) -> dict:
    if predictions.empty:
        return {"split": split, "model_type": model_type, "num_samples": 0, "num_critical": 0, "precision_at_20": 0.0}
    ordered = predictions.sort_values(["learned_score", "path"], ascending=[False, True])
    top20 = ordered.head(20)
    total = max(int(predictions["y_critical"].sum()), 1)
    return {
        "split": split,
        "model_type": model_type,
        "num_samples": int(len(predictions)),
        "num_critical": int(predictions["y_critical"].sum()),
        "precision_at_20": float(top20["y_critical"].mean()) if len(top20) else 0.0,
        "recall_at_20": float(top20["y_critical"].sum() / total),
        "mean_positive_score": float(predictions.loc[predictions["y_critical"] == 1, "learned_score"].mean()),
        "mean_negative_score": float(predictions.loc[predictions["y_critical"] == 0, "learned_score"].mean()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a minimal learned path reranker.")
    parser.add_argument("--dataset-dir", default=TrainPathRerankerConfig.dataset_dir)
    parser.add_argument("--output-dir", default=TrainPathRerankerConfig.output_dir)
    parser.add_argument("--model-type", choices=["logistic", "mlp"], default="mlp")
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_path_reranker(
        TrainPathRerankerConfig(
            dataset_dir=args.dataset_dir,
            output_dir=args.output_dir,
            model_type=args.model_type,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
        )
    )


if __name__ == "__main__":
    main()
