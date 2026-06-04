from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from train_path_reranker import FEATURE_COLUMNS, TrainPathRerankerConfig, _fit_model, _predict_table


@dataclass(frozen=True)
class StrictHeldoutConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    baseline_eval_dir: str = "results/gcn_search/path_reranker_fulltruth_eval"
    output_dir: str = "results/gcn_search/path_reranker_strict_heldout_eval"
    seeds: tuple[int, ...] = (20260722, 20260723, 20260724, 20260725, 20260726)
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    epochs: int = 80
    learning_rate: float = 0.01
    lambda_pairwise_rank: float = 0.05


def evaluate_strict_heldout(config: StrictHeldoutConfig) -> dict:
    out = Path(config.output_dir)
    (out / "diagnostics").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "strict_heldout_config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "strict_heldout_feature_columns.json").write_text(json.dumps({"feature_columns": FEATURE_COLUMNS}, ensure_ascii=False, indent=2), encoding="utf-8")
    dataset = _load_dataset(config.dataset_dir)
    baseline_rows = _load_baseline_rows(config)
    learned_rows: list[dict] = []
    rank_shift_rows: list[dict] = []
    missed_rows: list[dict] = []
    for test_seed in config.seeds:
        train_seeds, val_seed = _fold_split(config.seeds, test_seed)
        train = dataset[dataset["seed"].isin(train_seeds)]
        test = dataset[dataset["seed"] == test_seed]
        for model_type in ("logistic", "mlp"):
            model, normalizer = _fit_model(
                train,
                TrainPathRerankerConfig(epochs=config.epochs, learning_rate=config.learning_rate, lambda_pairwise_rank=config.lambda_pairwise_rank),
                model_type,
            )
            pred = _predict_table(model, normalizer, test, model_type, test_seed)
            method = f"learned_{model_type}_reranker_strict"
            ordered = pred.sort_values(["learned_score", "path"], ascending=[False, True]).reset_index(drop=True)
            total = int(test["y_critical"].sum())
            for k in config.top_k:
                subset = ordered.head(k)
                learned_rows.append(
                    {
                        "seed": test_seed,
                        "method": method,
                        "top_k": k,
                        "critical_found": int(subset["y_critical"].sum()),
                        "critical_path_recall": float(subset["y_critical"].sum() / max(total, 1)),
                        "found": int(subset["y_critical"].sum()),
                        "mean_critical_rank": _mean_critical_rank(ordered),
                        "median_critical_rank": _median_critical_rank(ordered),
                        "train_seeds": ",".join(map(str, train_seeds)),
                        "val_seed": val_seed,
                        "notes": "strict leave-one-seed-out; test seed excluded from train and validation",
                    }
                )
            rank_lookup = {path: rank for rank, path in enumerate(ordered["path"], start=1)}
            for _, row in test[test["y_critical"] == 1].iterrows():
                learned_rank = int(rank_lookup.get(row["path"], 999999))
                rank_shift_rows.append({"seed": test_seed, "model_type": model_type, "path": row["path"], "rank_in_pio": int(row["rank_in_pio"]), "learned_rank": learned_rank})
                if learned_rank > 200:
                    missed_rows.append({"seed": test_seed, "model_type": model_type, "path": row["path"], "learned_rank": learned_rank, "rank_in_pio": int(row["rank_in_pio"])})
    per_fold = pd.DataFrame(baseline_rows + learned_rows)
    per_fold.to_csv(out / "strict_heldout_per_fold_summary.csv", index=False, encoding="utf-8-sig")
    comparison = _aggregate(per_fold)
    comparison.to_csv(out / "strict_heldout_method_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rank_shift_rows).to_csv(out / "diagnostics" / "strict_heldout_rank_shift.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(missed_rows).to_csv(out / "diagnostics" / "strict_heldout_missed_critical.csv", index=False, encoding="utf-8-sig")
    _plot_bar(comparison, out / "figures" / "strict_heldout_recall_bar.png")
    return {"output_dir": str(out)}


def _load_dataset(dataset_dir: str | Path) -> pd.DataFrame:
    return pd.concat([pd.read_csv(Path(dataset_dir) / name) for name in ["path_reranker_train.csv", "path_reranker_val.csv", "path_reranker_test.csv"]], ignore_index=True)


def _fold_split(seeds: tuple[int, ...], test_seed: int) -> tuple[tuple[int, ...], int]:
    remaining = [seed for seed in seeds if seed != test_seed]
    val_seed = remaining[-1]
    train_seeds = tuple(remaining[:-1])
    return train_seeds, val_seed


def _load_baseline_rows(config: StrictHeldoutConfig) -> list[dict]:
    table = pd.read_csv(Path(config.baseline_eval_dir) / "path_reranker_topk_summary.csv")
    keep = {"PIO_GCN", "paper_GCN_path_prob_strong", "LODF_yP", "rerank_physical_stress", "oracle"}
    rows = []
    for _, item in table[table["method"].isin(keep)].iterrows():
        row = item.to_dict()
        row["found"] = row.get("critical_found", "")
        rows.append(row)
    return rows


def _mean_critical_rank(ordered: pd.DataFrame) -> float:
    ranks = np.arange(1, len(ordered) + 1)
    crit = ordered["y_critical"].to_numpy(dtype=int) == 1
    return float(np.mean(ranks[crit])) if crit.any() else float("nan")


def _median_critical_rank(ordered: pd.DataFrame) -> float:
    ranks = np.arange(1, len(ordered) + 1)
    crit = ordered["y_critical"].to_numpy(dtype=int) == 1
    return float(np.median(ranks[crit])) if crit.any() else float("nan")


def _aggregate(per_fold: pd.DataFrame) -> pd.DataFrame:
    return (
        per_fold.groupby(["method", "top_k"], sort=False)
        .agg(
            num_test_seeds=("seed", "nunique"),
            mean_found=("critical_found", "mean"),
            std_found=("critical_found", "std"),
            mean_recall=("critical_path_recall", "mean"),
            std_recall=("critical_path_recall", "std"),
            mean_critical_rank=("mean_critical_rank", "mean"),
            median_critical_rank=("median_critical_rank", "median"),
            notes=("notes", "first"),
        )
        .reset_index()
    )


def _plot_bar(comparison: pd.DataFrame, path: Path) -> None:
    top = comparison[comparison["top_k"] == comparison["top_k"].max()]
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=160)
    ax.bar(top["method"], top["mean_recall"])
    ax.set_ylabel("Mean recall")
    ax.set_title("Strict Held-Out Recall at Max Top-K")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strict held-out seed evaluation for learned path reranker.")
    parser.add_argument("--dataset-dir", default=StrictHeldoutConfig.dataset_dir)
    parser.add_argument("--baseline-eval-dir", default=StrictHeldoutConfig.baseline_eval_dir)
    parser.add_argument("--output-dir", default=StrictHeldoutConfig.output_dir)
    parser.add_argument("--epochs", type=int, default=80)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluate_strict_heldout(StrictHeldoutConfig(dataset_dir=args.dataset_dir, baseline_eval_dir=args.baseline_eval_dir, output_dir=args.output_dir, epochs=args.epochs))


if __name__ == "__main__":
    main()
