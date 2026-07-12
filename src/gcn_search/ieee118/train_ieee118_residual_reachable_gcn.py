from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(IEEE118_DIR))

from train_ieee118_paper_aligned_gcn import metrics_by_subset, predict_probability, split_metrics
from train_ieee118_with_original_rts79_gcn import (
    build_branch_graph_adjacency_from_endpoints,
    load_original_rts79_gcn_symbols,
)


DEFAULT_DATASET = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_reachable_gcn"
    / "pilot_2000_dataset"
    / "ieee118_residual_reachable_gcn_dataset.npz"
)
DEFAULT_OUTPUT = ROOT / "results" / "gcn_search" / "ieee118_n1_residual_reachable_gcn" / "training"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train residual reachable labels with the original RTS-79 PaperStyleRts79Gcn.")
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--positive-weight", type=float, default=20.0)
    parser.add_argument("--k-gcn", type=int, default=3)
    parser.add_argument("--first-layer-channels", type=int, default=16)
    parser.add_argument("--second-layer-channels", type=int, default=4)
    parser.add_argument("--random-seed", type=int, default=20260712)
    parser.add_argument("--prediction-batch-size", type=int, default=128)
    return parser.parse_args(argv)


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing residual reachable dataset NPZ: {path}. "
            "Run build_ieee118_residual_reachable_dataset.py first; training will not rerun OPA."
        )


def validate_dataset(data: Any) -> None:
    required = {
        "x_gcn",
        "y_gcn",
        "loss_mask",
        "split",
        "sample_type",
        "line_labels",
        "branch_from_bus",
        "branch_to_bus",
        "feature_names",
    }
    missing = sorted(required - set(data.files))
    if missing:
        raise ValueError(f"Residual dataset NPZ missing required arrays: {missing}")
    if data["x_gcn"].shape[:2] != data["y_gcn"].shape:
        raise ValueError("x_gcn and y_gcn state/line dimensions do not match.")
    if data["loss_mask"].shape != data["y_gcn"].shape:
        raise ValueError("loss_mask and y_gcn dimensions do not match.")
    if not data["loss_mask"].astype(bool).any():
        raise ValueError("Residual dataset contains no active labels.")


def compact_prediction_rows(
    probability: np.ndarray,
    y: np.ndarray,
    mask: np.ndarray,
    split: np.ndarray,
    sample_type: np.ndarray,
    line_labels: np.ndarray,
    max_states: int = 25,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    validation_indices = np.where(split == "validation")[0]
    for sample_idx in validation_indices[:max_states]:
        candidates = np.where(mask[sample_idx])[0]
        order = candidates[np.argsort(-probability[sample_idx, candidates])][:10]
        for line_idx in order:
            rows.append(
                {
                    "sample_index": int(sample_idx),
                    "split": str(split[sample_idx]),
                    "sample_type": str(sample_type[sample_idx]),
                    "line_label": str(line_labels[line_idx]),
                    "label": int(y[sample_idx, line_idx]),
                    "residual_reachable_probability": float(probability[sample_idx, line_idx]),
                }
            )
    return pd.DataFrame(rows)


def train(args: argparse.Namespace) -> dict[str, Any]:
    require_file(args.dataset_npz)
    if args.k_gcn < 0:
        raise ValueError("--k-gcn must be non-negative.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = np.load(args.dataset_npz, allow_pickle=True)
    validate_dataset(data)
    symbols = load_original_rts79_gcn_symbols()
    torch = symbols["torch"]
    nn = symbols["nn"]
    DataLoader = symbols["DataLoader"]
    TensorDataset = symbols["TensorDataset"]
    PaperGcnTrainConfig = symbols["PaperGcnTrainConfig"]
    PaperStyleRts79Gcn = symbols["PaperStyleRts79Gcn"]
    build_adjacency_powers = symbols["_build_adjacency_powers"]

    x = data["x_gcn"].astype(np.float32)
    y = data["y_gcn"].astype(np.int64)
    mask = data["loss_mask"].astype(bool)
    split = data["split"].astype(str)
    sample_type = data["sample_type"].astype(str)
    line_labels = data["line_labels"].astype(str)
    train_idx = np.where(split == "train")[0]
    val_idx = np.where(split == "validation")[0]
    test_idx = np.where(split == "test")[0]
    if len(train_idx) == 0 or len(val_idx) == 0:
        raise ValueError("Residual training requires non-empty train and validation seed splits.")

    config = PaperGcnTrainConfig(
        epochs=int(args.epochs),
        batch_size=int(args.batch_size),
        learning_rate=float(args.learning_rate),
        k_gcn=int(args.k_gcn),
        first_layer_channels=int(args.first_layer_channels),
        second_layer_channels=int(args.second_layer_channels),
        positive_weight=float(args.positive_weight),
        validation_fraction=0.0,
        random_seed=int(args.random_seed),
    )
    adjacency = build_branch_graph_adjacency_from_endpoints(data["branch_from_bus"], data["branch_to_bus"])
    adjacency_powers = torch.tensor(build_adjacency_powers(adjacency, config.k_gcn), dtype=torch.float32)
    torch.manual_seed(config.random_seed)
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loss_fn = nn.CrossEntropyLoss(
        weight=torch.tensor([1.0, config.positive_weight], dtype=torch.float32),
        reduction="none",
    )
    generator = torch.Generator().manual_seed(config.random_seed)
    loader = DataLoader(
        TensorDataset(
            torch.tensor(x[train_idx], dtype=torch.float32),
            torch.tensor(y[train_idx], dtype=torch.long),
            torch.tensor(mask[train_idx], dtype=torch.bool),
        ),
        batch_size=config.batch_size,
        shuffle=True,
        generator=generator,
    )

    log_rows: list[dict[str, Any]] = []
    best_epoch = 0
    best_validation_ap = float("-inf")
    best_model_state: dict[str, Any] | None = None
    for epoch in range(1, config.epochs + 1):
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
            count = int(mb.sum())
            total_loss += float(loss.detach()) * count
            total_count += count
        val_probability = predict_probability(model, x[val_idx], adjacency_powers, torch)
        val_metrics = split_metrics(y[val_idx], val_probability, mask[val_idx])
        row = {"epoch": epoch, "train_loss": total_loss / max(total_count, 1), **val_metrics}
        log_rows.append(row)
        validation_ap = float(row["average_precision"])
        if np.isfinite(validation_ap) and validation_ap > best_validation_ap:
            best_epoch = epoch
            best_validation_ap = validation_ap
            best_model_state = {
                name: value.detach().cpu().clone()
                for name, value in model.state_dict().items()
            }
        print(
            "[residual-reachable-gcn] "
            f"k={config.k_gcn} epoch={epoch}/{config.epochs} loss={row['train_loss']:.6f} "
            f"val_ap={row['average_precision']:.6f} val_f1={row['f1']:.6f}",
            flush=True,
        )

    if best_model_state is None:
        raise RuntimeError("No finite validation average precision was observed during training.")
    model.load_state_dict(best_model_state)
    probability = predict_probability(model, x, adjacency_powers, torch)
    metrics = {
        "status": "complete",
        "method_name": f"RTS79_residual_reachable_GCN_k{config.k_gcn}_reused_on_IEEE118",
        "model_class": "PaperStyleRts79Gcn",
        "source_model_file": "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py",
        "model_core_modified": False,
        "target_scheme": "N1-masked multi-depth residual reachable: S0 reachable, S1 critical",
        "dataset_npz": str(args.dataset_npz),
        "num_state_samples": int(len(x)),
        "num_train_state_samples": int(len(train_idx)),
        "num_validation_state_samples": int(len(val_idx)),
        "num_test_state_samples": int(len(test_idx)),
        "num_line_labels": int(x.shape[1]),
        "input_channels": int(x.shape[2]),
        "feature_names": [str(value) for value in data["feature_names"].tolist()],
        "train_config": asdict(config),
        "checkpoint_selection_metric": "validation_average_precision",
        "best_epoch": int(best_epoch),
        "best_validation_average_precision": float(best_validation_ap),
        "effective_two_layer_max_hops": int(2 * config.k_gcn),
        "classification_metrics": metrics_by_subset(y, probability, mask, sample_type, split),
    }
    stem = f"ieee118_residual_reachable_gcn_k{config.k_gcn}"
    pd.DataFrame(log_rows).to_csv(args.output_dir / f"{stem}_training_log.csv", index=False, encoding="utf-8-sig")
    compact_prediction_rows(probability, y, mask, split, sample_type, line_labels).to_csv(
        args.output_dir / f"{stem}_validation_predictions_compact.csv",
        index=False,
        encoding="utf-8-sig",
    )
    checkpoint_path = args.output_dir / f"{stem}_model.pt"
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "train_config": asdict(config),
            "feature_names": metrics["feature_names"],
            "source_model_class": "PaperStyleRts79Gcn",
            "target_scheme": metrics["target_scheme"],
            "checkpoint_selection_metric": metrics["checkpoint_selection_metric"],
            "best_epoch": metrics["best_epoch"],
            "best_validation_average_precision": metrics["best_validation_average_precision"],
        },
        checkpoint_path,
    )
    metrics["model_checkpoint"] = str(checkpoint_path)
    (args.output_dir / f"{stem}_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (args.output_dir / f"{stem}_readme.md").write_text(
        "# IEEE118 Residual Reachable GCN\n\n"
        "This run calls the original RTS-79 `PaperStyleRts79Gcn`. The model structure is unchanged; "
        "only the N-1-masked multi-depth labels and configurable graph radius differ.\n\n"
        f"- k_gcn: {config.k_gcn}\n"
        f"- effective two-layer maximum hops: {2 * config.k_gcn}\n"
        f"- selected epoch: {metrics['best_epoch']} of {config.epochs}\n"
        f"- validation AP: {metrics['best_validation_average_precision']:.6f}\n",
        encoding="utf-8",
    )
    return metrics


def main() -> None:
    args = parse_args()
    print(json.dumps(train(args), indent=2))


if __name__ == "__main__":
    main()
