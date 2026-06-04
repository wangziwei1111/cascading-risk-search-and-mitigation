from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from evaluate_rts79_paper_gcn_search import SearchEvalConfig, _load_gcn_model, _predict_gcn_shed_probability
from evaluate_rts79_pio_gcn_topk import PioTopkConfig, _load_model as _load_pio_model, _make_path_order
from gcn_physics_constraints import make_candidate_mask
from rts79_cascade import Rts79InitialConfig, line_label_to_index_1based, run_initial_dcopf
from rts79_cascade_from_case import run_sequential_outages_from_case
from rts79_lodf import calculate_physical_vulnerability_y_p


@dataclass(frozen=True)
class EnsembleRankingConfig:
    output_dir: str = "results/gcn_search/pio_ensemble_preliminary"
    extended_dir: str = "results/gcn_search/pio_extended_fulltruth_5seed"
    pio_model: str = "results/gcn_search/pio_extended_fulltruth_5seed/training/physics_informed/rts79_physics_gcn_model.pt"
    pio_normalizer: str = "results/gcn_search/pio_extended_fulltruth_5seed/training/physics_dataset/rts79_step2_state_feature_normalizer_physics.json"
    paper_model: str = "results/gcn_search/paper_baseline_strong/paper_train_ce_only/rts79_physics_gcn_model.pt"
    paper_normalizer: str = "results/gcn_search/paper_baseline_strong/paper_dataset/rts79_step2_state_feature_normalizer.json"
    test_seed_start: int = 20260722
    test_num_seeds: int = 5
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    alphas: tuple[float, ...] = (0.25, 0.50, 0.75)
    beta: float = 1.2
    security_limit: float = 1.0


def evaluate_ensemble_ranking(config: EnsembleRankingConfig) -> dict:
    out = Path(config.output_dir)
    (out / "diagnostics").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    pio_model, pio_adjacency = _load_pio_model(config.pio_model)
    pio_normalizer = json.loads(Path(config.pio_normalizer).read_text(encoding="utf-8"))
    paper_model, paper_adjacency = _load_gcn_model(config.paper_model)
    paper_normalizer = json.loads(Path(config.paper_normalizer).read_text(encoding="utf-8"))
    per_seed_rows: list[dict] = []
    rank_shift_rows: list[dict] = []
    for seed in range(config.test_seed_start, config.test_seed_start + config.test_num_seeds):
        truth = _load_truth(config.extended_dir, seed)
        total_critical = int(truth["critical"].sum())
        truth_by_path = truth.set_index("path")["critical"].astype(bool).to_dict()
        score_table = _make_score_table(seed, config, pio_model, pio_adjacency, pio_normalizer, paper_model, paper_adjacency, paper_normalizer)
        orders = _make_orders(score_table, config.alphas)
        orders["oracle"] = truth.sort_values(["critical", "path"], ascending=[False, True])["path"].tolist()
        for method, order in orders.items():
            for k in config.top_k:
                subset = order[:k]
                found = sum(bool(truth_by_path.get(path, False)) for path in subset)
                per_seed_rows.append(
                    {
                        "seed": seed,
                        "method": method,
                        "top_k": k,
                        "critical_found": found,
                        "critical_path_recall": found / max(total_critical, 1),
                        "notes": "score-level ensemble from regenerated PIO and paper path scores" if method.startswith("ensemble") else "baseline",
                    }
                )
        per_seed_rows.extend(_load_compact_baseline_rows(config.extended_dir, seed, config.top_k, methods=("LODF_yP",)))
        pio_rank = {path: rank for rank, path in enumerate(orders.get("PIO_GCN", []), start=1)}
        paper_rank = {path: rank for rank, path in enumerate(orders.get("paper_GCN_path_prob_strong", []), start=1)}
        for alpha in config.alphas:
            name = f"ensemble_alpha_{alpha:.2f}"
            ensemble_rank = {path: rank for rank, path in enumerate(orders[name], start=1)}
            critical_paths = [path for path, critical in truth_by_path.items() if critical]
            rank_shift_rows.append(
                {
                    "seed": seed,
                    "method": name,
                    "alpha": alpha,
                    "num_critical_paths": len(critical_paths),
                    "mean_rank_pio_critical": float(np.mean([pio_rank.get(path, np.nan) for path in critical_paths])),
                    "mean_rank_paper_critical": float(np.mean([paper_rank.get(path, np.nan) for path in critical_paths])),
                    "mean_rank_ensemble_critical": float(np.mean([ensemble_rank.get(path, np.nan) for path in critical_paths])),
                    "top100_critical_count": sum(bool(truth_by_path.get(path, False)) for path in orders[name][:100]),
                    "top200_critical_count": sum(bool(truth_by_path.get(path, False)) for path in orders[name][:200]),
                }
            )
    per_seed = pd.DataFrame(per_seed_rows)
    per_seed.to_csv(out / "ensemble_topk_summary.csv", index=False, encoding="utf-8-sig")
    comparison = _aggregate(per_seed)
    comparison.to_csv(out / "ensemble_method_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rank_shift_rows).to_csv(out / "diagnostics" / "ensemble_rank_shift_summary.csv", index=False, encoding="utf-8-sig")
    _plot_recall_bar(comparison, out / "figures" / "ensemble_recall_bar.png")
    _plot_topk_curve(comparison, out / "figures" / "ensemble_topk_curve.png")
    return {"output_dir": str(out), "summary": str(out / "ensemble_method_comparison.csv")}


def _load_truth(extended_dir: str | Path, seed: int) -> pd.DataFrame:
    path = Path(extended_dir) / "seeds" / f"seed_{seed}" / "pio_topk_full_truth" / "pio_gcn_topk_full_truth.csv"
    return pd.read_csv(path)


def _make_score_table(seed: int, config: EnsembleRankingConfig, pio_model, pio_adjacency, pio_normalizer, paper_model, paper_adjacency, paper_normalizer) -> pd.DataFrame:
    root_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
    pio_order = _make_path_order(
        pio_model,
        pio_adjacency,
        pio_normalizer,
        root_case,
        PioTopkConfig(
            model=config.pio_model,
            normalizer=config.pio_normalizer,
            output_dir="",
            seed=seed,
            beta=config.beta,
            security_limit=config.security_limit,
            top_k=config.top_k,
        ),
    )
    pio_scores = {row["path"]: float(row["score"]) for row in pio_order}
    paper_scores = _make_paper_scores(seed, config, paper_model, paper_adjacency, paper_normalizer)
    all_paths = sorted(set(pio_scores) | set(paper_scores))
    table = pd.DataFrame(
        {
            "path": all_paths,
            "pio_score": [pio_scores.get(path, 0.0) for path in all_paths],
            "paper_score": [paper_scores.get(path, 0.0) for path in all_paths],
        }
    )
    table["normalized_pio_score"] = _minmax(table["pio_score"].to_numpy())
    table["normalized_paper_score"] = _minmax(table["paper_score"].to_numpy())
    return table


def _make_paper_scores(seed: int, config: EnsembleRankingConfig, model, adjacency, normalizer) -> dict[str, float]:
    root_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
    first_probability = _predict_gcn_shed_probability(model, adjacency, normalizer, root_case, config.beta)
    first_mask = make_candidate_mask(root_case)
    scores: dict[str, float] = {}
    for first_idx in np.where(first_mask)[0]:
        first_line = f"L{first_idx + 1:02d}"
        state = run_sequential_outages_from_case(root_case, [first_line], beta=config.beta, security_limit=config.security_limit)
        second_probability = _predict_gcn_shed_probability(model, adjacency, normalizer, state["case"], config.beta)
        second_mask = make_candidate_mask(state["case"], used_lines=[first_line])
        for second_idx in np.where(second_mask)[0]:
            second_line = f"L{second_idx + 1:02d}"
            scores[f"{first_line}->{second_line}"] = float(first_probability[first_idx] * second_probability[second_idx])
    return scores


def _make_orders(score_table: pd.DataFrame, alphas: tuple[float, ...]) -> dict[str, list[str]]:
    orders = {
        "PIO_GCN": score_table.sort_values(["pio_score", "path"], ascending=[False, True])["path"].tolist(),
        "paper_GCN_path_prob_strong": score_table.sort_values(["paper_score", "path"], ascending=[False, True])["path"].tolist(),
    }
    for alpha in alphas:
        name = f"ensemble_alpha_{alpha:.2f}"
        score = alpha * score_table["normalized_pio_score"] + (1.0 - alpha) * score_table["normalized_paper_score"]
        work = score_table.assign(ensemble_score=score)
        orders[name] = work.sort_values(["ensemble_score", "path"], ascending=[False, True])["path"].tolist()
    return orders


def _make_lodf_order(seed: int, config: EnsembleRankingConfig) -> list[str]:
    root_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
    first_table = calculate_physical_vulnerability_y_p(root_case, beta=config.beta).dropna(subset=["y_P"])
    paths: list[tuple[float, str]] = []
    for _, first_row in first_table.iterrows():
        first_line = str(first_row["candidate_line"])
        state = run_sequential_outages_from_case(root_case, [first_line], beta=config.beta, security_limit=config.security_limit)
        second_table = calculate_physical_vulnerability_y_p(state["case"], beta=config.beta).dropna(subset=["y_P"])
        for _, second_row in second_table.iterrows():
            second_line = str(second_row["candidate_line"])
            if second_line == first_line:
                continue
            score = float(first_row["y_P"]) * float(second_row["y_P"])
            paths.append((-score, f"{first_line}->{second_line}"))
    paths.sort()
    return [path for _, path in paths]


def _load_compact_baseline_rows(extended_dir: str | Path, seed: int, top_k: tuple[int, ...], methods: tuple[str, ...]) -> list[dict]:
    path = Path(extended_dir) / "baseline_per_seed_summary.csv"
    table = pd.read_csv(path)
    table = table[(table["seed"].astype(int) == int(seed)) & (table["method"].isin(methods))]
    rows: list[dict] = []
    for _, item in table.iterrows():
        for k in top_k:
            rows.append(
                {
                    "seed": seed,
                    "method": str(item["method"]),
                    "top_k": int(k),
                    "critical_found": int(item[f"found_after_{k}"]),
                    "critical_path_recall": float(item[f"recall_at_{k}"]),
                    "notes": str(item.get("notes", "compact baseline from extended full-truth result")),
                }
            )
    return rows


def _minmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    lo = float(np.nanmin(values)) if len(values) else 0.0
    hi = float(np.nanmax(values)) if len(values) else 0.0
    if hi - lo < 1e-12:
        return np.zeros_like(values, dtype=float)
    return (values - lo) / (hi - lo)


def _aggregate(per_seed: pd.DataFrame) -> pd.DataFrame:
    return (
        per_seed.groupby(["method", "top_k"], sort=False)
        .agg(
            num_test_seeds=("seed", "nunique"),
            mean_found=("critical_found", "mean"),
            std_found=("critical_found", "std"),
            mean_recall=("critical_path_recall", "mean"),
            std_recall=("critical_path_recall", "std"),
            notes=("notes", "first"),
        )
        .reset_index()
    )


def _plot_recall_bar(comparison: pd.DataFrame, path: Path) -> None:
    top = comparison[comparison["top_k"] == comparison["top_k"].max()]
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=160)
    ax.bar(top["method"].astype(str), top["mean_recall"].astype(float))
    ax.set_title("Ensemble Recall at Max Top-K")
    ax.set_ylabel("Mean recall")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_topk_curve(comparison: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
    for method, group in comparison.groupby("method", sort=False):
        group = group.sort_values("top_k")
        ax.plot(group["top_k"], group["mean_recall"], marker="o", label=method)
    ax.set_xlabel("Top-K")
    ax.set_ylabel("Mean recall")
    ax.set_title("Ensemble Top-K Curve")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate score-level PIO-GCN and paper-GCN ensemble ranking.")
    parser.add_argument("--output-dir", default=EnsembleRankingConfig.output_dir)
    parser.add_argument("--extended-dir", default=EnsembleRankingConfig.extended_dir)
    parser.add_argument("--pio-model", default=EnsembleRankingConfig.pio_model)
    parser.add_argument("--pio-normalizer", default=EnsembleRankingConfig.pio_normalizer)
    parser.add_argument("--paper-model", default=EnsembleRankingConfig.paper_model)
    parser.add_argument("--paper-normalizer", default=EnsembleRankingConfig.paper_normalizer)
    parser.add_argument("--test-seed-start", type=int, default=20260722)
    parser.add_argument("--test-num-seeds", type=int, default=5)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100, 200])
    parser.add_argument("--alphas", type=float, nargs="+", default=[0.25, 0.50, 0.75])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluate_ensemble_ranking(
        EnsembleRankingConfig(
            output_dir=args.output_dir,
            extended_dir=args.extended_dir,
            pio_model=args.pio_model,
            pio_normalizer=args.pio_normalizer,
            paper_model=args.paper_model,
            paper_normalizer=args.paper_normalizer,
            test_seed_start=args.test_seed_start,
            test_num_seeds=args.test_num_seeds,
            top_k=tuple(args.top_k),
            alphas=tuple(args.alphas),
        )
    )


if __name__ == "__main__":
    main()
