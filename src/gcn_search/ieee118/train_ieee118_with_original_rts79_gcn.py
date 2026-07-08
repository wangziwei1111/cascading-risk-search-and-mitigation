from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train IEEE118 with the original RTS-79 PaperStyleRts79Gcn model.")
    parser.add_argument(
        "--dataset-npz",
        type=Path,
        default=ROOT
        / "results"
        / "gcn_search"
        / "ieee118_flow_scaled_800_original_rts79_gcn_eval"
        / "ieee118_rts79_gcn_dataset.npz",
    )
    parser.add_argument(
        "--path-index-csv",
        type=Path,
        default=ROOT
        / "results"
        / "gcn_search"
        / "ieee118_flow_scaled_800_original_rts79_gcn_eval"
        / "ieee118_rts79_gcn_path_index.csv",
    )
    parser.add_argument("--target", choices=["label_critical", "label_relay_cascade"], default="label_critical")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--positive-weight", type=float, default=20.0)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--random-seed", type=int, default=20260512)
    parser.add_argument("--topk-output-rows", type=int, default=5000)
    parser.add_argument("--allow-torch-blocked", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval",
    )
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}. Run the IEEE118-to-RTS79-GCN converter first.")


def load_original_rts79_gcn_symbols() -> dict[str, Any]:
    if str(LEGACY) not in sys.path:
        sys.path.insert(0, str(LEGACY))
    try:
        torch = importlib.import_module("torch")
        nn = importlib.import_module("torch.nn")
        data_mod = importlib.import_module("torch.utils.data")
        paper = importlib.import_module("train_rts79_paper_gcn")
    except Exception as exc:  # pragma: no cover - depends on local torch installation.
        raise RuntimeError(
            "Original RTS-79 GCN reuse requires importing torch and "
            "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py. "
            f"The current environment failed during import: {exc}"
        ) from exc
    return {
        "torch": torch,
        "nn": nn,
        "DataLoader": data_mod.DataLoader,
        "TensorDataset": data_mod.TensorDataset,
        "PaperGcnTrainConfig": paper.PaperGcnTrainConfig,
        "PaperStyleRts79Gcn": paper.PaperStyleRts79Gcn,
        "_build_adjacency_powers": paper._build_adjacency_powers,
    }


def build_branch_graph_adjacency_from_endpoints(from_bus: np.ndarray, to_bus: np.ndarray) -> np.ndarray:
    line_count = len(from_bus)
    adjacency = np.zeros((line_count, line_count), dtype=np.float32)
    endpoints = [set([int(f_bus), int(t_bus)]) for f_bus, t_bus in zip(from_bus, to_bus)]
    for i in range(line_count):
        for j in range(line_count):
            if i != j and endpoints[i] & endpoints[j]:
                adjacency[i, j] = 1.0
    degree = adjacency.sum(axis=1)
    inv_sqrt_degree = np.diag(1.0 / np.sqrt(np.maximum(degree, 1e-8)))
    return inv_sqrt_degree @ adjacency @ inv_sqrt_degree


def split_indices(num_rows: int, validation_fraction: float, random_seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(random_seed)
    indices = np.arange(num_rows)
    validation_size = max(1, int(round(num_rows * validation_fraction)))
    validation = rng.choice(indices, size=validation_size, replace=False)
    validation_set = set(int(idx) for idx in validation)
    train = np.asarray([idx for idx in indices if int(idx) not in validation_set], dtype=int)
    return train, np.asarray(validation, dtype=int)


def predict_probability(model: Any, x: np.ndarray, adjacency_powers: Any, torch: Any) -> np.ndarray:
    model.eval()
    probability: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(x), 128):
            logits = model(torch.tensor(x[start : start + 128], dtype=torch.float32), adjacency_powers)
            probability.append(torch.softmax(logits, dim=2)[:, :, 1].detach().cpu().numpy())
    return np.concatenate(probability) if probability else np.zeros((0, x.shape[1]), dtype=np.float32)


def binary_metrics(y: np.ndarray, score: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    prediction = score >= 0.5
    truth = y.astype(bool)
    active = mask.astype(bool)
    tp = int((prediction & truth & active).sum())
    tn = int(((~prediction) & (~truth) & active).sum())
    fp = int((prediction & (~truth) & active).sum())
    fn = int(((~prediction) & truth & active).sum())
    total = max(int(active.sum()), 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "total_accuracy": float((tp + tn) / total),
        "hit_rate": float(precision),
        "cover_rate": float(recall),
        "f1": float(2 * precision * recall / max(precision + recall, 1e-12)),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
    }


def make_predictions_table(path_index: pd.DataFrame, probabilities: np.ndarray) -> pd.DataFrame:
    rows = []
    for _, row in path_index.iterrows():
        sample_idx = int(row["sample_index"])
        line_idx = int(row["line_index"])
        rows.append(
            {
                "path": str(row["path"]),
                "first_line": str(row["first_line"]),
                "second_line": str(row["second_line"]),
                "target_label": int(row.get("label_critical", 0)),
                "label_critical": int(row.get("label_critical", 0)),
                "label_relay_cascade": int(row.get("label_relay_cascade", 0)),
                "gcn_score": float(probabilities[sample_idx, line_idx]),
                "method": "RTS79_PIO_GCN_reused_on_IEEE118",
            }
        )
    return pd.DataFrame(rows).sort_values(["gcn_score", "path"], ascending=[False, True])


def write_blocked_output(args: argparse.Namespace, error: Exception) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics = {
        "status": "blocked_torch_import",
        "model": "PaperStyleRts79Gcn from src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py",
        "reason": str(error),
        "notes": "No fallback NumPy/logistic scorer was used. Fix torch import to train the original RTS-79 GCN.",
    }
    (args.output_dir / "original_rts79_gcn_ieee118_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )
    return metrics


def train_with_original_rts79_gcn(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    require_file(args.dataset_npz, "converted IEEE118 RTS-79 GCN NPZ")
    require_file(args.path_index_csv, "converted IEEE118 path index CSV")
    try:
        symbols = load_original_rts79_gcn_symbols()
    except RuntimeError as exc:
        if args.allow_torch_blocked:
            return write_blocked_output(args, exc)
        raise

    torch = symbols["torch"]
    nn = symbols["nn"]
    DataLoader = symbols["DataLoader"]
    TensorDataset = symbols["TensorDataset"]
    PaperGcnTrainConfig = symbols["PaperGcnTrainConfig"]
    PaperStyleRts79Gcn = symbols["PaperStyleRts79Gcn"]
    build_adjacency_powers = symbols["_build_adjacency_powers"]

    data = np.load(args.dataset_npz, allow_pickle=True)
    x = data["x_gcn"].astype(np.float32)
    y_key = "y_relay_cascade" if args.target == "label_relay_cascade" else "y_critical"
    y = data[y_key].astype(np.int64)
    loss_mask = data["loss_mask"].astype(bool)
    path_index = pd.read_csv(args.path_index_csv)
    train_idx, val_idx = split_indices(len(x), args.validation_fraction, args.random_seed)
    train_config = PaperGcnTrainConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        k_gcn=3,
        first_layer_channels=16,
        second_layer_channels=4,
        positive_weight=args.positive_weight,
        validation_fraction=args.validation_fraction,
        random_seed=args.random_seed,
    )
    adjacency = build_branch_graph_adjacency_from_endpoints(data["branch_from_bus"], data["branch_to_bus"])
    adjacency_powers = torch.tensor(build_adjacency_powers(adjacency, train_config.k_gcn), dtype=torch.float32)
    torch.manual_seed(args.random_seed)
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=train_config)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor([1.0, args.positive_weight], dtype=torch.float32), reduction="none")
    loader = DataLoader(
        TensorDataset(
            torch.tensor(x[train_idx], dtype=torch.float32),
            torch.tensor(y[train_idx], dtype=torch.long),
            torch.tensor(loss_mask[train_idx], dtype=torch.bool),
        ),
        batch_size=args.batch_size,
        shuffle=True,
    )
    epoch_rows = []
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
        val_metrics = binary_metrics(y[val_idx], val_prob, loss_mask[val_idx])
        epoch_rows.append({"epoch": epoch, "train_loss": total_loss / max(total_count, 1), **val_metrics})

    probabilities = predict_probability(model, x, adjacency_powers, torch)
    predictions = make_predictions_table(path_index, probabilities)
    predictions.to_csv(args.output_dir / "original_rts79_gcn_ieee118_predictions.csv", index=False, encoding="utf-8-sig")
    predictions.head(args.topk_output_rows).to_csv(
        args.output_dir / "original_rts79_gcn_ieee118_topk_paths.csv",
        index=False,
        encoding="utf-8-sig",
    )
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "train_config": asdict(train_config),
            "feature_names": [str(name) for name in data["feature_names"].tolist()],
            "adjacency_powers": adjacency_powers.detach().cpu().numpy(),
            "source_model_class": "PaperStyleRts79Gcn",
            "source_model_file": "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py",
        },
        args.output_dir / "original_rts79_gcn_ieee118_model.pt",
    )
    pd.DataFrame(epoch_rows).to_csv(
        args.output_dir / "original_rts79_gcn_ieee118_epoch_log.csv",
        index=False,
        encoding="utf-8-sig",
    )
    metrics = {
        "status": "complete",
        "target": args.target,
        "num_state_samples": int(x.shape[0]),
        "num_path_samples": int(len(path_index)),
        "model_class": "PaperStyleRts79Gcn",
        "source_model_file": "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py",
        "train_config": asdict(train_config),
        "validation": epoch_rows[-1] if epoch_rows else {},
        "notes": "Uses the original RTS-79 GCN model class; IEEE118 changes are limited to data formatting and branch adjacency.",
    }
    (args.output_dir / "original_rts79_gcn_ieee118_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "original_rts79_gcn_ieee118_readme.md").write_text(
        "# IEEE118 Original RTS-79 GCN Reuse\n\n"
        "This run uses `PaperStyleRts79Gcn` from `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`. "
        "The previous `GCN_smoke` scorer is only a NumPy/logistic pipeline sanity check and is not the formal GCN result.\n",
        encoding="utf-8",
    )
    return metrics


def main() -> None:
    args = parse_args()
    metrics = train_with_original_rts79_gcn(args)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
