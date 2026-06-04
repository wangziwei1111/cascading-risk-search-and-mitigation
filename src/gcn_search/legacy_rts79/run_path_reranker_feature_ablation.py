from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch import nn

from evaluate_path_reranker_strict_heldout import _fold_split, _load_dataset
from train_path_reranker import TrainPathRerankerConfig, _pairwise_loss


FEATURE_GROUPS = {
    "score_only": ["pio_score", "paper_score", "lodf_score"],
    "score_plus_rank": ["pio_score", "paper_score", "lodf_score", "rank_in_pio", "rank_in_paper", "rank_in_lodf"],
    "physical_only": [
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
    ],
    "score_plus_physical": [
        "pio_score",
        "paper_score",
        "lodf_score",
        "first_line_loading_ratio",
        "second_line_loading_ratio",
        "max_loading_ratio",
        "min_security_margin",
        "min_relay_margin",
        "first_outage_max_loading_ratio",
    ],
}
FEATURE_GROUPS["all_safe_features"] = sorted(set(sum(FEATURE_GROUPS.values(), []) + ["ensemble_score_alpha_0_75", "candidate_position_min_rank"]))


@dataclass(frozen=True)
class FeatureAblationConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    output_dir: str = "results/gcn_search/path_reranker_feature_ablation"
    seeds: tuple[int, ...] = (20260722, 20260723, 20260724, 20260725, 20260726)
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    epochs: int = 80
    learning_rate: float = 0.01
    lambda_pairwise_rank: float = 0.05


class AblationMlp(nn.Module):
    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(input_dim, 24), nn.ReLU(), nn.Linear(24, 12), nn.ReLU(), nn.Linear(12, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def run_feature_ablation(config: FeatureAblationConfig) -> dict:
    out = Path(config.output_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "feature_ablation_config.json").write_text(json.dumps({"config": config.__dict__, "feature_groups": FEATURE_GROUPS}, ensure_ascii=False, indent=2), encoding="utf-8")
    dataset = _load_dataset(config.dataset_dir)
    rows: list[dict] = []
    for group_name, features in FEATURE_GROUPS.items():
        for test_seed in config.seeds:
            train_seeds, _ = _fold_split(config.seeds, test_seed)
            train = dataset[dataset["seed"].isin(train_seeds)]
            test = dataset[dataset["seed"] == test_seed]
            score = _fit_predict(train, test, features, config)
            ordered = test.assign(score=score).sort_values(["score", "path"], ascending=[False, True])
            total = int(test["y_critical"].sum())
            for k in config.top_k:
                found = int(ordered.head(k)["y_critical"].sum())
                rows.append({"feature_group": group_name, "seed": test_seed, "top_k": k, "critical_found": found, "critical_path_recall": found / max(total, 1), "num_features": len(features)})
    per_seed = pd.DataFrame(rows)
    summary = (
        per_seed.groupby(["feature_group", "top_k"], sort=False)
        .agg(mean_found=("critical_found", "mean"), mean_recall=("critical_path_recall", "mean"), std_recall=("critical_path_recall", "std"), num_features=("num_features", "first"))
        .reset_index()
    )
    per_seed.to_csv(out / "feature_ablation_method_comparison.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(out / "feature_ablation_summary.csv", index=False, encoding="utf-8-sig")
    _plot(summary, out / "figures" / "feature_ablation_recall_bar.png")
    return {"output_dir": str(out)}


def _fit_predict(train: pd.DataFrame, test: pd.DataFrame, features: list[str], config: FeatureAblationConfig) -> np.ndarray:
    x_train_raw = train[features].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=np.float32)
    x_test_raw = test[features].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=np.float32)
    mean = x_train_raw.mean(axis=0)
    std = x_train_raw.std(axis=0)
    std[std < 1e-6] = 1.0
    x_train = torch.tensor((x_train_raw - mean) / std, dtype=torch.float32)
    x_test = torch.tensor((x_test_raw - mean) / std, dtype=torch.float32)
    y = torch.tensor(train["y_critical"].to_numpy(dtype=np.float32), dtype=torch.float32)
    model = AblationMlp(x_train.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    pos_weight = torch.tensor(float((len(y) - y.sum()) / max(float(y.sum()), 1.0)), dtype=torch.float32)
    for _ in range(config.epochs):
        optimizer.zero_grad()
        logits = model(x_train)
        loss = nn.functional.binary_cross_entropy_with_logits(logits, y, pos_weight=pos_weight)
        if config.lambda_pairwise_rank > 0:
            loss = loss + config.lambda_pairwise_rank * _pairwise_loss(logits, y)
        loss.backward()
        optimizer.step()
    with torch.no_grad():
        return torch.sigmoid(model(x_test)).numpy()


def _plot(summary: pd.DataFrame, path: Path) -> None:
    top = summary[summary["top_k"] == summary["top_k"].max()]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
    ax.bar(top["feature_group"], top["mean_recall"])
    ax.set_ylabel("Mean recall")
    ax.set_title("Feature Ablation Recall at Max Top-K")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run path reranker feature ablation.")
    parser.add_argument("--dataset-dir", default=FeatureAblationConfig.dataset_dir)
    parser.add_argument("--output-dir", default=FeatureAblationConfig.output_dir)
    parser.add_argument("--epochs", type=int, default=80)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_feature_ablation(FeatureAblationConfig(dataset_dir=args.dataset_dir, output_dir=args.output_dir, epochs=args.epochs))


if __name__ == "__main__":
    main()
