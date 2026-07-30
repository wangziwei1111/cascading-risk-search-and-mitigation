from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(IEEE118_DIR))

from train_ieee118_paper_aligned_gcn import split_metrics


DEFAULT_RUN_ROOT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase2_budget_curve"
)
DEFAULT_DATASET = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "paper_8000_residual"
    / "ieee118_residual_reachable_gcn_dataset.npz"
)
DEFAULT_BASELINE_DIR = (
    ROOT / "results" / "gcn_search" / "ieee118_n1_residual_scaleup"
)
DEFAULT_OUTPUT = (
    ROOT / "results" / "gcn_search" / "ieee118_simulation_efficient_gcn"
)
PRIMARY_METHOD = "pmf_hybrid_prior_corrected"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create compact Phase-2 IEEE118 label-efficiency artifacts."
    )
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--full-label-metrics-json",
        type=Path,
        default=(
            DEFAULT_BASELINE_DIR
            / "training_k6"
            / "ieee118_residual_reachable_gcn_k6_metrics.json"
        ),
    )
    parser.add_argument(
        "--full-label-thresholds-json",
        type=Path,
        default=DEFAULT_BASELINE_DIR / "eval_k6" / "ieee118_n1_gated_thresholds.json",
    )
    parser.add_argument(
        "--dual-anchor-summary-json",
        type=Path,
        default=DEFAULT_OUTPUT / "ieee118_phase2_dual_anchor_summary.json",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}. This summary does not regenerate it.")


def _full_label_baseline(metrics_path: Path, thresholds_path: Path) -> dict[str, Any]:
    _require_file(metrics_path, "full-label GCN metrics JSON")
    _require_file(thresholds_path, "full-label search thresholds JSON")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
    primary = next(
        row
        for row in thresholds
        if row["method"] == "N1_gate_plus_RTS79_residual_reachable_GCN_path_prob"
    )
    residual = next(
        row
        for row in thresholds
        if row["method"] == "RTS79_residual_reachable_GCN_path_prob_residual_only"
    )
    classification = metrics["classification_metrics"]
    return {
        "num_training_oracle_labels": int(
            classification["train"]["num_labels"]
        ),
        "validation_average_precision": float(
            classification["validation"]["average_precision"]
        ),
        "test_average_precision": float(classification["test"]["average_precision"]),
        "s0_average_precision": float(classification["S0"]["average_precision"]),
        "s1_average_precision": float(classification["S1"]["average_precision"]),
        "path_prob_K90": int(primary["K90"]),
        "path_prob_K95": int(primary["K95"]),
        "path_prob_K99": int(primary["K99"]),
        "path_prob_K100": int(primary["K100"]),
        "residual_path_prob_K90": int(residual["K90"]),
    }


def _final_type_metrics(run_root: Path, dataset_path: Path) -> list[dict[str, Any]]:
    _require_file(dataset_path, "residual GCN dataset NPZ")
    dataset = np.load(dataset_path, allow_pickle=True)
    records: list[dict[str, Any]] = []
    for checkpoint_path in sorted(
        run_root.glob("*_seed_*/active_label_replay_local_checkpoint.npz")
    ):
        checkpoint = np.load(checkpoint_path)
        source_indices = checkpoint["subset_source_state_indices"].astype(np.int64)
        probability = checkpoint["mean_probability"].astype(float)
        split = dataset["split"][source_indices].astype(str)
        sample_type = dataset["sample_type"][source_indices].astype(str)
        y = dataset["y_gcn"][source_indices].astype(np.int64)
        valid = dataset["loss_mask"][source_indices].astype(bool)
        record: dict[str, Any] = {
            "method": checkpoint_path.parent.name.rsplit("_seed_", 1)[0],
            "acquisition_seed": int(
                checkpoint_path.parent.name.rsplit("_seed_", 1)[1]
            ),
        }
        for state_type in ("S0", "S1"):
            rows = (split == "test") & (sample_type == state_type)
            record[f"test_{state_type.lower()}_average_precision"] = float(
                split_metrics(y[rows], probability[rows], valid[rows])[
                    "average_precision"
                ]
            )
        records.append(record)
    return records


def summarize_phase2(
    run_root: Path,
    dataset_path: Path,
    metrics_path: Path,
    thresholds_path: Path,
    output_dir: Path,
    dual_anchor_summary_path: Path | None = None,
) -> dict[str, Any]:
    aggregate_path = (
        run_root / "compact" / "ieee118_active_label_replay_aggregate.csv"
    )
    _require_file(aggregate_path, "Phase-2 aggregate CSV")
    aggregate = pd.read_csv(aggregate_path, encoding="utf-8-sig")
    baseline = _full_label_baseline(metrics_path, thresholds_path)
    required = {
        "method",
        "queried_training_labels",
        "queried_training_label_fraction",
        "queried_positive_labels_mean",
        "test_average_precision_mean",
        "test_average_precision_std",
        "search_path_prob_K90_mean",
        "search_path_prob_K90_std",
        "search_path_prob_K95_mean",
        "search_path_prob_K99_mean",
        "search_residual_path_prob_K90_mean",
    }
    missing = sorted(required - set(aggregate))
    if missing:
        raise ValueError(f"Phase-2 aggregate CSV is missing fields: {missing}")
    compact = aggregate.copy()
    compact["oracle_label_saving_fraction"] = (
        1.0
        - compact["queried_training_labels"]
        / baseline["num_training_oracle_labels"]
    )
    compact["test_ap_fraction_of_full_label"] = (
        compact["test_average_precision_mean"]
        / baseline["test_average_precision"]
    )
    compact["path_prob_K90_gap_vs_full_label"] = (
        compact["search_path_prob_K90_mean"] - baseline["path_prob_K90"]
    )
    columns = [
        "method",
        "queried_training_labels",
        "queried_training_label_fraction",
        "oracle_label_saving_fraction",
        "num_acquisition_seeds",
        "queried_positive_labels_mean",
        "queried_positive_labels_std",
        "validation_average_precision_mean",
        "validation_average_precision_std",
        "test_average_precision_mean",
        "test_average_precision_std",
        "test_ap_fraction_of_full_label",
        "search_path_prob_K90_mean",
        "search_path_prob_K90_std",
        "path_prob_K90_gap_vs_full_label",
        "search_path_prob_K95_mean",
        "search_path_prob_K99_mean",
        "search_residual_path_prob_K90_mean",
        "search_second_only_K90_mean",
        "search_second_only_K95_mean",
        "search_second_only_K99_mean",
    ]
    compact = compact[columns].sort_values(
        ["queried_training_labels", "method"],
        kind="stable",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    curve_name = "ieee118_phase2_label_efficiency_curve.csv"
    compact.to_csv(
        output_dir / curve_name,
        index=False,
        encoding="utf-8-sig",
    )

    type_records = _final_type_metrics(run_root, dataset_path)
    type_table = pd.DataFrame(type_records)
    type_summary: list[dict[str, Any]] = []
    if not type_table.empty:
        for method, group in type_table.groupby("method", sort=True):
            type_summary.append(
                {
                    "method": str(method),
                    "num_acquisition_seeds": int(group["acquisition_seed"].nunique()),
                    "test_s0_average_precision_mean": float(
                        group["test_s0_average_precision"].mean()
                    ),
                    "test_s0_average_precision_std": float(
                        group["test_s0_average_precision"].std(ddof=0)
                    ),
                    "test_s1_average_precision_mean": float(
                        group["test_s1_average_precision"].mean()
                    ),
                    "test_s1_average_precision_std": float(
                        group["test_s1_average_precision"].std(ddof=0)
                    ),
                }
            )

    final = compact.loc[
        compact["queried_training_labels"].eq(
            compact["queried_training_labels"].max()
        )
    ]
    primary = final.loc[final["method"].eq(PRIMARY_METHOD)]
    if len(primary) != 1:
        raise ValueError(f"Expected one final row for {PRIMARY_METHOD}.")
    primary_row = primary.iloc[0]
    validation_gate = bool(
        primary_row["validation_average_precision_mean"]
        >= 0.95 * baseline["validation_average_precision"]
    )
    k90_gate = bool(
        primary_row["search_path_prob_K90_mean"]
        <= 1.10 * baseline["path_prob_K90"]
    )
    label_gate = bool(
        primary_row["queried_training_label_fraction"] <= 0.10
    )
    summary = {
        "status": "complete",
        "research_stage": "Phase 2 retrospective label-efficiency experiment",
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "num_acquisition_seeds": int(primary_row["num_acquisition_seeds"]),
        "full_label_baseline": baseline,
        "primary_method": PRIMARY_METHOD,
        "primary_5_percent_result": {
            "queried_training_labels": int(
                primary_row["queried_training_labels"]
            ),
            "queried_training_label_fraction": float(
                primary_row["queried_training_label_fraction"]
            ),
            "oracle_label_saving_fraction": float(
                primary_row["oracle_label_saving_fraction"]
            ),
            "test_average_precision_mean": float(
                primary_row["test_average_precision_mean"]
            ),
            "test_average_precision_std": float(
                primary_row["test_average_precision_std"]
            ),
            "test_ap_fraction_of_full_label": float(
                primary_row["test_ap_fraction_of_full_label"]
            ),
            "path_prob_K90_mean": float(
                primary_row["search_path_prob_K90_mean"]
            ),
            "path_prob_K90_std": float(
                primary_row["search_path_prob_K90_std"]
            ),
            "path_prob_K95_mean": float(
                primary_row["search_path_prob_K95_mean"]
            ),
            "path_prob_K99_mean": float(
                primary_row["search_path_prob_K99_mean"]
            ),
            "residual_path_prob_K90_mean": float(
                primary_row["search_residual_path_prob_K90_mean"]
            ),
        },
        "final_test_metrics_by_state_type": type_summary,
        "gate_1": {
            "validation_ap_95_percent_of_full_label": validation_gate,
            "overall_path_K90_not_materially_worse": k90_gate,
            "within_10_percent_oracle_labels": label_gate,
            "passed": bool(validation_gate and k90_gate and label_gate),
            "reason": (
                "The primary method uses only 5% of labels and approaches overall "
                "gated K90, but mean validation AP is below 95% of the full-label "
                "value and residual high-recall ranking remains materially worse."
            ),
        },
        "negative_result": (
            "Active selection improves AP and gated K90 label efficiency, but "
            "selection bias still harms residual-only K90/K95/K99. The next core "
            "experiment must estimate query propensities or preserve a stronger "
            "representative loss, rather than claiming deployment readiness."
        ),
        "interpretation_limit": (
            "All labels were generated previously and hidden retrospectively. "
            "This does not yet prove prospective physical-oracle savings."
        ),
        "output_files": {"budget_curve": curve_name},
    }
    if dual_anchor_summary_path is not None and dual_anchor_summary_path.exists():
        dual = json.loads(dual_anchor_summary_path.read_text(encoding="utf-8"))
        selected_dual = dual["recommended_for_next_seed"]
        summary["dual_anchor_diagnostic"] = {
            "validation_selected_fusion": dual["validation_selected_fusion"],
            "training_oracle_labels_mean": float(
                selected_dual["training_oracle_labels_mean"]
            ),
            "training_oracle_fraction_mean": float(
                selected_dual["training_oracle_fraction_mean"]
            ),
            "path_prob_K90_mean": float(
                selected_dual["search_path_prob_K90_mean"]
            ),
            "path_prob_K95_mean": float(
                selected_dual["search_path_prob_K95_mean"]
            ),
            "path_prob_K99_mean": float(
                selected_dual["search_path_prob_K99_mean"]
            ),
            "residual_path_prob_K90_mean": float(
                selected_dual["search_residual_path_prob_K90_mean"]
            ),
            "status": dual["formal_status"],
        }
    summary_name = "ieee118_phase2_label_efficiency_summary.json"
    (output_dir / summary_name).write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    readme_name = "ieee118_phase2_label_efficiency_readme.md"
    (output_dir / readme_name).write_text(
        "# IEEE118 Phase-2 Label-Efficiency Result\n\n"
        "The unchanged RTS-79 `PaperStyleRts79Gcn` was trained with hidden-label "
        "replay at five acquisition seeds. The primary hybrid uses random anchors, "
        "risk/uncertainty/physics cohorts, and queried-label prior correction.\n\n"
        f"- Full-label training oracle labels: "
        f"{baseline['num_training_oracle_labels']:,}\n"
        f"- Primary queried labels: "
        f"{int(primary_row['queried_training_labels']):,} "
        f"({100.0 * primary_row['queried_training_label_fraction']:.2f}%)\n"
        f"- Mean test AP: {primary_row['test_average_precision_mean']:.4f} "
        f"+/- {primary_row['test_average_precision_std']:.4f} "
        f"(full-label {baseline['test_average_precision']:.4f})\n"
        f"- Mean gated path K90: {primary_row['search_path_prob_K90_mean']:.1f} "
        f"+/- {primary_row['search_path_prob_K90_std']:.1f} "
        f"(full-label {baseline['path_prob_K90']})\n"
        f"- Mean gated path K95/K99: "
        f"{primary_row['search_path_prob_K95_mean']:.1f}/"
        f"{primary_row['search_path_prob_K99_mean']:.1f}\n\n"
        "The validation-selected dual-anchor mean fusion uses about 9.52% of "
        "the union label budget and improves the active-only K99/residual K90 "
        "diagnostics, but it remains a freeze-then-confirm recommendation.\n\n"
        "Gate 1 is not passed. Residual-only high-recall ranking remains much worse "
        "than the full-label model, and this is retrospective replay rather than an "
        "on-demand physical-oracle run.\n",
        encoding="utf-8",
    )
    summary["output_files"].update(
        {"summary": summary_name, "readme": readme_name}
    )
    (output_dir / summary_name).write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            summarize_phase2(
                args.run_root,
                args.dataset_npz,
                args.full_label_metrics_json,
                args.full_label_thresholds_json,
                args.output_dir,
                args.dual_anchor_summary_json,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
