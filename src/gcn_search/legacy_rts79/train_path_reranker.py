from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn


FEATURE_COLUMNS = [
    "rank_in_pio",
    "rank_in_paper",
    "rank_in_lodf",
    "pio_score",
    "paper_score",
    "lodf_score",
    "ensemble_score_alpha_0_75",
    "first_line_loading_ratio",
    "second_line_loading_ratio",
    "max_loading_ratio",
    "min_security_margin",
    "min_relay_margin",
    "first_line_abs_flow",
    "second_line_abs_flow",
    "first_outage_num_overloaded_lines",
    "first_outage_max_loading_ratio",
    "first_outage_total_load_shed_mw",
    "candidate_position_min_rank",
]


@dataclass(frozen=True)
class TrainPathRerankerConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    output_dir: str = "results/gcn_search/path_reranker_models"
    model_type: str = "both"
    seed_split_mode: str = "leave_one_seed_out"
    epochs: int = 80
    learning_rate: float = 0.01
    positive_weight: float | None = None
    use_load_shed_weight: bool = False
    focal_gamma: float = 0.0
    lambda_pairwise_rank: float = 0.05
    random_seed: int = 20260801


class LogisticReranker(nn.Module):
    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.linear = nn.Linear(input_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x).squeeze(-1)


class MlpReranker(nn.Module):
    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Dropout(0.05), nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def train_path_reranker(config: TrainPathRerankerConfig) -> dict:
    torch.manual_seed(config.random_seed)
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "path_reranker_train_config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    dataset = _load_dataset(config.dataset_dir)
    model_types = ["logistic", "mlp"] if config.model_type == "both" else [config.model_type]
    all_metric_rows: list[dict] = []
    all_prediction_rows: list[pd.DataFrame] = []
    feature_importance_rows: list[dict] = []
    for model_type in model_types:
        if config.seed_split_mode == "leave_one_seed_out":
            for heldout_seed in sorted(dataset["seed"].unique()):
                train = dataset[dataset["seed"] != heldout_seed]
                val = dataset[dataset["seed"] == heldout_seed]
                model, normalizer = _fit_model(train, config, model_type)
                predictions = _predict_table(model, normalizer, val, model_type, heldout_seed)
                metrics = _metrics_for_predictions(predictions, model_type, f"heldout_seed_{heldout_seed}")
                all_metric_rows.append(metrics)
                all_prediction_rows.append(predictions)
                _save_model(out / f"path_reranker_{model_type}_heldout_{heldout_seed}.pt", model, normalizer, model_type)
                if model_type == "logistic":
                    feature_importance_rows.extend(_linear_importance(model, model_type, heldout_seed))
        else:
            train = pd.read_csv(Path(config.dataset_dir) / "path_reranker_train.csv")
            val = pd.read_csv(Path(config.dataset_dir) / "path_reranker_val.csv")
            model, normalizer = _fit_model(train, config, model_type)
            predictions = _predict_table(model, normalizer, val, model_type, int(val["seed"].iloc[0]))
            all_metric_rows.append(_metrics_for_predictions(predictions, model_type, "fixed_val"))
            all_prediction_rows.append(predictions)
            _save_model(out / f"path_reranker_{model_type}.pt", model, normalizer, model_type)
            if model_type == "logistic":
                feature_importance_rows.extend(_linear_importance(model, model_type, -1))
    metrics = pd.DataFrame(all_metric_rows)
    predictions = pd.concat(all_prediction_rows, ignore_index=True)
    metrics.to_csv(out / "path_reranker_metrics.csv", index=False, encoding="utf-8-sig")
    predictions.to_csv(out / "path_reranker_validation_predictions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(feature_importance_rows).to_csv(out / "path_reranker_feature_importance.csv", index=False, encoding="utf-8-sig")
    return {"output_dir": str(out), "metrics": str(out / "path_reranker_metrics.csv")}


def _load_dataset(dataset_dir: str | Path) -> pd.DataFrame:
    parts = [pd.read_csv(Path(dataset_dir) / name) for name in ["path_reranker_train.csv", "path_reranker_val.csv", "path_reranker_test.csv"]]
    return pd.concat(parts, ignore_index=True)


def _fit_model(train: pd.DataFrame, config: TrainPathRerankerConfig, model_type: str) -> tuple[nn.Module, dict]:
    x_raw = train[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=np.float32)
    y = train["y_critical"].to_numpy(dtype=np.float32)
    mean = x_raw.mean(axis=0)
    std = x_raw.std(axis=0)
    std[std < 1e-6] = 1.0
    x = (x_raw - mean) / std
    model: nn.Module = LogisticReranker(x.shape[1]) if model_type == "logistic" else MlpReranker(x.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    pos_weight_value = config.positive_weight or float((len(y) - y.sum()) / max(y.sum(), 1.0))
    pos_weight = torch.tensor(pos_weight_value, dtype=torch.float32)
    xt = torch.tensor(x, dtype=torch.float32)
    yt = torch.tensor(y, dtype=torch.float32)
    sample_weight = torch.ones_like(yt)
    if config.use_load_shed_weight:
        shed = torch.tensor(train["y_load_shed"].to_numpy(dtype=np.float32), dtype=torch.float32)
        sample_weight = sample_weight + torch.clamp(shed / max(float(shed.max()), 1.0), min=0.0)
    for _ in range(config.epochs):
        optimizer.zero_grad()
        logits = model(xt)
        loss = nn.functional.binary_cross_entropy_with_logits(logits, yt, pos_weight=pos_weight, reduction="none")
        if config.focal_gamma > 0:
            prob = torch.sigmoid(logits)
            pt = torch.where(yt > 0.5, prob, 1.0 - prob)
            loss = loss * torch.pow(1.0 - pt, config.focal_gamma)
        loss = (loss * sample_weight).mean()
        if config.lambda_pairwise_rank > 0:
            loss = loss + config.lambda_pairwise_rank * _pairwise_loss(logits, yt)
        loss.backward()
        optimizer.step()
    return model.eval(), {"mean": mean.tolist(), "std": std.tolist(), "features": FEATURE_COLUMNS}


def _pairwise_loss(logits: torch.Tensor, y: torch.Tensor, max_pairs: int = 2048, margin: float = 0.05) -> torch.Tensor:
    pos = logits[y > 0.5]
    neg = logits[y <= 0.5]
    if pos.numel() == 0 or neg.numel() == 0:
        return logits.sum() * 0.0
    count = min(max_pairs, int(pos.numel() * neg.numel()))
    pos_idx = torch.randint(0, pos.numel(), (count,))
    neg_idx = torch.randint(0, neg.numel(), (count,))
    return torch.relu(margin - (pos[pos_idx] - neg[neg_idx])).mean()


def _predict_table(model: nn.Module, normalizer: dict, table: pd.DataFrame, model_type: str, heldout_seed: int) -> pd.DataFrame:
    x_raw = table[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=np.float32)
    mean = np.asarray(normalizer["mean"], dtype=np.float32)
    std = np.asarray(normalizer["std"], dtype=np.float32)
    x = (x_raw - mean) / std
    with torch.no_grad():
        score = torch.sigmoid(model(torch.tensor(x, dtype=torch.float32))).numpy()
    keep = ["seed", "path", "y_critical", "y_load_shed", "rank_in_pio", "rank_in_paper", "rank_in_lodf"]
    result = table[keep].copy()
    result["model_type"] = model_type
    result["heldout_seed"] = heldout_seed
    result["learned_score"] = score
    return result


def _metrics_for_predictions(predictions: pd.DataFrame, model_type: str, split: str) -> dict:
    y = predictions["y_critical"].to_numpy(dtype=int)
    score = predictions["learned_score"].to_numpy(dtype=float)
    ordered = predictions.sort_values(["learned_score", "path"], ascending=[False, True]).reset_index(drop=True)
    total = max(int(y.sum()), 1)
    ranks = np.arange(1, len(ordered) + 1)
    critical_ranks = ranks[ordered["y_critical"].to_numpy(dtype=int) == 1]
    return {
        "model_type": model_type,
        "split": split,
        "num_samples": int(len(predictions)),
        "num_critical": int(y.sum()),
        "pr_auc": _average_precision(y, score),
        "roc_auc": _roc_auc(y, score),
        "precision_at_20": _precision_at(ordered, 20),
        "recall_at_20": _recall_at(ordered, 20, total),
        "recall_at_50": _recall_at(ordered, 50, total),
        "recall_at_100": _recall_at(ordered, 100, total),
        "recall_at_200": _recall_at(ordered, 200, total),
        "mean_critical_rank": float(np.mean(critical_ranks)) if len(critical_ranks) else np.nan,
        "median_critical_rank": float(np.median(critical_ranks)) if len(critical_ranks) else np.nan,
        "positive_score_mean": float(score[y == 1].mean()) if y.sum() else np.nan,
        "negative_score_mean": float(score[y == 0].mean()) if (y == 0).sum() else np.nan,
        "score_gap": float(score[y == 1].mean() - score[y == 0].mean()) if y.sum() and (y == 0).sum() else np.nan,
    }


def _average_precision(y: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(-score)
    y_sorted = y[order]
    positives = y_sorted.sum()
    if positives == 0:
        return 0.0
    precision = np.cumsum(y_sorted) / (np.arange(len(y_sorted)) + 1)
    return float((precision * y_sorted).sum() / positives)


def _roc_auc(y: np.ndarray, score: np.ndarray) -> float:
    pos = score[y == 1]
    neg = score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float(((pos[:, None] > neg[None, :]).mean()) + 0.5 * ((pos[:, None] == neg[None, :]).mean()))


def _precision_at(ordered: pd.DataFrame, k: int) -> float:
    subset = ordered.head(k)
    return float(subset["y_critical"].mean()) if len(subset) else 0.0


def _recall_at(ordered: pd.DataFrame, k: int, total: int) -> float:
    return float(ordered.head(k)["y_critical"].sum() / max(total, 1))


def _linear_importance(model: nn.Module, model_type: str, heldout_seed: int) -> list[dict]:
    weight = model.linear.weight.detach().cpu().numpy().reshape(-1)
    return [{"model_type": model_type, "heldout_seed": heldout_seed, "feature": name, "weight": float(value)} for name, value in zip(FEATURE_COLUMNS, weight)]


def _save_model(path: Path, model: nn.Module, normalizer: dict, model_type: str) -> None:
    torch.save({"model_type": model_type, "state_dict": model.state_dict(), "normalizer": normalizer}, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train lightweight learned path reranker.")
    parser.add_argument("--dataset-dir", default=TrainPathRerankerConfig.dataset_dir)
    parser.add_argument("--output-dir", default=TrainPathRerankerConfig.output_dir)
    parser.add_argument("--model-type", choices=["logistic", "mlp", "both"], default="both")
    parser.add_argument("--seed-split-mode", choices=["leave_one_seed_out", "fixed"], default="leave_one_seed_out")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--positive-weight", type=float)
    parser.add_argument("--use-load-shed-weight", action="store_true")
    parser.add_argument("--focal-gamma", type=float, default=0.0)
    parser.add_argument("--lambda-pairwise-rank", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_path_reranker(
        TrainPathRerankerConfig(
            dataset_dir=args.dataset_dir,
            output_dir=args.output_dir,
            model_type=args.model_type,
            seed_split_mode=args.seed_split_mode,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            positive_weight=args.positive_weight,
            use_load_shed_weight=args.use_load_shed_weight,
            focal_gamma=args.focal_gamma,
            lambda_pairwise_rank=args.lambda_pairwise_rank,
        )
    )


if __name__ == "__main__":
    main()
