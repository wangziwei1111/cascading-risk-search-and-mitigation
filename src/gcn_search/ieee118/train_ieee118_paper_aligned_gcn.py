from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from train_ieee118_with_original_rts79_gcn import (
    build_branch_graph_adjacency_from_endpoints,
    load_original_rts79_gcn_symbols,
)


ROOT = Path(__file__).resolve().parents[3]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train IEEE118 paper-aligned S0+S1 data with original RTS-79 GCN.")
    parser.add_argument(
        "--dataset-npz",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_paper_aligned_training" / "ieee118_paper_gcn_dataset.npz",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_paper_aligned_training",
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--positive-weight", type=float, default=20.0)
    parser.add_argument("--random-seed", type=int, default=20260708)
    parser.add_argument("--config-sweep-positive-weights", type=float, nargs="*", default=[20, 50, 100, 200, 800])
    parser.add_argument("--config-sweep-epochs", type=int, nargs="*", default=[20, 40])
    parser.add_argument("--config-sweep-batch-sizes", type=int, nargs="*", default=[32, 128, 256])
    return parser.parse_args()


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing paper-aligned IEEE118 GCN dataset: {path}. "
            "Run build_ieee118_paper_gcn_training_dataset.py first; this script will not regenerate large data."
        )


def average_precision(y_true: np.ndarray, score: np.ndarray) -> float:
    if int(y_true.sum()) == 0:
        return 0.0
    order = np.argsort(-score)
    y_sorted = y_true[order].astype(bool)
    precision_at_hit = np.cumsum(y_sorted) / (np.arange(len(y_sorted)) + 1)
    return float(precision_at_hit[y_sorted].sum() / max(int(y_sorted.sum()), 1))


def split_metrics(y: np.ndarray, score: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    active_y = y[mask].astype(int)
    active_score = score[mask].astype(float)
    pred = active_score >= 0.5
    truth = active_y.astype(bool)
    tp = int((pred & truth).sum())
    tn = int(((~pred) & (~truth)).sum())
    fp = int((pred & (~truth)).sum())
    fn = int(((~pred) & truth).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "total_accuracy": float((tp + tn) / max(len(active_y), 1)),
        "hit_rate": float(precision),
        "cover_rate": float(recall),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(2 * precision * recall / max(precision + recall, 1e-12)),
        "pr_auc": average_precision(active_y, active_score),
        "average_precision": average_precision(active_y, active_score),
        "mean_positive_score": float(active_score[truth].mean()) if truth.any() else 0.0,
        "mean_negative_score": float(active_score[~truth].mean()) if (~truth).any() else 0.0,
        "positive_negative_score_gap": float(active_score[truth].mean() - active_score[~truth].mean()) if truth.any() and (~truth).any() else 0.0,
        "positive_prediction_rate_at_0.5": float((active_score >= 0.5).mean()) if len(active_score) else 0.0,
        "positive_prediction_rate_at_0.8": float((active_score >= 0.8).mean()) if len(active_score) else 0.0,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "num_labels": int(len(active_y)),
        "num_positive_labels": int(active_y.sum()),
    }


def predict_probability(model: Any, x: np.ndarray, adjacency_powers: Any, torch: Any) -> np.ndarray:
    model.eval()
    chunks = []
    with torch.no_grad():
        for start in range(0, len(x), 128):
            logits = model(torch.tensor(x[start : start + 128], dtype=torch.float32), adjacency_powers)
            chunks.append(torch.softmax(logits, dim=2)[:, :, 1].detach().cpu().numpy())
    return np.concatenate(chunks) if chunks else np.zeros((0, x.shape[1]), dtype=np.float32)


def metrics_by_subset(y: np.ndarray, prob: np.ndarray, mask: np.ndarray, sample_type: np.ndarray, split: np.ndarray) -> dict[str, Any]:
    out: dict[str, Any] = {"overall": split_metrics(y, prob, mask)}
    for split_name in ("train", "validation", "test"):
        idx = split == split_name
        if idx.any():
            out[split_name] = split_metrics(y[idx], prob[idx], mask[idx])
    for sample_name in ("S0", "S1"):
        idx = sample_type == sample_name
        if idx.any():
            out[sample_name] = split_metrics(y[idx], prob[idx], mask[idx])
    return out


def train(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    require_file(args.dataset_npz)
    symbols = load_original_rts79_gcn_symbols()
    torch = symbols["torch"]
    nn = symbols["nn"]
    DataLoader = symbols["DataLoader"]
    TensorDataset = symbols["TensorDataset"]
    PaperGcnTrainConfig = symbols["PaperGcnTrainConfig"]
    PaperStyleRts79Gcn = symbols["PaperStyleRts79Gcn"]
    build_adjacency_powers = symbols["_build_adjacency_powers"]

    data = np.load(args.dataset_npz, allow_pickle=True)
    x = data["x_gcn"].astype(np.float32)
    y = data["y_gcn"].astype(np.int64)
    mask = data["loss_mask"].astype(bool)
    split = data["split"].astype(str)
    sample_type = data["sample_type"].astype(str)
    train_idx = np.where(split == "train")[0]
    val_idx = np.where(split == "validation")[0]
    if len(train_idx) == 0:
        train_idx = np.arange(len(x))
    if len(val_idx) == 0:
        val_idx = train_idx

    config = PaperGcnTrainConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        k_gcn=3,
        first_layer_channels=16,
        second_layer_channels=4,
        positive_weight=args.positive_weight,
        validation_fraction=0.0,
        random_seed=args.random_seed,
    )
    adjacency = build_branch_graph_adjacency_from_endpoints(data["branch_from_bus"], data["branch_to_bus"])
    adjacency_powers = torch.tensor(build_adjacency_powers(adjacency, config.k_gcn), dtype=torch.float32)
    torch.manual_seed(args.random_seed)
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=config)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor([1.0, args.positive_weight], dtype=torch.float32), reduction="none")
    loader = DataLoader(
        TensorDataset(
            torch.tensor(x[train_idx], dtype=torch.float32),
            torch.tensor(y[train_idx], dtype=torch.long),
            torch.tensor(mask[train_idx], dtype=torch.bool),
        ),
        batch_size=args.batch_size,
        shuffle=True,
    )

    log_rows = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        total_count = 0
        for xb, yb, mb in loader:
            optimizer.zero_grad()
            logits = model(xb, adjacency_powers)
            loss_matrix = loss_fn(logits.reshape(-1, 2), yb.reshape(-1)).reshape_as(yb)
            loss = loss_matrix[mb].mean()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach()) * int(mb.sum())
            total_count += int(mb.sum())
        val_prob = predict_probability(model, x[val_idx], adjacency_powers, torch)
        val_metrics = split_metrics(y[val_idx], val_prob, mask[val_idx])
        log_rows.append({"epoch": epoch, "train_loss": total_loss / max(total_count, 1), **val_metrics})

    prob = predict_probability(model, x, adjacency_powers, torch)
    metrics = {
        "status": "complete",
        "model_class": "PaperStyleRts79Gcn",
        "source_model_file": "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py",
        "num_state_samples": int(x.shape[0]),
        "input_channels": int(x.shape[2]),
        "feature_names": [str(name) for name in data["feature_names"].tolist()],
        "train_config": asdict(config),
        "classification_metrics": metrics_by_subset(y, prob, mask, sample_type, split),
        "config_sweep_grid": {
            "positive_weight": [float(value) for value in args.config_sweep_positive_weights],
            "epochs": [int(value) for value in args.config_sweep_epochs],
            "batch_size": [int(value) for value in args.config_sweep_batch_sizes],
            "note": "Grid is documented for sensitivity; main run keeps RTS-79 defaults unless explicitly changed.",
        },
    }
    pd.DataFrame(log_rows).to_csv(args.output_dir / "ieee118_paper_gcn_training_log.csv", index=False, encoding="utf-8-sig")
    compact_rows = []
    for sample_idx in val_idx[: min(len(val_idx), 25)]:
        top_lines = np.argsort(-prob[sample_idx])[:10]
        for line_idx in top_lines:
            compact_rows.append(
                {
                    "sample_index": int(sample_idx),
                    "split": str(split[sample_idx]),
                    "sample_type": str(sample_type[sample_idx]),
                    "line_label": str(data["line_labels"][line_idx]),
                    "label": int(y[sample_idx, line_idx]),
                    "loss_mask": bool(mask[sample_idx, line_idx]),
                    "gcn_score": float(prob[sample_idx, line_idx]),
                }
            )
    pd.DataFrame(compact_rows).to_csv(args.output_dir / "ieee118_paper_gcn_validation_predictions_compact.csv", index=False, encoding="utf-8-sig")
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "train_config": asdict(config),
            "feature_names": [str(name) for name in data["feature_names"].tolist()],
            "source_model_class": "PaperStyleRts79Gcn",
        },
        args.output_dir / "ieee118_paper_gcn_model.pt",
    )
    (args.output_dir / "ieee118_paper_gcn_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (args.output_dir / "ieee118_paper_gcn_readme.md").write_text(
        "# IEEE118 Paper-Aligned GCN Training\n\n"
        "This run trains the original RTS-79 `PaperStyleRts79Gcn` on S0+S1 paper-style IEEE118 states. "
        "The model checkpoint and full NPZ should remain local; compact metrics are tracked.\n",
        encoding="utf-8",
    )
    return metrics


def main() -> None:
    args = parse_args()
    print(json.dumps(train(args), indent=2))


if __name__ == "__main__":
    main()
