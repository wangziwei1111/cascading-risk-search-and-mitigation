from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PILOT = ROOT / "results" / "gcn_search" / "ieee118_n1_residual_reachable_gcn"
DEFAULT_SCALEUP = ROOT / "results" / "gcn_search" / "ieee118_n1_residual_scaleup"
METHOD_PATH = "N1_gate_plus_RTS79_residual_reachable_GCN_path_prob"
METHOD_SECOND = "N1_gate_plus_RTS79_residual_reachable_GCN_second_only"
KEY_BUDGETS = [100, 500, 1000, 2000, 3000, 5000]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare IEEE118 residual GCN pilot-2000 and paper-8000 runs.")
    parser.add_argument("--pilot-root", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--scaleup-root", type=Path, default=DEFAULT_SCALEUP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SCALEUP / "compact")
    return parser.parse_args(argv)


def read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing residual scale-up comparison input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def threshold_row(rows: list[dict[str, Any]], method: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("method") == method and row.get("universe") == "full"]
    if len(matches) != 1:
        raise ValueError(f"Expected one full-universe threshold row for {method}, found {len(matches)}.")
    return matches[0]


def load_run(run_root: Path, label: str) -> tuple[list[dict[str, Any]], pd.DataFrame, dict[str, Any]]:
    training_dir = run_root / "training_k6"
    eval_dir = run_root / "eval_k6"
    metrics = read_json(training_dir / "ieee118_residual_reachable_gcn_k6_metrics.json")
    thresholds = read_json(eval_dir / "ieee118_n1_gated_thresholds.json")
    rows = []
    for method, variant in ((METHOD_PATH, "path_prob"), (METHOD_SECOND, "second_only")):
        threshold = threshold_row(thresholds, method)
        rows.append(
            {
                "dataset": label,
                "state_samples": int(metrics["num_state_samples"]),
                "train_state_samples": int(metrics["num_train_state_samples"]),
                "validation_state_samples": int(metrics["num_validation_state_samples"]),
                "test_state_samples": int(metrics["num_test_state_samples"]),
                "k_gcn": int(metrics["train_config"]["k_gcn"]),
                "ranking_variant": variant,
                "best_epoch": int(metrics["best_epoch"]),
                "validation_average_precision": float(metrics["best_validation_average_precision"]),
                "test_average_precision": float(metrics["classification_metrics"]["test"]["average_precision"]),
                "s0_average_precision": float(metrics["classification_metrics"]["S0"]["average_precision"]),
                "s1_average_precision": float(metrics["classification_metrics"]["S1"]["average_precision"]),
                **{
                    key: threshold[key]
                    for key in (
                        "K90",
                        "K95",
                        "K99",
                        "K100",
                        "total_physical_K90",
                        "total_physical_K95",
                        "total_physical_K99",
                        "total_physical_K100",
                    )
                },
            }
        )
    summary_path = eval_dir / "ieee118_n1_gated_search_summary.csv"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing residual scale-up comparison input: {summary_path}")
    budget = pd.read_csv(summary_path)
    budget = budget.loc[budget["method"].isin([METHOD_PATH, METHOD_SECOND]) & budget["K"].isin(KEY_BUDGETS)].copy()
    budget.insert(0, "dataset", label)
    return rows, budget, metrics


def compare(args: argparse.Namespace) -> dict[str, Any]:
    pilot_rows, pilot_budget, pilot_metrics = load_run(args.pilot_root, "pilot_2000")
    scale_rows, scale_budget, scale_metrics = load_run(args.scaleup_root, "paper_8000")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    thresholds = pd.DataFrame(pilot_rows + scale_rows)
    budgets = pd.concat([pilot_budget, scale_budget], ignore_index=True, sort=False)
    thresholds.to_csv(args.output_dir / "ieee118_paper8000_vs_pilot2000_thresholds.csv", index=False, encoding="utf-8-sig")
    budgets.to_csv(args.output_dir / "ieee118_paper8000_vs_pilot2000_key_budgets.csv", index=False, encoding="utf-8-sig")

    result: dict[str, Any] = {
        "status": "complete",
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "k_gcn": 6,
        "pilot_state_samples": int(pilot_metrics["num_state_samples"]),
        "paper8000_state_samples": int(scale_metrics["num_state_samples"]),
        "checkpoint_selection": "maximum validation average precision",
        "comparison": thresholds.to_dict("records"),
        "large_artifacts_tracked_in_git": False,
    }
    for variant in ("path_prob", "second_only"):
        pilot = thresholds.loc[
            thresholds["dataset"].eq("pilot_2000") & thresholds["ranking_variant"].eq(variant)
        ].iloc[0]
        scale = thresholds.loc[
            thresholds["dataset"].eq("paper_8000") & thresholds["ranking_variant"].eq(variant)
        ].iloc[0]
        result[f"{variant}_delta"] = {
            "validation_average_precision": float(
                scale["validation_average_precision"] - pilot["validation_average_precision"]
            ),
            "test_average_precision": float(scale["test_average_precision"] - pilot["test_average_precision"]),
            "total_physical_K90": float(scale["total_physical_K90"] - pilot["total_physical_K90"]),
            "total_physical_K95": float(scale["total_physical_K95"] - pilot["total_physical_K95"]),
            "total_physical_K99": float(scale["total_physical_K99"] - pilot["total_physical_K99"]),
        }
    (args.output_dir / "ieee118_paper8000_vs_pilot2000_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    pilot_path = thresholds.loc[
        thresholds["dataset"].eq("pilot_2000") & thresholds["ranking_variant"].eq("path_prob")
    ].iloc[0]
    scale_path = thresholds.loc[
        thresholds["dataset"].eq("paper_8000") & thresholds["ranking_variant"].eq("path_prob")
    ].iloc[0]
    (args.output_dir / "ieee118_paper8000_vs_pilot2000_readme.md").write_text(
        "# IEEE118 Residual-Reachable Scale-Up Comparison\n\n"
        "This compact comparison holds the original RTS-79 `PaperStyleRts79Gcn`, `k_gcn=6`, loss, truth, and "
        "N-1-gated evaluation protocol fixed. Only multi-seed training-state volume changes from 2,000 to 8,000. "
        "`path_prob` is the primary ranking; `second_only` remains a diagnostic ablation.\n\n"
        "| Dataset | Test AP | Total physical K90 | K95 | K99 |\n"
        "|---|---:|---:|---:|---:|\n"
        f"| pilot-2000 | {pilot_path['test_average_precision']:.4f} | "
        f"{int(pilot_path['total_physical_K90']):,} | {int(pilot_path['total_physical_K95']):,} | "
        f"{int(pilot_path['total_physical_K99']):,} |\n"
        f"| paper-8000 | {scale_path['test_average_precision']:.4f} | "
        f"{int(scale_path['total_physical_K90']):,} | {int(scale_path['total_physical_K95']):,} | "
        f"{int(scale_path['total_physical_K99']):,} |\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    args = parse_args()
    print(json.dumps(compare(args), indent=2))


if __name__ == "__main__":
    main()
