from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from evaluate_path_reranker_renewable import RenewableRerankerEvalConfig, evaluate_path_reranker_renewable
from path_reranker_eval_utils import dataclass_payload, write_json


@dataclass(frozen=True)
class CrossScenarioEvalConfig:
    output_dir: str = "results/gcn_search/path_reranker_cross_scenario_eval"
    renewable_eval_dir: str = "results/gcn_search/path_reranker_renewable_eval"
    run_renewable_if_missing: bool = True


def run_cross_scenario_eval(config: CrossScenarioEvalConfig) -> dict:
    out = Path(config.output_dir)
    (out / "diagnostics").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    write_json(out / "cross_scenario_config.json", dataclass_payload(config))
    renewable_summary = Path(config.renewable_eval_dir) / "renewable_path_reranker_method_comparison.csv"
    renewable_per_seed = Path(config.renewable_eval_dir) / "renewable_path_reranker_per_seed_summary.csv"
    if (not renewable_summary.exists() or not renewable_per_seed.exists()) and config.run_renewable_if_missing:
        evaluate_path_reranker_renewable(RenewableRerankerEvalConfig(output_dir=config.renewable_eval_dir))
    comparison = pd.read_csv(renewable_summary)
    per_seed = pd.read_csv(renewable_per_seed)
    comparison = comparison.copy()
    comparison.insert(0, "setting", "standard_train_to_synthetic_renewable_test")
    per_seed = per_seed.copy()
    per_seed.insert(0, "setting", "standard_train_to_synthetic_renewable_test")
    comparison.to_csv(out / "cross_scenario_method_comparison.csv", index=False, encoding="utf-8-sig")
    per_seed.to_csv(out / "cross_scenario_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    _failure_modes(per_seed).to_csv(out / "diagnostics" / "cross_scenario_failure_modes.csv", index=False, encoding="utf-8-sig")
    _plot(comparison, out / "figures" / "cross_scenario_recall_bar.png")
    return {"output_dir": str(out), "summary": str(out / "cross_scenario_method_comparison.csv")}


def _failure_modes(per_seed: pd.DataFrame) -> pd.DataFrame:
    top100 = per_seed[per_seed["top_k"] == 100].copy()
    pivot = top100.pivot_table(index=["setting", "seed"], columns="method", values="critical_path_recall", aggfunc="first").reset_index()
    rows = []
    for _, item in pivot.iterrows():
        pio = float(item.get("PIO_GCN", 0.0))
        learned = float(item.get("learned_mlp_reranker_renewable", item.get("learned_mlp_reranker_external", 0.0)))
        rows.append(
            {
                "setting": item["setting"],
                "seed": int(item["seed"]),
                "pio_recall_at_100": pio,
                "learned_mlp_recall_at_100": learned,
                "learned_minus_pio_at_100": learned - pio,
                "failure_mode": "learned worse than PIO on shifted synthetic renewable case" if learned < pio else "learned not worse than PIO",
            }
        )
    return pd.DataFrame(rows)


def _plot(comparison: pd.DataFrame, path: Path) -> None:
    top = comparison[comparison["top_k"] == comparison["top_k"].max()]
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=160)
    ax.bar(top["method"].astype(str), top["mean_recall"].astype(float))
    ax.set_title("Cross-Scenario Recall at Max Top-K")
    ax.set_ylabel("Mean recall")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-scenario path reranker evaluation.")
    parser.add_argument("--output-dir", default=CrossScenarioEvalConfig.output_dir)
    parser.add_argument("--renewable-eval-dir", default=CrossScenarioEvalConfig.renewable_eval_dir)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_cross_scenario_eval(CrossScenarioEvalConfig(output_dir=args.output_dir, renewable_eval_dir=args.renewable_eval_dir))


if __name__ == "__main__":
    main()
