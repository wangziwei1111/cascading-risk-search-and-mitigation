from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from evaluate_rts79_paper_gcn_search import SearchEvalConfig, _load_gcn_model as _load_paper_model, _make_gcn_path_probability_order, _make_lodf_order
from evaluate_rts79_pio_gcn_topk import PioTopkConfig, _load_model as _load_physics_model, _make_path_order
from rts79_cascade import Rts79InitialConfig, run_initial_dcopf
from train_rts79_physics_gcn import PhysicsGcnRunConfig, train_physics_gcn


@dataclass(frozen=True)
class RankLossExperimentConfig:
    output_dir: str
    base_experiment_dir: str
    lambda_rank: float = 0.2
    rank_margin: float = 0.05
    rank_max_pairs: int = 512
    test_seed_start: int = 20260722
    test_num_seeds: int = 3
    top_k: tuple[int, ...] = (20, 50, 100)
    beta: float = 1.2
    security_limit: float = 1.0


def run_rank_loss_experiment(config: RankLossExperimentConfig) -> dict:
    out = Path(config.output_dir)
    base = Path(config.base_experiment_dir)
    out.mkdir(parents=True, exist_ok=True)
    rank_train_dir = out / "training" / "physics_rank_loss"
    dataset_npz = base / "training" / "physics_dataset" / "rts79_step2_state_dataset_physics.npz"
    normalizer = base / "training" / "physics_dataset" / "rts79_step2_state_feature_normalizer_physics.json"
    rank_model = rank_train_dir / "rts79_physics_gcn_model.pt"
    base_config = json.loads((base / "config.json").read_text(encoding="utf-8"))
    (out / "config.json").write_text(json.dumps({**asdict(config), "base_config": base_config}, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copyfile(base / "training_dataset_stats.json", out / "training_dataset_stats.json")
    if not rank_model.exists():
        train_physics_gcn(
            PhysicsGcnRunConfig(
                dataset_npz=str(dataset_npz),
                output_dir=str(rank_train_dir),
                epochs=int(base_config.get("training_epochs", 5)),
                lambda_mask=0.1,
                lambda_relay=0.1,
                lambda_monotonic=0.1,
                lambda_rank=config.lambda_rank,
                rank_margin=config.rank_margin,
                rank_max_pairs=config.rank_max_pairs,
                beta=config.beta,
                security_limit=config.security_limit,
            )
        )
    shutil.copyfile(rank_train_dir / "rts79_physics_gcn_metrics.csv", out / "rank_loss_training_metrics.csv")
    models = {
        "physics_ce_mask": (_load_physics_model(base / "training" / "physics_ce_only" / "rts79_physics_gcn_model.pt"), True),
        "physics_loss_mask": (_load_physics_model(base / "training" / "physics_informed" / "rts79_physics_gcn_model.pt"), True),
        "physics_rank_loss_mask": (_load_physics_model(rank_model), True),
    }
    norm = json.loads(normalizer.read_text(encoding="utf-8"))
    paper_model_path = Path("results/gcn_search/pio_validation_round2/paper_train_ce_only/rts79_physics_gcn_model.pt")
    paper_norm_path = Path("results/gcn_search/pio_validation_round2/paper_dataset/rts79_step2_state_feature_normalizer.json")
    paper = (*_load_paper_model(paper_model_path), json.loads(paper_norm_path.read_text(encoding="utf-8"))) if paper_model_path.exists() and paper_norm_path.exists() else None

    rows = []
    for offset in range(config.test_num_seeds):
        seed = config.test_seed_start + offset
        truth = _load_truth(base, seed)
        root_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
        orders = {}
        for method, ((model, adjacency), use_mask) in models.items():
            started = time.time()
            order = pd.DataFrame(
                _make_path_order(
                    model,
                    adjacency,
                    norm,
                    root_case,
                    PioTopkConfig(model="", normalizer="", output_dir="", seed=seed, beta=config.beta, security_limit=config.security_limit, top_k=config.top_k, use_candidate_probability_mask=use_mask),
                )
            )
            order["rank"] = np.arange(1, len(order) + 1)
            order.attrs["runtime_seconds"] = time.time() - started
            orders[method] = order[["path", "rank"]]
        if paper is not None:
            paper_model, paper_adj, paper_norm = paper
            started = time.time()
            paper_order = _make_gcn_path_probability_order(paper_model, paper_adj, paper_norm, Rts79InitialConfig(random_seed=seed), SearchEvalConfig(seed=seed, beta=config.beta, security_limit=config.security_limit, random_seed=seed))
            orders["paper_gcn_path_prob"] = _order_table(paper_order, time.time() - started)
        started = time.time()
        orders["LODF_yP"] = _order_table(_make_lodf_order(Rts79InitialConfig(random_seed=seed), SearchEvalConfig(seed=seed, beta=config.beta, security_limit=config.security_limit)), time.time() - started)
        started = time.time()
        orders["oracle"] = _order_table(truth.sort_values(["critical", "total_load_shed_mw"], ascending=[False, False])["path"].astype(str).tolist(), time.time() - started)
        total_critical = int(truth["critical"].sum())
        for method, order in orders.items():
            rows.extend(_summarize(seed, method, order, truth, total_critical, float(order.attrs.get("runtime_seconds", 0.0)), config.top_k))
    per_seed = pd.DataFrame(rows)
    aggregate_topk = _aggregate_topk(per_seed)
    comparison = _comparison(per_seed)
    per_seed.to_csv(out / "pio_topk_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    aggregate_topk.to_csv(out / "aggregate_topk_summary.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(out / "aggregate_method_comparison.csv", index=False, encoding="utf-8-sig")
    diagnostics = out / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(diagnostics / "rank_loss_vs_ce_summary.csv", index=False, encoding="utf-8-sig")
    _plot(comparison, out / "figures")
    return {"output_dir": str(out)}


def _load_truth(base: Path, seed: int) -> pd.DataFrame:
    path = base / "seeds" / f"seed_{seed}" / "pio_topk_full_truth" / "pio_gcn_topk_full_truth.csv"
    truth = pd.read_csv(path)
    if len(truth) != 1406:
        raise ValueError(f"Expected full ordered N-2 truth for seed {seed}, got {len(truth)}")
    return truth


def _order_table(paths: list[str], runtime: float) -> pd.DataFrame:
    table = pd.DataFrame({"path": paths, "rank": np.arange(1, len(paths) + 1)})
    table.attrs["runtime_seconds"] = runtime
    return table


def _summarize(seed: int, method: str, order: pd.DataFrame, truth: pd.DataFrame, total_critical: int, runtime: float, top_k_values: tuple[int, ...]) -> list[dict]:
    truth_by_path = truth.set_index("path").to_dict(orient="index")
    rows = []
    for top_k in top_k_values:
        subset = order.head(top_k)
        found = sum(bool(truth_by_path.get(path, {}).get("critical", False)) for path in subset["path"])
        rows.append(
            {
                "seed": seed,
                "method": method,
                "top_k": int(top_k),
                "total_critical_paths": total_critical,
                "critical_found": int(found),
                "critical_path_recall": float(found / max(total_critical, 1)),
                "runtime_seconds": runtime,
                "notes": _notes(method),
            }
        )
    return rows


def _notes(method: str) -> str:
    return {
        "physics_ce_mask": "CE-only physics feature model with candidate mask",
        "physics_loss_mask": "original physics-informed loss model with candidate mask",
        "physics_rank_loss_mask": "physics-informed model with reachable pairwise ranking loss and candidate mask",
        "paper_gcn_path_prob": "original paper 4-feature GCN_path_prob baseline; weak model",
        "LODF_yP": "physical-rule ranking baseline",
        "oracle": "upper bound only",
    }.get(method, "")


def _aggregate_topk(per_seed: pd.DataFrame) -> pd.DataFrame:
    return (
        per_seed.groupby(["method", "top_k"], sort=False)
        .agg(
            num_test_seeds=("seed", "nunique"),
            mean_total_critical_paths=("total_critical_paths", "mean"),
            mean_critical_found=("critical_found", "mean"),
            mean_critical_path_recall=("critical_path_recall", "mean"),
            mean_runtime_seconds=("runtime_seconds", "mean"),
            notes=("notes", "first"),
        )
        .reset_index()
    )


def _comparison(per_seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, group in per_seed.groupby("method", sort=False):
        rows.append(
            {
                "method": method,
                "mean_found_after_20": _mean(group, 20, "critical_found"),
                "mean_found_after_50": _mean(group, 50, "critical_found"),
                "mean_found_after_100": _mean(group, 100, "critical_found"),
                "mean_recall_at_20": _mean(group, 20, "critical_path_recall"),
                "mean_recall_at_50": _mean(group, 50, "critical_path_recall"),
                "mean_recall_at_100": _mean(group, 100, "critical_path_recall"),
                "mean_runtime_seconds": float(group["runtime_seconds"].mean()),
                "notes": str(group["notes"].iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def _mean(group: pd.DataFrame, top_k: int, column: str) -> float:
    return float(group.loc[group["top_k"] == top_k, column].mean())


def _plot(comparison: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    _bar(comparison["method"], comparison["mean_recall_at_100"], "Rank Loss vs CE Recall@100", "Mean recall@100", figure_dir / "rank_loss_vs_ce_recall.png")
    labels = comparison["method"].tolist()
    x = np.arange(len(labels))
    width = 0.25
    fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=160)
    for offset, col in enumerate(["mean_found_after_20", "mean_found_after_50", "mean_found_after_100"]):
        ax.bar(x + (offset - 1) * width, comparison[col], width, label=col.replace("mean_", ""))
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Mean critical paths found")
    ax.set_title("Rank Loss vs CE Found After K")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / "rank_loss_vs_ce_found_after_k.png")
    plt.close(fig)


def _bar(labels, values, title: str, ylabel: str, path: Path) -> None:
    label_list = [str(label) for label in labels]
    x = np.arange(len(label_list))
    fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=160)
    bars = ax.bar(x, values, color="#1f77b4")
    ax.set_xticks(x)
    ax.set_xticklabels(label_list, rotation=30, ha="right")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.bar_label(bars, fmt="%.3g", padding=3)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RTS-79 rank-loss preliminary comparison.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--base-experiment-dir", required=True)
    parser.add_argument("--lambda-rank", type=float, default=0.2)
    parser.add_argument("--rank-margin", type=float, default=0.05)
    parser.add_argument("--rank-max-pairs", type=int, default=512)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_rank_loss_experiment(RankLossExperimentConfig(**vars(args)))


if __name__ == "__main__":
    main()
