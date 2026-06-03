from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .metrics import evaluate_scenario_ranking
from .model import BranchGCN, torch
from .risk_dataset import RiskDataset, load_dataset


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


def scenario_scores(node_scores: np.ndarray, outage_masks: np.ndarray) -> np.ndarray:
    masked = np.where(outage_masks > 0.0, node_scores, -np.inf)
    max_scores = np.max(masked, axis=1)
    fallback = np.max(node_scores, axis=1)
    return np.where(np.isfinite(max_scores), max_scores, fallback)


def train_branch_gcn(
    dataset_dir: Path,
    checkpoint_dir: Path,
    eval_dir: Path,
    seed: int = 7,
    epochs: int = 120,
    learning_rate: float = 0.01,
    hidden_dim: int = 32,
    outage_loss_weight: float = 6.0,
) -> dict:
    set_seed(seed)
    train = load_dataset(dataset_dir, "train")
    val = load_dataset(dataset_dir, "val")
    test = load_dataset(dataset_dir, "test")
    model = BranchGCN(train.features.shape[-1], hidden_dim=hidden_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    adj = torch.tensor(train.normalized_adjacency, dtype=torch.float32)
    x_train = torch.tensor(train.features, dtype=torch.float32)
    y_train = torch.tensor(train.targets, dtype=torch.float32)
    mask_train = torch.tensor(train.outage_masks, dtype=torch.float32)
    weights = 1.0 + outage_loss_weight * mask_train
    history = []
    best_state = None
    best_epoch = 0
    best_val_spearman = -1e9
    for epoch in range(1, epochs + 1):
        model.train()
        pred = model(x_train, adj)
        loss = torch.mean(weights * (pred - y_train) ** 2)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        with torch.no_grad():
            val_scores = predict_dataset(model, val)
        val_metrics = evaluate_scenario_ranking(val_scores, val.true_risk)
        if val_metrics["spearman"] > best_val_spearman:
            best_val_spearman = val_metrics["spearman"]
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            history.append({"epoch": epoch, "train_loss": float(loss.item()), **{f"val_{k}": v for k, v in val_metrics.items()}})
    if best_state is not None:
        model.load_state_dict(best_state)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state": model.state_dict(),
        "input_dim": int(train.features.shape[-1]),
        "hidden_dim": int(hidden_dim),
        "seed": int(seed),
        "epochs": int(epochs),
        "best_epoch": int(best_epoch),
        "best_val_spearman": float(best_val_spearman),
    }, checkpoint_dir / "branch_gcn.pt")
    metrics = {
        "train": evaluate_scenario_ranking(predict_dataset(model, train), train.true_risk),
        "val": evaluate_scenario_ranking(predict_dataset(model, val), val.true_risk),
        "test": evaluate_scenario_ranking(predict_dataset(model, test), test.true_risk),
        "baselines": baseline_metrics(train, val, test),
        "selected_epoch": int(best_epoch),
        "history": history,
    }
    eval_dir.mkdir(parents=True, exist_ok=True)
    with open(eval_dir / "branch_gcn_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    write_ranking_csv(model, test, eval_dir / "test_risk_ranking.csv")
    return metrics


def predict_dataset(model: BranchGCN, dataset: RiskDataset) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        pred = model(
            torch.tensor(dataset.features, dtype=torch.float32),
            torch.tensor(dataset.normalized_adjacency, dtype=torch.float32),
        ).cpu().numpy()
    return scenario_scores(pred, dataset.outage_masks)


def baseline_metrics(train: RiskDataset, val: RiskDataset, test: RiskDataset) -> dict:
    return {
        "outage_count": _baseline_all(lambda ds: ds.outage_masks.sum(axis=1), train, val, test),
        "branch_degree": _baseline_all(lambda ds: (ds.outage_masks * ds.adjacency.sum(axis=1)).sum(axis=1), train, val, test),
    }


def _baseline_all(fn, train: RiskDataset, val: RiskDataset, test: RiskDataset) -> dict:
    return {
        "train": evaluate_scenario_ranking(fn(train), train.true_risk),
        "val": evaluate_scenario_ranking(fn(val), val.true_risk),
        "test": evaluate_scenario_ranking(fn(test), test.true_risk),
    }


def write_ranking_csv(model: BranchGCN, dataset: RiskDataset, path: Path) -> None:
    scores = predict_dataset(model, dataset)
    order = np.argsort(scores)[::-1]
    with open(path, "w", encoding="utf-8") as f:
        f.write("rank,scenario_id,gcn_score,true_do_nothing_negative_return,best_improvement,initial_outages\n")
        for rank, idx in enumerate(order, start=1):
            outages = np.where(dataset.outage_masks[idx] > 0.0)[0]
            f.write(
                f"{rank},{int(dataset.scenario_ids[idx])},{float(scores[idx]):.8f},"
                f"{float(dataset.true_risk[idx]):.8f},{float(dataset.best_improvement[idx]):.8f},"
                f"\"{','.join(str(int(v)) for v in outages)}\"\n"
            )
