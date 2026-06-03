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

from gcn_physics_constraints import compute_physics_constraint_loss
from train_rts79_paper_gcn import (
    PaperGcnTrainConfig,
    PaperStyleRts79Gcn,
    _build_adjacency_powers,
    _build_branch_graph_adjacency,
    _evaluate_paper_gcn,
    _x_gcn_physics_feature_names,
)
from rts79_cascade import load_rts79_case


@dataclass(frozen=True)
class PhysicsGcnRunConfig:
    dataset_npz: str
    output_dir: str
    epochs: int = 2
    batch_size: int = 16
    learning_rate: float = 0.005
    lambda_mask: float = 0.0
    lambda_relay: float = 0.0
    lambda_monotonic: float = 0.0
    beta: float = 1.2
    security_limit: float = 1.0
    p_min_relay: float = 0.5
    monotonic_margin: float = 0.0
    random_seed: int = 20260603


def train_physics_gcn(config: PhysicsGcnRunConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = np.load(config.dataset_npz, allow_pickle=True)
    x = data["x_gcn"].astype(np.float32)
    y = data["y_reachable"].astype(np.int64)
    loss_mask = data["loss_mask"].astype(bool)
    train_config = PaperGcnTrainConfig(
        epochs=config.epochs,
        batch_size=config.batch_size,
        learning_rate=config.learning_rate,
        random_seed=config.random_seed,
    )
    torch.manual_seed(config.random_seed)
    adjacency = _build_branch_graph_adjacency(load_rts79_case())
    adjacency_powers = torch.tensor(_build_adjacency_powers(adjacency, train_config.k_gcn), dtype=torch.float32)
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=train_config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loss_function = nn.CrossEntropyLoss(weight=torch.tensor([1.0, train_config.positive_weight]), reduction="none")
    indices = np.arange(x.shape[0])
    if len(indices) > 1:
        validation_count = max(1, int(round(0.2 * len(indices))))
        validation_index = indices[-validation_count:]
        train_index = indices[:-validation_count]
    else:
        train_index = indices
        validation_index = indices
    loader = DataLoader(
        TensorDataset(
            torch.tensor(x[train_index], dtype=torch.float32),
            torch.tensor(y[train_index], dtype=torch.long),
            torch.tensor(loss_mask[train_index], dtype=torch.bool),
        ),
        batch_size=config.batch_size,
        shuffle=True,
    )
    epoch_rows = []
    loading_feature_idx = _x_gcn_physics_feature_names().index("loading_ratio") if x.shape[2] >= 9 else None
    for epoch in range(1, config.epochs + 1):
        model.train()
        sums = {"ce_loss": 0.0, "mask_invalid_loss": 0.0, "relay_priority_loss": 0.0, "loading_monotonic_loss": 0.0, "total_loss": 0.0}
        batches = 0
        for xb, yb, mb in loader:
            optimizer.zero_grad()
            logits = model(xb, adjacency_powers)
            ce_matrix = loss_function(logits.reshape(-1, 2), yb.reshape(-1)).reshape_as(yb)
            ce_loss = ce_matrix[mb].mean()
            probability = torch.softmax(logits, dim=2)[:, :, 1]
            loading_ratio = xb[:, :, loading_feature_idx] if loading_feature_idx is not None else None
            physics = compute_physics_constraint_loss(
                probability,
                mb,
                loading_ratio=loading_ratio,
                lambda_mask=config.lambda_mask,
                lambda_relay=config.lambda_relay,
                lambda_monotonic=config.lambda_monotonic,
                p_min_relay=config.p_min_relay,
                monotonic_margin=config.monotonic_margin,
            )
            total_loss = ce_loss + physics["total_physics_loss"]
            total_loss.backward()
            optimizer.step()
            batches += 1
            sums["ce_loss"] += float(ce_loss.detach())
            for key in ("mask_invalid_loss", "relay_priority_loss", "loading_monotonic_loss"):
                sums[key] += float(physics[key].detach())
            sums["total_loss"] += float(total_loss.detach())
        metrics = _evaluate_paper_gcn(model, x[validation_index], y[validation_index], loss_mask[validation_index], adjacency_powers)
        row = {"epoch": epoch, **{k: v / max(batches, 1) for k, v in sums.items()}, **{f"validation_{k}": v for k, v in metrics.items()}}
        epoch_rows.append(row)
        print(json.dumps(row, ensure_ascii=False))
    final_metrics = _evaluate_paper_gcn(model, x[validation_index], y[validation_index], loss_mask[validation_index], adjacency_powers)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "train_config": asdict(train_config),
            "physics_run_config": asdict(config),
            "feature_names": _x_gcn_physics_feature_names() if x.shape[2] >= 9 else [f"feature_{i}" for i in range(x.shape[2])],
            "adjacency_powers": adjacency_powers.numpy(),
            "class_order": ["normal", "shed"],
        },
        out / "rts79_physics_gcn_model.pt",
    )
    pd.DataFrame(epoch_rows).to_csv(out / "rts79_physics_gcn_epoch_log.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"split": "validation", **final_metrics}]).to_csv(out / "rts79_physics_gcn_metrics.csv", index=False, encoding="utf-8-sig")
    (out / "rts79_physics_gcn_train_config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    return final_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train physics-informed RTS-79 reachable GCN.")
    parser.add_argument("--dataset-npz", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--lambda-mask", type=float, default=0.0)
    parser.add_argument("--lambda-relay", type=float, default=0.0)
    parser.add_argument("--lambda-monotonic", type=float, default=0.0)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--p-min-relay", type=float, default=0.5)
    parser.add_argument("--monotonic-margin", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_physics_gcn(PhysicsGcnRunConfig(**vars(args)))


if __name__ == "__main__":
    main()
