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

from train_ieee118_first_line_fragility_gcn import average_precision, roc_auc, split_metrics
from train_ieee118_with_original_rts79_gcn import build_branch_graph_adjacency_from_endpoints, load_original_rts79_gcn_symbols


DEFAULT_OUTPUT = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup" / "strict_fragility_targets"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train strict IEEE118 first-line fragility targets with PaperStyleRts79Gcn.")
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_OUTPUT / "ieee118_strict_fragility_targets_dataset.npz")
    parser.add_argument("--target-summary-csv", type=Path, default=DEFAULT_OUTPUT / "ieee118_strict_fragility_target_summary.csv")
    parser.add_argument("--line-stats-csv", type=Path, default=DEFAULT_OUTPUT / "ieee118_strict_fragility_line_stats_compact.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--k-gcn", type=int, default=3)
    parser.add_argument("--first-layer-channels", type=int, default=16)
    parser.add_argument("--second-layer-channels", type=int, default=4)
    parser.add_argument("--baseline-positive-weight", type=float, default=20.0)
    parser.add_argument("--weight-sweep", type=str, nargs="*", default=["20", "auto", "50", "100", "200"])
    parser.add_argument("--seed", type=int, default=20260708)
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}. Build strict fragility targets first; this trainer will not regenerate large data.")


def predict_probability(model: Any, x: np.ndarray, adjacency_powers: Any, torch: Any) -> np.ndarray:
    model.eval()
    out = []
    with torch.no_grad():
        for start in range(0, len(x), 128):
            logits = model(torch.tensor(x[start : start + 128], dtype=torch.float32), adjacency_powers)
            out.append(torch.softmax(logits, dim=2)[:, :, 1].detach().cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, x.shape[1]), dtype=np.float32)


def metrics_by_split(y: np.ndarray, prob: np.ndarray, mask: np.ndarray, split: np.ndarray) -> list[dict[str, Any]]:
    rows = []
    for name in ["overall", "train", "validation", "test"]:
        idx = np.ones(len(split), dtype=bool) if name == "overall" else split == name
        if not idx.any():
            continue
        metrics = split_metrics(y[idx], prob[idx], mask[idx])
        metrics["split"] = name
        rows.append(metrics)
    return rows


def resolve_weight(token: str, positive: int, negative: int) -> float:
    if str(token).lower() == "auto":
        return float(negative / max(positive, 1))
    return float(token)


def train_target(args: argparse.Namespace, data: Any, target_index: int, positive_weight: float, save_model: bool) -> tuple[np.ndarray, pd.DataFrame, list[dict[str, Any]]]:
    symbols = load_original_rts79_gcn_symbols()
    torch = symbols["torch"]
    nn = symbols["nn"]
    DataLoader = symbols["DataLoader"]
    TensorDataset = symbols["TensorDataset"]
    PaperGcnTrainConfig = symbols["PaperGcnTrainConfig"]
    PaperStyleRts79Gcn = symbols["PaperStyleRts79Gcn"]
    build_adjacency_powers = symbols["_build_adjacency_powers"]

    x = data["x_gcn"].astype(np.float32)
    y = data["y_targets"][target_index].astype(np.int64)
    mask = data["loss_masks"][target_index].astype(bool)
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
    torch.manual_seed(args.seed + int(target_index))
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=config)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor([1.0, float(positive_weight)], dtype=torch.float32), reduction="none")
    loader = DataLoader(
        TensorDataset(torch.tensor(x[train_idx], dtype=torch.float32), torch.tensor(y[train_idx], dtype=torch.long), torch.tensor(mask[train_idx], dtype=torch.bool)),
        batch_size=args.batch_size,
        shuffle=True,
    )
    logs = []
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
        logs.append({"epoch": epoch, "train_loss": total_loss / max(total_count, 1), **val_metrics})
    prob = predict_probability(model, x, adjacency_powers, torch)
    if save_model:
        torch.save(
            {"model_state_dict": model.state_dict(), "train_config": asdict(config), "target_name": str(data["target_names"][target_index]), "source_model_class": "PaperStyleRts79Gcn"},
            args.output_dir / f"ieee118_strict_fragility_{str(data['target_names'][target_index])}_model.pt",
        )
    return prob, pd.DataFrame(logs), metrics_by_split(y, prob, mask, split)


def run_training(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    require_file(args.dataset_npz, "strict fragility dataset NPZ")
    require_file(args.target_summary_csv, "strict fragility target summary CSV")
    data = np.load(args.dataset_npz, allow_pickle=True)
    target_summary = pd.read_csv(args.target_summary_csv)
    trainable = target_summary.loc[~target_summary["degenerate"].astype(bool)].copy()
    metric_rows = []
    log_rows = []
    sweep_rows = []
    prob_rows = []
    compact_rows = []
    target_names = data["target_names"].astype(str).tolist()
    target_to_idx = {name: idx for idx, name in enumerate(target_names)}
    for _, target in trainable.iterrows():
        name = str(target["target_name"])
        target_idx = target_to_idx[name]
        positive = int(target["num_positive"])
        negative = int(target["num_negative"])
        for token in args.weight_sweep:
            weight = resolve_weight(token, positive, negative)
            save = token == str(args.baseline_positive_weight) or (float(weight) == float(args.baseline_positive_weight) and str(token) == "20")
            prob, logs, metrics = train_target(args, data, target_idx, weight, save_model=save)
            logs.insert(0, "positive_weight", weight)
            logs.insert(0, "target_name", name)
            log_rows.append(logs)
            for row in metrics:
                metric_rows.append({"target_name": name, "target_mode": target["target_mode"], "top_quantile": float(target["top_quantile"]), "positive_weight": weight, **row})
            val = [row for row in metrics if row["split"] == "validation"] or [metrics[0]]
            sweep_rows.append({"target_name": name, "positive_weight": weight, "validation_average_precision": val[0]["average_precision"], "validation_f1": val[0]["f1"], "validation_precision": val[0]["precision"], "validation_recall": val[0]["recall"]})
            if abs(weight - float(args.baseline_positive_weight)) < 1e-12:
                for sample_idx in range(prob.shape[0]):
                    for line_idx, line in enumerate(data["line_labels"].astype(str)):
                        row = {
                            "seed": int(data["seed"][sample_idx]),
                            "scenario_id": int(data["seed"][sample_idx]),
                            "target_mode": str(target["target_mode"]),
                            "target_name": name,
                            "top_quantile": float(target["top_quantile"]),
                            "line_label": str(line),
                            "line_index": int(line_idx),
                            "q_strict_fragile": float(prob[sample_idx, line_idx]),
                            "strict_fragility_label": int(data["y_targets"][target_idx, sample_idx, line_idx]),
                            "loss_mask": bool(data["loss_masks"][target_idx, sample_idx, line_idx]),
                            "first_step_direct_shed_label": int(data["first_step_direct_shed_label"][sample_idx, line_idx]),
                            "first_step_critical": bool(data["first_step_direct_shed_label"][sample_idx, line_idx]),
                            "split": str(data["split"][sample_idx]),
                        }
                        prob_rows.append(row)
                compact = pd.DataFrame(prob_rows).loc[lambda df: df["target_name"].eq(name) & df["split"].isin(["validation", "test"])].sort_values("q_strict_fragile", ascending=False).head(80)
                compact_rows.append(compact)
    pd.concat(log_rows, ignore_index=True).to_csv(args.output_dir / "ieee118_strict_fragility_training_log.csv", index=False, encoding="utf-8-sig")
    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(args.output_dir / "ieee118_strict_fragility_metrics_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(sweep_rows).to_csv(args.output_dir / "ieee118_strict_fragility_weight_sweep_summary.csv", index=False, encoding="utf-8-sig")
    probabilities = pd.DataFrame(prob_rows)
    if args.line_stats_csv.exists() and not probabilities.empty:
        stats = pd.read_csv(args.line_stats_csv)
        probabilities = probabilities.merge(stats, on=["seed", "line_label", "line_index", "first_step_critical", "first_step_direct_shed_label"], how="left", suffixes=("", "_stat"))
    probabilities.to_csv(args.output_dir / "ieee118_strict_fragility_probabilities_compact.csv", index=False, encoding="utf-8-sig")
    if compact_rows:
        pd.concat(compact_rows, ignore_index=True).to_csv(args.output_dir / "ieee118_strict_fragility_validation_predictions_compact.csv", index=False, encoding="utf-8-sig")
    metrics = {
        "status": "complete",
        "model_class": "PaperStyleRts79Gcn",
        "source_model_file": "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py",
        "num_trainable_targets": int(len(trainable)),
        "skipped_degenerate_targets": target_summary.loc[target_summary["degenerate"].astype(bool), "target_name"].astype(str).tolist(),
        "metrics": metric_rows,
    }
    (args.output_dir / "ieee118_strict_fragility_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (args.output_dir / "ieee118_strict_fragility_readme.md").write_text(
        "# IEEE118 Strict Fragility GCN\n\n"
        "Each non-degenerate strict target is trained with the original RTS-79 `PaperStyleRts79Gcn`. "
        "The baseline positive weight is 20; auto weight is `num_negative / num_positive`. Checkpoints stay local-only.\n",
        encoding="utf-8",
    )
    return metrics


def main() -> None:
    print(json.dumps(run_training(parse_args()), indent=2))


if __name__ == "__main__":
    main()
