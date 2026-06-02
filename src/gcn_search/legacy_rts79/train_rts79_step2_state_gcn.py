from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from rts79_cascade import load_rts79_case
from train_rts79_paper_gcn import (
    PaperGcnTrainConfig,
    PaperStyleRts79Gcn,
    _build_adjacency_powers,
    _build_branch_graph_adjacency,
)


@dataclass(frozen=True)
class Step2TrainConfig:
    """Step2-State GCN 训练配置；label 是“标签”。"""

    epochs: int = 20
    batch_size: int = 32
    learning_rate: float = 0.005
    k_gcn: int = 3
    first_layer_channels: int = 16
    second_layer_channels: int = 4
    positive_weight: float = 20.0
    validation_fraction: float = 0.2
    random_seed: int = 20260512


def train_step2_state_gcn_pair(dataset_npz: str | Path, output_dir: str | Path, config: Step2TrainConfig) -> pd.DataFrame:
    """分别训练 one_step 和 reachable 两套标签的论文式 GCN。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = np.load(dataset_npz, allow_pickle=True)
    results: list[pd.DataFrame] = []
    for label_name, label_key in [
        ("one_step", "y_one_step"),
        ("reachable", "y_reachable"),
    ]:
        print(f"[Step2训练] 开始训练标签方案: {label_name}")
        label_dir = out / label_name
        metrics = _train_one_label(
            x=data["x_gcn"].astype(np.float32),
            y=data[label_key].astype(np.int64),
            loss_mask=data["loss_mask"].astype(bool),
            active_depth=data["active_depth"].astype(np.int64),
            output_dir=label_dir,
            config=config,
            label_name=label_name,
        )
        metrics.insert(0, "label_scheme", label_name)
        results.append(metrics)
    comparison = pd.concat(results, ignore_index=True)
    comparison.to_csv(out / "rts79_step2_state_gcn_label_comparison.csv", index=False, encoding="utf-8-sig")
    (out / "rts79_step2_state_gcn_train_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("[Step2训练] 标签对比结果：")
    print(comparison.to_string(index=False))
    return comparison


def _train_one_label(
    x: np.ndarray,
    y: np.ndarray,
    loss_mask: np.ndarray,
    active_depth: np.ndarray,
    output_dir: Path,
    config: Step2TrainConfig,
    label_name: str,
) -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    train_index, validation_index = _split_indices(active_depth, config)
    x_train, y_train, mask_train = x[train_index], y[train_index], loss_mask[train_index]
    x_validation, y_validation, mask_validation = x[validation_index], y[validation_index], loss_mask[validation_index]

    paper_config = PaperGcnTrainConfig(
        epochs=config.epochs,
        batch_size=config.batch_size,
        learning_rate=config.learning_rate,
        k_gcn=config.k_gcn,
        first_layer_channels=config.first_layer_channels,
        second_layer_channels=config.second_layer_channels,
        positive_weight=config.positive_weight,
        validation_fraction=config.validation_fraction,
        random_seed=config.random_seed,
    )
    adjacency = _build_branch_graph_adjacency(load_rts79_case())
    adjacency_powers = torch.tensor(_build_adjacency_powers(adjacency, config.k_gcn), dtype=torch.float32)
    torch.manual_seed(config.random_seed)
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=paper_config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loss_function = nn.CrossEntropyLoss(
        weight=torch.tensor([1.0, config.positive_weight], dtype=torch.float32),
        reduction="none",
    )
    loader = DataLoader(
        TensorDataset(
            torch.tensor(x_train, dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.long),
            torch.tensor(mask_train, dtype=torch.bool),
        ),
        batch_size=config.batch_size,
        shuffle=True,
    )

    for epoch in range(1, config.epochs + 1):
        model.train()
        total_loss = 0.0
        total_count = 0
        for xb, yb, mb in loader:
            optimizer.zero_grad()
            logits = model(xb, adjacency_powers)
            loss_matrix = loss_function(logits.reshape(-1, 2), yb.reshape(-1)).reshape_as(yb)
            loss = loss_matrix[mb].mean()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach()) * int(mb.sum())
            total_count += int(mb.sum())
        metrics = _evaluate(model, x_validation, y_validation, mask_validation, adjacency_powers)
        print(
            "[Step2训练] "
            f"label={label_name}, "
            f"epoch={epoch}, "
            f"loss={total_loss / max(total_count, 1):.6f}, "
            f"hit_rate={metrics['hit_rate']:.4f}, "
            f"cover_rate={metrics['cover_rate']:.4f}"
        )

    train_metrics = _evaluate(model, x_train, y_train, mask_train, adjacency_powers)
    validation_metrics = _evaluate(model, x_validation, y_validation, mask_validation, adjacency_powers)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "train_config": asdict(paper_config),
            "label_scheme": label_name,
            "adjacency_powers": adjacency_powers.numpy(),
            "class_order": ["normal 不切负荷", "positive 正标签"],
        },
        output_dir / "rts79_step2_state_gcn_model.pt",
    )
    table = pd.DataFrame(
        [
            {"split": "train", **train_metrics},
            {"split": "validation", **validation_metrics},
        ]
    )
    table.to_csv(output_dir / "rts79_step2_state_gcn_metrics.csv", index=False, encoding="utf-8-sig")
    return table


def _split_indices(active_depth: np.ndarray, config: Step2TrainConfig) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(config.random_seed)
    indices = np.arange(len(active_depth))
    validation_size = max(1, int(round(len(indices) * config.validation_fraction)))
    # Keep at least one root/depth-0 state in training when possible.
    validation_index = rng.choice(indices, size=validation_size, replace=False)
    train_index = np.array([idx for idx in indices if idx not in set(validation_index)], dtype=int)
    return train_index, validation_index


def _predict_probability(model: nn.Module, x: np.ndarray, adjacency_powers: torch.Tensor) -> np.ndarray:
    model.eval()
    probability: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(x), 128):
            logits = model(torch.tensor(x[start : start + 128], dtype=torch.float32), adjacency_powers)
            probability.append(torch.softmax(logits, dim=2)[:, :, 1].numpy())
    return np.concatenate(probability) if probability else np.zeros((0, 38), dtype=np.float32)


def _evaluate(model: nn.Module, x: np.ndarray, y: np.ndarray, loss_mask: np.ndarray, adjacency_powers: torch.Tensor) -> dict:
    probability = _predict_probability(model, x, adjacency_powers)
    prediction = (probability >= 0.5).astype(int)
    truth = y.astype(int)
    active = loss_mask.astype(bool)
    tp = int(((prediction == 1) & (truth == 1) & active).sum())
    tn = int(((prediction == 0) & (truth == 0) & active).sum())
    fp = int(((prediction == 1) & (truth == 0) & active).sum())
    fn = int(((prediction == 0) & (truth == 1) & active).sum())
    total_accuracy = (tp + tn) / max(int(active.sum()), 1)
    hit_rate = tp / max(tp + fp, 1)
    cover_rate = tp / max(tp + fn, 1)
    f1 = 2 * hit_rate * cover_rate / max(hit_rate + cover_rate, 1e-12)
    return {
        "total_accuracy": float(total_accuracy),
        "hit_rate": float(hit_rate),
        "cover_rate": float(cover_rate),
        "f1": float(f1),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="训练并比较 RTS-79 Step2-State 的 one_step 与 reachable GCN 标签。")
    parser.add_argument("--dataset-npz", required=True, help="Step2-State 数据集 NPZ 文件。")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "step2_state_gcn_training"), help="输出目录。")
    parser.add_argument("--epochs", type=int, default=20, help="训练轮数。")
    parser.add_argument("--batch-size", type=int, default=32, help="批大小。")
    parser.add_argument("--learning-rate", type=float, default=0.005, help="学习率。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Step2TrainConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
    )
    train_step2_state_gcn_pair(args.dataset_npz, args.output_dir, config)


if __name__ == "__main__":
    main()
