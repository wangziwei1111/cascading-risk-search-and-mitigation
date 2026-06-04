from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PathRerankerEvalConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    model_dir: str = "results/gcn_search/path_reranker_models"
    rerank_dir: str = "results/gcn_search/pio_rerank_preliminary"
    ensemble_dir: str = "results/gcn_search/pio_ensemble_preliminary"
    output_dir: str = "results/gcn_search/path_reranker_fulltruth_eval"
    top_k: tuple[int, ...] = (20, 50, 100, 200)


def evaluate_path_reranker_fulltruth(config: PathRerankerEvalConfig) -> dict:
    out = Path(config.output_dir)
    (out / "diagnostics").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    dataset = _load_dataset(config.dataset_dir)
    predictions = pd.read_csv(Path(config.model_dir) / "path_reranker_validation_predictions.csv")
    per_seed_rows = _baseline_rows(config)
    per_seed_rows.extend(_learned_rows(dataset, predictions, config))
    per_seed = pd.DataFrame(per_seed_rows)
    per_seed.to_csv(out / "path_reranker_topk_summary.csv", index=False, encoding="utf-8-sig")
    per_seed.to_csv(out / "path_reranker_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    comparison = _aggregate(per_seed)
    comparison.to_csv(out / "path_reranker_method_comparison.csv", index=False, encoding="utf-8-sig")
    _diagnostics(dataset, predictions, out, config)
    _plot_bar(comparison, out / "figures" / "path_reranker_recall_bar.png")
    _plot_curve(comparison, out / "figures" / "path_reranker_topk_curve.png")
    _plot_rank_shift(out / "diagnostics" / "critical_rank_shift_summary.csv", out / "figures" / "path_reranker_rank_shift.png")
    return {"output_dir": str(out), "summary": str(out / "path_reranker_method_comparison.csv")}


def _load_dataset(dataset_dir: str | Path) -> pd.DataFrame:
    return pd.concat([pd.read_csv(Path(dataset_dir) / name) for name in ["path_reranker_train.csv", "path_reranker_val.csv", "path_reranker_test.csv"]], ignore_index=True)


def _baseline_rows(config: PathRerankerEvalConfig) -> list[dict]:
    rows: list[dict] = []
    rerank = pd.read_csv(Path(config.rerank_dir) / "rerank_topk_summary.csv")
    keep = {"PIO_GCN", "paper_GCN_path_prob_strong", "LODF_yP", "rerank_physical_stress", "oracle"}
    for _, item in rerank[rerank["method"].isin(keep)].iterrows():
        rows.append(item.to_dict())
    ensemble = pd.read_csv(Path(config.ensemble_dir) / "ensemble_topk_summary.csv")
    for _, item in ensemble[ensemble["method"] == "ensemble_alpha_0.75"].iterrows():
        rows.append(item.to_dict())
    return rows


def _learned_rows(dataset: pd.DataFrame, predictions: pd.DataFrame, config: PathRerankerEvalConfig) -> list[dict]:
    truth_total = dataset.groupby("seed")["y_critical"].sum().to_dict()
    rows: list[dict] = []
    for (model_type, seed), group in predictions.groupby(["model_type", "seed"], sort=False):
        ordered = group.sort_values(["learned_score", "path"], ascending=[False, True])
        method = f"learned_{model_type}_reranker"
        total = int(truth_total[int(seed)])
        for k in config.top_k:
            subset = ordered.head(k)
            found = int(subset["y_critical"].sum())
            rows.append(
                {
                    "seed": int(seed),
                    "method": method,
                    "top_k": int(k),
                    "critical_found": found,
                    "critical_path_recall": found / max(total, 1),
                    "notes": "leave-one-seed-out learned path reranker",
                }
            )
    return rows


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


def _diagnostics(dataset: pd.DataFrame, predictions: pd.DataFrame, out: Path, config: PathRerankerEvalConfig) -> None:
    best = _best_model(predictions, config)
    pred = predictions[predictions["model_type"] == best].copy()
    rows = []
    missed = []
    rescued = []
    for seed, group in pred.groupby("seed"):
        ordered = group.sort_values(["learned_score", "path"], ascending=[False, True]).reset_index(drop=True)
        rank = {path: i for i, path in enumerate(ordered["path"], start=1)}
        source = dataset[dataset["seed"] == seed].set_index("path")
        critical = source[source["y_critical"] == 1]
        for path, item in critical.iterrows():
            rows.append(
                {
                    "seed": int(seed),
                    "path": path,
                    "rank_in_pio": int(item["rank_in_pio"]),
                    "rank_in_learned": int(rank.get(path, 999999)),
                    "rank_shift_pio_minus_learned": int(item["rank_in_pio"]) - int(rank.get(path, 999999)),
                }
            )
            if rank.get(path, 999999) > 200:
                missed.append({"seed": int(seed), "path": path, "learned_rank": int(rank.get(path, 999999)), "pio_rank": int(item["rank_in_pio"])})
            if rank.get(path, 999999) <= 200 and int(item["rank_in_pio"]) > 200:
                rescued.append({"seed": int(seed), "path": path, "learned_rank": int(rank.get(path, 999999)), "pio_rank": int(item["rank_in_pio"])})
    pd.DataFrame(rows).to_csv(out / "diagnostics" / "critical_rank_shift_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(missed).to_csv(out / "diagnostics" / "missed_critical_after_learned_rerank.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rescued).to_csv(out / "diagnostics" / "rescued_critical_paths.csv", index=False, encoding="utf-8-sig")


def _best_model(predictions: pd.DataFrame, config: PathRerankerEvalConfig) -> str:
    rows = []
    for model_type, group in predictions.groupby("model_type"):
        total = group.groupby("seed")["y_critical"].sum().sum()
        found = 0
        for _, seed_group in group.groupby("seed"):
            found += int(seed_group.sort_values(["learned_score", "path"], ascending=[False, True]).head(100)["y_critical"].sum())
        rows.append((found / max(total, 1), model_type))
    return sorted(rows, reverse=True)[0][1]


def _plot_bar(comparison: pd.DataFrame, path: Path) -> None:
    top = comparison[comparison["top_k"] == comparison["top_k"].max()]
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=160)
    ax.bar(top["method"], top["mean_recall"])
    ax.set_ylabel("Mean recall")
    ax.set_title("Path Reranker Recall at Max Top-K")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_curve(comparison: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=160)
    for method, group in comparison.groupby("method", sort=False):
        group = group.sort_values("top_k")
        ax.plot(group["top_k"], group["mean_recall"], marker="o", label=method)
    ax.set_xlabel("Top-K")
    ax.set_ylabel("Mean recall")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_rank_shift(csv_path: Path, output: Path) -> None:
    table = pd.read_csv(csv_path)
    fig, ax = plt.subplots(figsize=(7, 4), dpi=160)
    ax.hist(table["rank_shift_pio_minus_learned"], bins=30)
    ax.set_title("Critical Path Rank Shift")
    ax.set_xlabel("PIO rank - learned rank")
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate learned path reranker against full-truth summaries.")
    parser.add_argument("--dataset-dir", default=PathRerankerEvalConfig.dataset_dir)
    parser.add_argument("--model-dir", default=PathRerankerEvalConfig.model_dir)
    parser.add_argument("--output-dir", default=PathRerankerEvalConfig.output_dir)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluate_path_reranker_fulltruth(PathRerankerEvalConfig(dataset_dir=args.dataset_dir, model_dir=args.model_dir, output_dir=args.output_dir))


if __name__ == "__main__":
    main()
