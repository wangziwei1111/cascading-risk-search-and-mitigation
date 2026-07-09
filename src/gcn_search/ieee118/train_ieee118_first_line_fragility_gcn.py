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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from train_ieee118_with_original_rts79_gcn import build_branch_graph_adjacency_from_endpoints, load_original_rts79_gcn_symbols


DEFAULT_OUTPUT = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup" / "first_line_fragility"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train IEEE118 first-line fragility with the original RTS-79 PaperStyleRts79Gcn.")
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_OUTPUT / "ieee118_first_line_fragility_dataset.npz")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--k-gcn", type=int, default=3)
    parser.add_argument("--first-layer-channels", type=int, default=16)
    parser.add_argument("--second-layer-channels", type=int, default=4)
    parser.add_argument("--positive-weight", type=float, default=20.0)
    parser.add_argument("--positive-weight-sweep", type=float, nargs="*", default=[20.0, 50.0, 100.0, 200.0])
    parser.add_argument("--seed", type=int, default=20260708)
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label}: {path}. Build the first-line fragility dataset first; this trainer will not regenerate large data."
        )


def average_precision(y_true: np.ndarray, score: np.ndarray) -> float:
    if len(y_true) == 0 or int(y_true.sum()) == 0:
        return 0.0
    order = np.argsort(-score)
    y_sorted = y_true[order].astype(bool)
    precision_at_hit = np.cumsum(y_sorted) / (np.arange(len(y_sorted)) + 1)
    return float(precision_at_hit[y_sorted].sum() / max(int(y_sorted.sum()), 1))


def roc_auc(y_true: np.ndarray, score: np.ndarray) -> float | None:
    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return None
    order = np.argsort(score)
    ranks = np.empty(len(score), dtype=float)
    ranks[order] = np.arange(1, len(score) + 1)
    pos = y_true.astype(bool)
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / max(n_pos * n_neg, 1))


def split_metrics(y: np.ndarray, score: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    active = mask.astype(bool)
    active_y = y[active].astype(int)
    active_score = score[active].astype(float)
    pred = active_score >= 0.5
    truth = active_y.astype(bool)
    tp = int((pred & truth).sum())
    tn = int(((~pred) & (~truth)).sum())
    fp = int((pred & (~truth)).sum())
    fn = int(((~pred) & truth).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "overall_accuracy": float((tp + tn) / max(len(active_y), 1)),
        "hit_rate": float(precision),
        "cover_rate": float(recall),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(2 * precision * recall / max(precision + recall, 1e-12)),
        "average_precision": average_precision(active_y, active_score),
        "roc_auc": roc_auc(active_y, active_score),
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
        "num_positive_labels": int(active_y.sum()) if len(active_y) else 0,
    }


def predict_probability(model: Any, x: np.ndarray, adjacency_powers: Any, torch: Any) -> np.ndarray:
    model.eval()
    chunks = []
    with torch.no_grad():
        for start in range(0, len(x), 128):
            logits = model(torch.tensor(x[start : start + 128], dtype=torch.float32), adjacency_powers)
            chunks.append(torch.softmax(logits, dim=2)[:, :, 1].detach().cpu().numpy())
    return np.concatenate(chunks) if chunks else np.zeros((0, x.shape[1]), dtype=np.float32)


def subset_metrics(y: np.ndarray, prob: np.ndarray, mask: np.ndarray, split: np.ndarray) -> dict[str, Any]:
    out = {"overall": split_metrics(y, prob, mask)}
    for name in ("train", "validation", "test"):
        idx = split == name
        if idx.any():
            out[name] = split_metrics(y[idx], prob[idx], mask[idx])
    return out


def train_once(args: argparse.Namespace, positive_weight: float, *, save_model: bool) -> tuple[dict[str, Any], np.ndarray, pd.DataFrame]:
    require_file(args.dataset_npz, "first-line fragility dataset NPZ")
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
    y = data["y_fragile"].astype(np.int64) if "y_fragile" in data else data["y_gcn"].astype(np.int64)
    mask = data["loss_mask"].astype(bool)
    split = data["split"].astype(str)
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
        k_gcn=args.k_gcn,
        first_layer_channels=args.first_layer_channels,
        second_layer_channels=args.second_layer_channels,
        positive_weight=float(positive_weight),
        validation_fraction=0.0,
        random_seed=args.seed,
    )
    adjacency = build_branch_graph_adjacency_from_endpoints(data["branch_from_bus"], data["branch_to_bus"])
    adjacency_powers = torch.tensor(build_adjacency_powers(adjacency, config.k_gcn), dtype=torch.float32)
    torch.manual_seed(args.seed)
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=config)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor([1.0, float(positive_weight)], dtype=torch.float32), reduction="none")
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
        log_rows.append({"epoch": epoch, "positive_weight": float(positive_weight), "train_loss": total_loss / max(total_count, 1), **val_metrics})

    prob = predict_probability(model, x, adjacency_powers, torch)
    metrics = {
        "status": "complete",
        "model_class": "PaperStyleRts79Gcn",
        "source_model_file": "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py",
        "target": "first_line_fragility",
        "positive_weight": float(positive_weight),
        "num_s0_samples": int(x.shape[0]),
        "input_channels": int(x.shape[2]),
        "feature_names": [str(name) for name in data["feature_names"].tolist()],
        "train_config": asdict(config),
        "classification_metrics": subset_metrics(y, prob, mask, split),
    }
    if save_model:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "train_config": asdict(config),
                "feature_names": [str(name) for name in data["feature_names"].tolist()],
                "source_model_class": "PaperStyleRts79Gcn",
                "target": "first_line_fragility",
            },
            args.output_dir / "ieee118_first_line_fragility_model.pt",
        )
    return metrics, prob, pd.DataFrame(log_rows)


def write_probabilities(args: argparse.Namespace, prob: np.ndarray) -> pd.DataFrame:
    data = np.load(args.dataset_npz, allow_pickle=True)
    rows = []
    for sample_idx in range(prob.shape[0]):
        for line_idx, label in enumerate(data["line_labels"].astype(str)):
            rows.append(
                {
                    "seed": int(data["seed"][sample_idx]),
                    "scenario_id": int(data["seed"][sample_idx]),
                    "line_label": str(label),
                    "line_index": int(line_idx),
                    "q_fragile": float(prob[sample_idx, line_idx]),
                    "fragility_label": int(data["y_fragile"][sample_idx, line_idx] if "y_fragile" in data else data["y_gcn"][sample_idx, line_idx]),
                    "loss_mask": bool(data["loss_mask"][sample_idx, line_idx]),
                    "first_step_direct_shed_label": int(data["first_step_direct_shed_label"][sample_idx, line_idx]),
                    "first_step_critical": bool(data["first_step_direct_shed_label"][sample_idx, line_idx]),
                    "num_valid_second_critical": np.nan,
                    "max_second_load_shed_mw": np.nan,
                    "num_valid_second_relay_cascade": np.nan,
                    "split": str(data["split"][sample_idx]),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(args.output_dir / "ieee118_first_line_fragility_probabilities.csv", index=False, encoding="utf-8-sig")
    return out


def run_training(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sweep_rows = []
    main_metrics: dict[str, Any] | None = None
    main_prob: np.ndarray | None = None
    main_log: pd.DataFrame | None = None
    for weight in args.positive_weight_sweep:
        metrics, prob, log = train_once(args, float(weight), save_model=float(weight) == float(args.positive_weight))
        val = metrics["classification_metrics"].get("validation", metrics["classification_metrics"]["overall"])
        test = metrics["classification_metrics"].get("test", metrics["classification_metrics"]["overall"])
        sweep_rows.append(
            {
                "positive_weight": float(weight),
                "validation_average_precision": val["average_precision"],
                "validation_precision": val["precision"],
                "validation_recall": val["recall"],
                "validation_f1": val["f1"],
                "test_average_precision": test["average_precision"],
                "test_precision": test["precision"],
                "test_recall": test["recall"],
                "test_f1": test["f1"],
            }
        )
        if float(weight) == float(args.positive_weight):
            main_metrics, main_prob, main_log = metrics, prob, log
    assert main_metrics is not None and main_prob is not None and main_log is not None
    main_log.to_csv(args.output_dir / "ieee118_first_line_fragility_training_log.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(sweep_rows).to_csv(args.output_dir / "ieee118_first_line_fragility_weight_sweep_summary.csv", index=False, encoding="utf-8-sig")
    probabilities = write_probabilities(args, main_prob)
    compact = probabilities.loc[probabilities["split"].isin(["validation", "test"])].copy()
    compact = compact.sort_values(["split", "q_fragile"], ascending=[True, False]).groupby("split").head(50)
    compact.to_csv(args.output_dir / "ieee118_first_line_fragility_validation_predictions_compact.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "ieee118_first_line_fragility_metrics.json").write_text(json.dumps(main_metrics, indent=2), encoding="utf-8")
    (args.output_dir / "ieee118_first_line_fragility_readme.md").write_text(
        "# IEEE118 First-Line Fragility GCN\n\n"
        "This run trains the original RTS-79 `PaperStyleRts79Gcn` on S0 graph features with first-line fragility labels. "
        "It does not modify the GCN architecture. Model checkpoints and NPZ datasets remain local-only; committed outputs are compact metrics and summaries.\n",
        encoding="utf-8",
    )
    return main_metrics


def main() -> None:
    print(json.dumps(run_training(parse_args()), indent=2))


if __name__ == "__main__":
    main()
