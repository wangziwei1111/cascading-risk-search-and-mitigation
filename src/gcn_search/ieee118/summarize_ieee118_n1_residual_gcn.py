from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN_ROOT = ROOT / "results" / "gcn_search" / "ieee118_n1_residual_reachable_gcn"
DEFAULT_OUTPUT = DEFAULT_RUN_ROOT / "compact"
GCN_PATH = "N1_gate_plus_RTS79_residual_reachable_GCN_path_prob"
GCN_SECOND = "N1_gate_plus_RTS79_residual_reachable_GCN_second_only"
COMPARISON_METHODS = [
    GCN_SECOND,
    GCN_PATH,
    "N1_gate_plus_LODF_yP",
    "N1_gate_plus_line_order",
    "N1_gate_plus_random",
    "LODF_yP",
    "line_order",
    "random",
]
COMPARISON_BUDGETS = [100, 500, 1000, 2000, 3000, 5000]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize the IEEE118 N-1 residual-reachable GCN pilot sweep.")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--k-values", type=int, nargs="+", default=[3, 5, 6, 8])
    parser.add_argument("--selected-k", type=int, default=None)
    return parser.parse_args(argv)


def read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing compact-summary input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def threshold_for(rows: list[dict[str, Any]], method: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("method") == method and row.get("universe") == "full"]
    if len(matches) != 1:
        raise ValueError(f"Expected one full-universe threshold row for {method}, found {len(matches)}.")
    return matches[0]


def build_k_sweep(run_root: Path, k_values: list[int]) -> pd.DataFrame:
    rows = []
    for k in k_values:
        train_dir = run_root / f"training_k{k}"
        eval_dir = run_root / f"eval_k{k}"
        metrics = read_json(train_dir / f"ieee118_residual_reachable_gcn_k{k}_metrics.json")
        thresholds = read_json(eval_dir / "ieee118_n1_gated_thresholds.json")
        for method in (GCN_PATH, GCN_SECOND):
            threshold = threshold_for(thresholds, method)
            rows.append(
                {
                    "k_gcn": int(k),
                    "effective_two_layer_max_hops": int(metrics["effective_two_layer_max_hops"]),
                    "ranking_variant": "path_prob" if method == GCN_PATH else "second_only",
                    "best_epoch": int(metrics["best_epoch"]),
                    "best_validation_average_precision": float(metrics["best_validation_average_precision"]),
                    "test_average_precision": float(metrics["classification_metrics"]["test"]["average_precision"]),
                    "s0_average_precision": float(metrics["classification_metrics"]["S0"]["average_precision"]),
                    "s1_average_precision": float(metrics["classification_metrics"]["S1"]["average_precision"]),
                    "K90": int(threshold["K90"]),
                    "K95": int(threshold["K95"]),
                    "K99": int(threshold["K99"]),
                    "K100": int(threshold["K100"]),
                    "total_physical_K90": int(threshold["total_physical_K90"]),
                    "total_physical_K95": int(threshold["total_physical_K95"]),
                    "total_physical_K99": int(threshold["total_physical_K99"]),
                    "total_physical_K100": int(threshold["total_physical_K100"]),
                }
            )
    return pd.DataFrame(rows).sort_values(["k_gcn", "ranking_variant"]).reset_index(drop=True)


def build_method_comparison(run_root: Path, selected_k: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eval_dir = run_root / f"eval_k{selected_k}"
    summary = pd.read_csv(eval_dir / "ieee118_n1_gated_search_summary.csv")
    comparison = summary.loc[
        summary["method"].isin(COMPARISON_METHODS) & summary["K"].isin(COMPARISON_BUDGETS)
    ].copy()
    comparison = comparison.sort_values(["K", "method"]).reset_index(drop=True)

    thresholds = pd.DataFrame(read_json(eval_dir / "ieee118_n1_gated_thresholds.json"))
    thresholds = thresholds.loc[thresholds["method"].isin(COMPARISON_METHODS)].copy()
    threshold_columns = [
        "method",
        "K90",
        "K90_std",
        "total_physical_K90",
        "total_physical_K90_std",
        "K95",
        "total_physical_K95",
        "K99",
        "total_physical_K99",
        "K100",
        "total_physical_K100",
    ]
    for column in threshold_columns:
        if column not in thresholds:
            thresholds[column] = pd.NA
    thresholds = thresholds[threshold_columns].sort_values("total_physical_K90").reset_index(drop=True)

    curve = pd.read_csv(eval_dir / "ieee118_n1_gated_curve_points.csv")
    curve = curve.loc[curve["method"].isin(COMPARISON_METHODS)].copy()
    curve = curve.sort_values(["method", "candidate_evaluations"]).reset_index(drop=True)
    return comparison, thresholds, curve


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sweep = build_k_sweep(args.run_root, args.k_values)
    validation_by_k = sweep.groupby("k_gcn", as_index=False)["best_validation_average_precision"].first()
    selected_k = int(
        args.selected_k
        if args.selected_k is not None
        else validation_by_k.sort_values(
            ["best_validation_average_precision", "k_gcn"], ascending=[False, True]
        ).iloc[0]["k_gcn"]
    )
    comparison, thresholds, curve = build_method_comparison(args.run_root, selected_k)

    sweep.to_csv(args.output_dir / "ieee118_residual_reachable_k_sweep.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(args.output_dir / "ieee118_n1_gated_method_comparison.csv", index=False, encoding="utf-8-sig")
    thresholds.to_csv(args.output_dir / "ieee118_n1_gated_threshold_comparison.csv", index=False, encoding="utf-8-sig")
    curve.to_csv(args.output_dir / "ieee118_n1_gated_curve_points.csv", index=False, encoding="utf-8-sig")

    selected_threshold_rows = read_json(
        args.run_root / f"eval_k{selected_k}" / "ieee118_n1_gated_thresholds.json"
    )
    selected = threshold_for(selected_threshold_rows, GCN_SECOND)
    selected_path = threshold_for(selected_threshold_rows, GCN_PATH)
    result = {
        "status": "complete",
        "experiment_scope": "pilot_2000_state_samples",
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "checkpoint_selection": "maximum validation average precision",
        "selected_k_gcn": selected_k,
        "selected_effective_two_layer_max_hops": 2 * selected_k,
        "num_valid_ordered_n2_paths": int(selected["total_paths"]),
        "num_critical_paths": int(selected["total_critical"]),
        "n1_prescreen_evaluations": int(selected["n1_prescreen_evaluations"]),
        "primary_protocol_method": GCN_PATH,
        "primary_path_probability_thresholds": {
            key: selected_path[key]
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
        "diagnostic_ablation_method": GCN_SECOND,
        "selected_second_only_thresholds": {
            key: selected[key]
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
        "rts79_reference_searches_per_critical": 68.2 / 56.6,
        "ieee118_primary_total_physical_K90_per_critical": selected_path["total_physical_K90"]
        / selected_path["total_critical"],
        "ieee118_total_physical_K90_per_critical": selected["total_physical_K90"] / selected["total_critical"],
        "large_training_artifacts_tracked_in_git": False,
        "final_paper_claim_permitted": False,
    }
    (args.output_dir / "ieee118_n1_residual_reachable_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    (args.output_dir / "ieee118_n1_residual_reachable_readme.md").write_text(
        "# IEEE118 N-1-Gated Residual-Reachable GCN Pilot\n\n"
        "This compact artifact uses the original RTS-79 `PaperStyleRts79Gcn`; the model core is unchanged. "
        "The selected graph radius is based on validation AP, not the held-out test thresholds.\n\n"
        f"- Selected `k_gcn`: {selected_k} (effective maximum about {2 * selected_k} hops)\n"
        f"- Critical paths: {selected['total_critical']} of {selected['total_paths']}\n"
        f"- N-1 prescreen: {selected['n1_prescreen_evaluations']} physical evaluations\n"
        f"- Primary path-probability total physical K90/K95/K99: {selected_path['total_physical_K90']} / "
        f"{selected_path['total_physical_K95']} / {selected_path['total_physical_K99']}\n"
        f"- Second-only ablation total physical K90/K95/K99: {selected['total_physical_K90']} / "
        f"{selected['total_physical_K95']} / {selected['total_physical_K99']}\n\n"
        "These are pilot-2000 results, not final full-scale training results and not a claim that all critical paths "
        "are found near K90. Large NPZs, checkpoints, and full predictions remain local.\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    args = parse_args()
    print(json.dumps(summarize(args), indent=2))


if __name__ == "__main__":
    main()
