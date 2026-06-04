from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from evaluate_rts79_paper_gcn_search import SearchEvalConfig, _load_gcn_model, _make_gcn_path_probability_order
from rts79_cascade import Rts79InitialConfig


@dataclass(frozen=True)
class TopkDepthTradeoffConfig:
    output_dir: str = "results/gcn_search/pio_topk_depth_tradeoff"
    extended_dir: str = "results/gcn_search/pio_extended_fulltruth_5seed"
    paper_v2_model: str | None = "results/gcn_search/paper_baseline_strong_v2/paper_train_ce_only/rts79_physics_gcn_model.pt"
    paper_v2_normalizer: str | None = "results/gcn_search/paper_baseline_strong_v2/paper_dataset/rts79_step2_state_feature_normalizer.json"
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    beta: float = 1.2
    security_limit: float = 1.0


def analyze_topk_depth_tradeoff(config: TopkDepthTradeoffConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    extended = Path(config.extended_dir)
    comparison = pd.read_csv(extended / "aggregate_method_comparison.csv")
    pio = pd.read_csv(extended / "pio_topk_per_seed_summary.csv")
    baseline = pd.read_csv(extended / "baseline_per_seed_summary.csv")

    v2_rows = _evaluate_paper_v2(config, extended)
    if v2_rows:
        v2 = pd.DataFrame(v2_rows)
        baseline = pd.concat([baseline, v2], ignore_index=True)

    long_rows = _make_long_summary(comparison, pio, baseline, config.top_k)
    long = pd.DataFrame(long_rows)
    long.to_csv(out / "topk_depth_tradeoff_summary.csv", index=False, encoding="utf-8-sig")
    _make_pio_vs_paper(long).to_csv(out / "pio_vs_paper_rank_depth_summary.csv", index=False, encoding="utf-8-sig")
    _make_recall_gain(long).to_csv(out / "recall_gain_by_k.csv", index=False, encoding="utf-8-sig")
    _write_recommendations(out, long)
    _plot_tradeoff(long, figures / "topk_depth_tradeoff.png")
    _plot_pio_vs_paper(long, figures / "pio_vs_paper_topk_curve.png")
    return {"output_dir": str(out)}


def _evaluate_paper_v2(config: TopkDepthTradeoffConfig, extended: Path) -> list[dict]:
    if not config.paper_v2_model or not config.paper_v2_normalizer:
        return []
    model_path = Path(config.paper_v2_model)
    normalizer_path = Path(config.paper_v2_normalizer)
    if not model_path.exists() or not normalizer_path.exists():
        return []
    model, adjacency = _load_gcn_model(model_path)
    normalizer = json.loads(normalizer_path.read_text(encoding="utf-8"))
    rows = []
    truth_summary = pd.read_csv(extended / "per_seed_fulltruth_summary.csv") if (extended / "per_seed_fulltruth_summary.csv").exists() else pd.read_csv(extended / "per_seed_full_truth_summary.csv")
    for seed in truth_summary["seed"].astype(int):
        truth_path = extended / "seeds" / f"seed_{seed}" / "pio_topk_full_truth" / "pio_gcn_topk_full_truth.csv"
        truth = pd.read_csv(truth_path)
        truth_by_path = truth.set_index("path").to_dict(orient="index")
        total = int(truth["critical"].sum())
        order = _make_gcn_path_probability_order(
            model,
            adjacency,
            normalizer,
            Rts79InitialConfig(random_seed=seed),
            SearchEvalConfig(seed=seed, beta=config.beta, security_limit=config.security_limit, random_seed=seed),
        )
        for k in config.top_k:
            subset = order[:k]
            found = sum(bool(truth_by_path.get(path, {}).get("critical", False)) for path in subset)
            rows.append(
                {
                    "seed": seed,
                    "method": "paper_GCN_path_prob_strong_v2",
                    "top_k": k,
                    "critical_found": found,
                    "critical_path_recall": found / max(total, 1),
                    "runtime_seconds": 0.0,
                    "notes": "paper-feature GCN_path_prob v2; partial 7-scenario training",
                }
            )
    return rows


def _make_long_summary(comparison: pd.DataFrame, pio: pd.DataFrame, baseline: pd.DataFrame, top_k_values: tuple[int, ...]) -> list[dict]:
    rows = []
    for _, row in comparison.iterrows():
        method = str(row["method"])
        for k in top_k_values:
            recall_col = f"mean_recall_at_{k}"
            found_col = f"mean_found_after_{k}"
            if recall_col in row and pd.notna(row[recall_col]) and row[recall_col] != "":
                rows.append({"method": method, "top_k": k, "mean_recall": float(row[recall_col]), "mean_found": float(row[found_col])})
    if not baseline.empty:
        for (method, top_k), group in baseline.groupby(["method", "top_k"], sort=False):
            rows.append({"method": method, "top_k": int(top_k), "mean_recall": float(group["critical_path_recall"].mean()), "mean_found": float(group["critical_found"].mean())})
    return rows


def _make_pio_vs_paper(long: pd.DataFrame) -> pd.DataFrame:
    keep = long[long["method"].isin(["PIO_GCN_Top20", "PIO_GCN_Top50", "PIO_GCN_Top100", "PIO_GCN_Top200", "paper_GCN_path_prob_strong", "paper_GCN_path_prob_strong_v2"])]
    return keep.sort_values(["top_k", "method"]).reset_index(drop=True)


def _make_recall_gain(long: pd.DataFrame) -> pd.DataFrame:
    pivot = long.pivot_table(index="top_k", columns="method", values="mean_recall", aggfunc="mean")
    rows = []
    for k, row in pivot.iterrows():
        pio_method = f"PIO_GCN_Top{int(k)}"
        pio = row.get(pio_method, np.nan)
        for method in ["paper_GCN_path_prob_strong", "paper_GCN_path_prob_strong_v2", "LODF_yP"]:
            if method in row and pd.notna(pio):
                rows.append({"top_k": int(k), "baseline": method, "pio_minus_baseline_recall": float(pio - row[method])})
    return pd.DataFrame(rows)


def _write_recommendations(out: Path, long: pd.DataFrame) -> None:
    text = """# Top-K Depth Tradeoff Recommendations

PIO-GCN PathRank is strongest in small Top-K screening because its physics-enhanced features concentrate many critical paths near the front of the ranking.

The stronger paper-feature baseline can overtake at Top-200 because it appears to spread useful critical paths deeper into the ranked list. This does not invalidate PIO-GCN for rapid screening, but it means Top-200 evaluation should not be summarized as a simple PIO-GCN win.

Current interpretation:

- PIO-GCN PathRank is better suited for small Top-K rapid screening.
- Strong paper-feature GCN_path_prob remains competitive for deeper Top-K budgets.
- Future work should consider ensemble ranking between physics-enhanced PIO scores and paper-feature GCN scores.
- Optimization should focus on Top-100 if the target is rapid critical-path discovery.
- If Top-200 or deeper search is the target, ensemble ranking or path-level loss should be tested.
"""
    (out / "recommendations.md").write_text(text, encoding="utf-8")


def _plot_tradeoff(long: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=160)
    for method, group in long.groupby("method", sort=False):
        if method in {"random", "line_order"}:
            continue
        group = group.sort_values("top_k")
        ax.plot(group["top_k"], group["mean_recall"], marker="o", label=method)
    ax.set_xlabel("Top-K")
    ax.set_ylabel("Mean recall")
    ax.set_title("Top-K Depth Tradeoff")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_pio_vs_paper(long: pd.DataFrame, path: Path) -> None:
    subset = long[long["method"].isin(["PIO_GCN_Top20", "PIO_GCN_Top50", "PIO_GCN_Top100", "PIO_GCN_Top200", "paper_GCN_path_prob_strong", "paper_GCN_path_prob_strong_v2"])]
    _plot_tradeoff(subset, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze PIO-GCN Top-K depth tradeoff.")
    parser.add_argument("--output-dir", default="results/gcn_search/pio_topk_depth_tradeoff")
    parser.add_argument("--extended-dir", default="results/gcn_search/pio_extended_fulltruth_5seed")
    parser.add_argument("--paper-v2-model", default=TopkDepthTradeoffConfig.paper_v2_model)
    parser.add_argument("--paper-v2-normalizer", default=TopkDepthTradeoffConfig.paper_v2_normalizer)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100, 200])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_topk_depth_tradeoff(
        TopkDepthTradeoffConfig(
            output_dir=args.output_dir,
            extended_dir=args.extended_dir,
            paper_v2_model=args.paper_v2_model,
            paper_v2_normalizer=args.paper_v2_normalizer,
            top_k=tuple(args.top_k),
        )
    )


if __name__ == "__main__":
    main()
