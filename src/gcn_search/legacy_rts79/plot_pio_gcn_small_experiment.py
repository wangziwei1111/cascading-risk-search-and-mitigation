from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_small_experiment(per_seed_csv: str, aggregate_csv: str, output_dir: str) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    per_seed = pd.read_csv(per_seed_csv)
    aggregate = pd.read_csv(aggregate_csv)
    outputs: dict[str, str] = {}

    if "mean_critical_path_recall" in aggregate.columns and aggregate["mean_critical_path_recall"].notna().any():
        outputs["topk_recall_bar"] = _bar(
            aggregate,
            value_col="mean_critical_path_recall",
            ylabel="Mean critical path recall",
            title="PIO-GCN Top-K Critical Path Recall",
            path=out / "topk_recall_bar.png",
        )
    else:
        print("No full recall column found; skip topk_recall_bar.png.")

    outputs["critical_found_bar"] = _bar(
        aggregate,
        value_col="mean_num_critical_found",
        ylabel="Mean critical paths found",
        title="PIO-GCN Top-K Critical Paths Found",
        path=out / "critical_found_bar.png",
    )
    runtime = per_seed.groupby("top_k", as_index=False)["runtime_seconds"].mean()
    outputs["runtime_bar"] = _bar(
        runtime,
        value_col="runtime_seconds",
        ylabel="Mean runtime (seconds)",
        title="PIO-GCN Top-K Runtime",
        path=out / "runtime_bar.png",
    )
    return outputs


def _bar(table: pd.DataFrame, value_col: str, ylabel: str, title: str, path: Path) -> str:
    labels = [f"Top-{int(value)}" for value in table["top_k"]]
    values = [float(value) for value in table[value_col]]
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=160)
    bars = ax.bar(labels, values, color="#1f77b4")
    ax.set_title(title)
    ax.set_xlabel("Top-K setting")
    ax.set_ylabel(ylabel)
    ax.bar_label(bars, fmt="%.3g", padding=3)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot PIO-GCN small experiment summaries.")
    parser.add_argument("--per-seed-summary", required=True)
    parser.add_argument("--aggregate-summary", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plot_small_experiment(args.per_seed_summary, args.aggregate_summary, args.output_dir)


if __name__ == "__main__":
    main()
