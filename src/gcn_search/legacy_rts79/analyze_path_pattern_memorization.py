from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from evaluate_path_reranker_strict_heldout import _load_dataset
from path_reranker_eval_utils import dataclass_payload, write_json


@dataclass(frozen=True)
class MemorizationAnalysisConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    strict_eval_dir: str = "results/gcn_search/path_reranker_strict_heldout_eval"
    external_eval_dir: str = "results/gcn_search/path_reranker_extended_strict_eval"
    renewable_eval_dir: str = "results/gcn_search/path_reranker_renewable_eval"
    output_dir: str = "results/gcn_search/path_reranker_memorization_analysis"


def analyze_path_pattern_memorization(config: MemorizationAnalysisConfig) -> dict:
    out = Path(config.output_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    write_json(out / "memorization_analysis_config.json", dataclass_payload(config))
    dataset = _load_dataset(config.dataset_dir)
    repeated = _repeated_path_summary(dataset)
    line_freq = _line_pair_frequency(dataset)
    risk = _risk_summary(dataset, repeated, config)
    repeated.to_csv(out / "repeated_path_pattern_summary.csv", index=False, encoding="utf-8-sig")
    line_freq.to_csv(out / "line_pair_frequency_summary.csv", index=False, encoding="utf-8-sig")
    risk.to_csv(out / "memorization_risk_summary.csv", index=False, encoding="utf-8-sig")
    _write_recommendations(out / "recommendations.md", risk)
    _plot_line_frequency(line_freq, out / "figures" / "line_pair_frequency.png")
    return {"output_dir": str(out), "summary": str(out / "memorization_risk_summary.csv")}


def _repeated_path_summary(dataset: pd.DataFrame) -> pd.DataFrame:
    return (
        dataset.groupby("path")
        .agg(
            num_seeds_seen=("seed", "nunique"),
            num_samples=("path", "count"),
            critical_count=("y_critical", "sum"),
            critical_rate=("y_critical", "mean"),
            mean_pio_score=("pio_score", "mean"),
            mean_lodf_score=("lodf_score", "mean"),
            mean_max_loading_ratio=("max_loading_ratio", "mean"),
        )
        .reset_index()
        .sort_values(["critical_count", "critical_rate", "path"], ascending=[False, False, True])
    )


def _line_pair_frequency(dataset: pd.DataFrame) -> pd.DataFrame:
    work = dataset.copy()
    return (
        work.groupby(["first_line", "second_line"])
        .agg(num_seeds_seen=("seed", "nunique"), critical_count=("y_critical", "sum"), critical_rate=("y_critical", "mean"), mean_pio_score=("pio_score", "mean"))
        .reset_index()
        .sort_values(["critical_count", "critical_rate"], ascending=[False, False])
    )


def _risk_summary(dataset: pd.DataFrame, repeated: pd.DataFrame, config: MemorizationAnalysisConfig) -> pd.DataFrame:
    total_critical = int(dataset["y_critical"].sum())
    top10_critical = int(repeated.head(10)["critical_count"].sum())
    repeated_positive = repeated[(repeated["num_seeds_seen"] >= 3) & (repeated["critical_rate"] >= 0.5)]
    rows = [
        {
            "item": "training_dataset_path_pattern_concentration",
            "value": float(top10_critical / max(total_critical, 1)),
            "interpretation": "fraction of critical labels covered by the ten most frequent critical line pairs",
            "risk_level": "medium" if top10_critical / max(total_critical, 1) > 0.30 else "low",
        },
        {
            "item": "repeated_positive_patterns",
            "value": int(len(repeated_positive)),
            "interpretation": "line pairs repeatedly critical across at least three training seeds",
            "risk_level": "medium" if len(repeated_positive) > 0 else "low",
        },
    ]
    for name, path in {
        "strict_heldout_summary_available": Path(config.strict_eval_dir) / "strict_heldout_method_comparison.csv",
        "external_summary_available": Path(config.external_eval_dir) / "extended_strict_method_comparison.csv",
        "renewable_summary_available": Path(config.renewable_eval_dir) / "renewable_path_reranker_method_comparison.csv",
    }.items():
        rows.append({"item": name, "value": int(path.exists() and path.stat().st_size > 0), "interpretation": str(path), "risk_level": "info"})
    rows.append(
        {
            "item": "overall_memorization_risk",
            "value": "medium",
            "interpretation": "No direct label leakage was found earlier, but fixed RTS-79 topology can still allow path-pattern learning; external and renewable tests are needed before stronger claims.",
            "risk_level": "medium",
        }
    )
    return pd.DataFrame(rows)


def _write_recommendations(path: Path, risk: pd.DataFrame) -> None:
    path.write_text(
        "\n".join(
            [
                "# Path Pattern Memorization Recommendations",
                "",
                "- Treat learned path reranker results as preliminary until evaluated on more unseen load/renewable scenarios.",
                "- Report external-seed and synthetic-renewable results together with standard RTS-79 results.",
                "- Avoid claiming final proof or production readiness.",
                "- Prefer feature groups without direct line identity if future tests show severe topology memorization.",
                "",
                "Current risk summary:",
                "",
                _markdown_table(risk),
            ]
        ),
        encoding="utf-8",
    )


def _markdown_table(table: pd.DataFrame) -> str:
    columns = list(table.columns)
    rows = ["|" + "|".join(columns) + "|", "|" + "|".join(["---"] * len(columns)) + "|"]
    for _, item in table.iterrows():
        rows.append("|" + "|".join(str(item[col]).replace("|", "/") for col in columns) + "|")
    return "\n".join(rows)


def _plot_line_frequency(line_freq: pd.DataFrame, path: Path) -> None:
    top = line_freq.head(15).copy()
    top["pair"] = top["first_line"].astype(str) + "->" + top["second_line"].astype(str)
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=160)
    ax.bar(top["pair"], top["critical_count"].astype(float))
    ax.set_ylabel("Critical count")
    ax.set_title("Most Frequent Critical Line-Pair Patterns")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze path-pattern memorization risk for learned reranker.")
    parser.add_argument("--dataset-dir", default=MemorizationAnalysisConfig.dataset_dir)
    parser.add_argument("--output-dir", default=MemorizationAnalysisConfig.output_dir)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_path_pattern_memorization(MemorizationAnalysisConfig(dataset_dir=args.dataset_dir, output_dir=args.output_dir))


if __name__ == "__main__":
    main()
