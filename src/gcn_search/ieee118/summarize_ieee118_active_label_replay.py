from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / "results" / "gcn_search" / "ieee118_simulation_efficient_gcn"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize same-budget IEEE118 hidden-label active-learning replay runs."
    )
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--run-glob", default="*_smoke")
    return parser.parse_args(argv)


def summarize(
    input_root: Path,
    output_dir: Path,
    *,
    run_glob: str = "*_smoke",
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for run_dir in sorted(input_root.glob(run_glob)):
        summary_path = run_dir / "active_label_replay_summary.json"
        rounds_path = run_dir / "active_label_replay_round_metrics.csv"
        if not summary_path.exists() or not rounds_path.exists():
            continue
        run_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        acquisition_seed = int(
            run_summary.get("train_config", {}).get("random_seed", 0)
        )
        rounds = pd.read_csv(rounds_path, encoding="utf-8-sig")
        for row in rounds.to_dict(orient="records"):
            records.append(
                {
                    "method": str(run_summary["acquisition_mode"]),
                    "acquisition_seed": acquisition_seed,
                    "active_round": int(row["active_round"]),
                    "queried_training_labels": int(row["queried_training_labels"]),
                    "queried_training_label_fraction": float(
                        row["queried_training_label_fraction"]
                    ),
                    "queried_positive_labels": int(row["queried_positive_labels"]),
                    "validation_average_precision": float(
                        row["validation_average_precision"]
                    ),
                    "test_average_precision": float(row["test_average_precision"]),
                    "risk_calibration_feasible": bool(
                        row.get("risk_calibration_feasible", False)
                    ),
                    "risk_calibration_upper_risk": float(
                        row.get("risk_calibration_upper_risk", float("nan"))
                    ),
                    "test_verification_budget_ratio": float(
                        row.get("test_verification_budget_ratio", float("nan"))
                    ),
                    "test_verification_positive_recall": float(
                        row.get("test_verification_positive_recall", float("nan"))
                    ),
                }
            )
    if not records:
        raise FileNotFoundError(
            f"No complete active-label replay runs matching {run_glob!r} were found under "
            f"{input_root}."
        )

    table = pd.DataFrame(records).sort_values(
        ["queried_training_labels", "method", "acquisition_seed", "active_round"],
        kind="stable",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(
        output_dir / "ieee118_active_label_replay_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )
    aggregate_records: list[dict[str, Any]] = []
    metric_names = (
        "queried_positive_labels",
        "validation_average_precision",
        "test_average_precision",
        "test_verification_budget_ratio",
        "test_verification_positive_recall",
    )
    for (method, labels), group in table.groupby(
        ["method", "queried_training_labels"],
        sort=True,
    ):
        record: dict[str, Any] = {
            "method": str(method),
            "queried_training_labels": int(labels),
            "num_acquisition_seeds": int(group["acquisition_seed"].nunique()),
            "queried_training_label_fraction": float(
                group["queried_training_label_fraction"].mean()
            ),
        }
        for metric in metric_names:
            values = group[metric].astype(float).to_numpy()
            record[f"{metric}_mean"] = float(values.mean())
            record[f"{metric}_std"] = float(values.std(ddof=0))
        aggregate_records.append(record)
    aggregate_table = pd.DataFrame(aggregate_records)
    aggregate_table.to_csv(
        output_dir / "ieee118_active_label_replay_aggregate.csv",
        index=False,
        encoding="utf-8-sig",
    )
    final_rows = (
        table.sort_values(
            ["method", "acquisition_seed", "active_round"],
            kind="stable",
        )
        .groupby(["method", "acquisition_seed"], sort=True)
        .tail(1)
    )
    best_rows = table.loc[
        table.groupby(["method", "acquisition_seed"])[
            "validation_average_precision"
        ].idxmax()
    ]
    method_summaries: list[dict[str, Any]] = []
    for method in sorted(table["method"].unique()):
        final = final_rows.loc[final_rows["method"] == method]
        best = best_rows.loc[best_rows["method"] == method]
        final_labels = final["queried_training_labels"].astype(int).unique()
        if len(final_labels) != 1:
            raise ValueError(
                f"Final queried-label budgets differ across {method} runs: "
                f"{final_labels.tolist()}"
            )
        method_summaries.append(
            {
                "method": method,
                "num_acquisition_seeds": int(final["acquisition_seed"].nunique()),
                "final_queried_training_labels": int(final_labels[0]),
                "final_queried_training_label_fraction_mean": float(
                    final["queried_training_label_fraction"].mean()
                ),
                "final_queried_positive_labels_mean": float(
                    final["queried_positive_labels"].mean()
                ),
                "final_queried_positive_labels_std": float(
                    final["queried_positive_labels"].std(ddof=0)
                ),
                "final_validation_average_precision_mean": float(
                    final["validation_average_precision"].mean()
                ),
                "final_validation_average_precision_std": float(
                    final["validation_average_precision"].std(ddof=0)
                ),
                "final_test_average_precision_mean": float(
                    final["test_average_precision"].mean()
                ),
                "final_test_average_precision_std": float(
                    final["test_average_precision"].std(ddof=0)
                ),
                "best_validation_average_precision_mean": float(
                    best["validation_average_precision"].mean()
                ),
                "test_average_precision_at_best_validation_round_mean": float(
                    best["test_average_precision"].mean()
                ),
                "final_test_verification_budget_ratio_mean": float(
                    final["test_verification_budget_ratio"].mean()
                ),
                "final_test_verification_positive_recall_mean": float(
                    final["test_verification_positive_recall"].mean()
                ),
            }
        )
    summary = {
        "status": "complete",
        "research_stage": "Phase 1 retrospective hidden-label replay smoke comparison",
        "num_methods": len(method_summaries),
        "methods": method_summaries,
        "interpretation_limit": (
            "These runs hide previously generated labels. They compare acquisition logic but "
            "do not yet demonstrate prospective savings from calling a physical simulator online."
        ),
    }
    (output_dir / "ieee118_active_label_replay_comparison.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            summarize(args.input_root, args.output_dir, run_glob=args.run_glob),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
