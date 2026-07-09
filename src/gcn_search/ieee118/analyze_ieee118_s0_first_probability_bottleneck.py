from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_ieee118_rts79_protocol_search import (
    load_truth,
    make_path_score_table,
    predict_s1_probabilities,
)


DEFAULT_BASE = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup"
DEFAULT_EVAL = DEFAULT_BASE / "pilot_2000_eval"
DEFAULT_TRAIN = DEFAULT_BASE / "pilot_2000"
DEFAULT_ORIGINAL = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"
DEFAULT_FULLTRUTH = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose IEEE118 S0 first-probability bottleneck.")
    parser.add_argument("--fulltruth-csv", type=Path, default=DEFAULT_FULLTRUTH / "ieee118_fulltruth_summary.csv")
    parser.add_argument("--path-index-csv", type=Path, default=DEFAULT_ORIGINAL / "ieee118_rts79_gcn_path_index.csv")
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_ORIGINAL / "ieee118_rts79_gcn_dataset.npz")
    parser.add_argument("--model-path", type=Path, default=DEFAULT_TRAIN / "ieee118_paper_gcn_model.pt")
    parser.add_argument("--feature-normalizer-json", type=Path, default=DEFAULT_TRAIN / "ieee118_paper_gcn_feature_normalizer.json")
    parser.add_argument("--first-step-probabilities-csv", type=Path, default=DEFAULT_EVAL / "ieee118_paper_aligned_pilot2000_first_step_probabilities.csv")
    parser.add_argument("--search-summary-csv", type=Path, default=DEFAULT_EVAL / "ieee118_paper_aligned_pilot2000_search_summary.csv")
    parser.add_argument("--topk-paths-csv", type=Path, default=DEFAULT_EVAL / "ieee118_paper_aligned_pilot2000_topk_paths.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_BASE / "s0_bottleneck_diagnostics")
    parser.add_argument("--eval-seed", type=int, default=20260708)
    parser.add_argument("--k-values", type=int, nargs="+", default=[100, 500, 1000, 2000, 5000, 10000])
    parser.add_argument("--suppressed-second-rank", type=int, default=1000)
    parser.add_argument("--suppressed-path-rank", type=int, default=5000)
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label}: {path}. This diagnostic reads local PR #14 pilot-2000 artifacts "
            "and will not regenerate OPA full-truth, NPZ datasets, or model checkpoints."
        )


def coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def rank_score_table(score: pd.DataFrame) -> pd.DataFrame:
    ranked = score.copy()
    ranked = ranked.sort_values(["path_product_score", "p_shed_first", "p_shed_second", "path"], ascending=[False, False, False, True])
    ranked["path_prob_rank"] = np.arange(1, len(ranked) + 1)
    path_rank = ranked[["path", "path_prob_rank"]]
    second_rank = score.sort_values(["p_shed_second", "path"], ascending=[False, True]).copy()
    second_rank["second_only_rank"] = np.arange(1, len(second_rank) + 1)
    out = score.merge(path_rank, on="path", how="left").merge(second_rank[["path", "second_only_rank"]], on="path", how="left")
    out["rank_gap"] = out["path_prob_rank"] - out["second_only_rank"]
    out["path_prob_score"] = out["path_product_score"]
    out["second_only_score"] = out["p_shed_second"]
    return out


def suppressed_masks(
    score: pd.DataFrame,
    *,
    class_a_second_rank: int = 1000,
    class_a_path_rank: int = 5000,
    class_b_second_rank: int = 5000,
    class_b_path_rank: int = 10000,
) -> tuple[pd.Series, pd.Series]:
    critical = coerce_bool(score["critical"])
    suppressed_a = critical & score["second_only_rank"].le(class_a_second_rank) & score["path_prob_rank"].gt(class_a_path_rank)
    suppressed_b = critical & score["second_only_rank"].le(class_b_second_rank) & score["path_prob_rank"].gt(class_b_path_rank)
    return suppressed_a, suppressed_b


def quantile(series: pd.Series, q: float) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return 0.0
    return float(numeric.quantile(q))


def distribution_row(name: str, group: pd.DataFrame) -> dict[str, Any]:
    return {
        "subset": name,
        "count": int(len(group)),
        "mean_p_first": float(group["p_shed_first"].mean()) if len(group) else 0.0,
        "median_p_first": float(group["p_shed_first"].median()) if len(group) else 0.0,
        "p05_p_first": quantile(group["p_shed_first"], 0.05),
        "p10_p_first": quantile(group["p_shed_first"], 0.10),
        "p25_p_first": quantile(group["p_shed_first"], 0.25),
        "p75_p_first": quantile(group["p_shed_first"], 0.75),
        "p90_p_first": quantile(group["p_shed_first"], 0.90),
        "p95_p_first": quantile(group["p_shed_first"], 0.95),
        "mean_p_second": float(group["p_shed_second"].mean()) if len(group) else 0.0,
        "median_p_second": float(group["p_shed_second"].median()) if len(group) else 0.0,
        "mean_path_prob_score": float(group["path_prob_score"].mean()) if len(group) else 0.0,
        "median_path_prob_score": float(group["path_prob_score"].median()) if len(group) else 0.0,
    }


def build_probability_distribution(score: pd.DataFrame, suppressed_a: pd.Series, suppressed_b: pd.Series) -> pd.DataFrame:
    critical = coerce_bool(score["critical"])
    relay = coerce_bool(score["relay_cascade"])
    mechanism = score["critical_mechanism"].fillna("").astype(str)
    rows = [
        distribution_row("all_valid_n2_paths", score),
        distribution_row("all_critical_valid_n2_paths", score.loc[critical]),
        distribution_row("relay_cascade_critical_paths", score.loc[critical & relay]),
        distribution_row("island_only_critical_paths", score.loc[critical & mechanism.eq("island_only")]),
        distribution_row("path_prob_top1000_critical", score.loc[critical & score["path_prob_rank"].le(1000)]),
        distribution_row("second_only_top1000_critical", score.loc[critical & score["second_only_rank"].le(1000)]),
        distribution_row("suppressed_critical_A", score.loc[suppressed_a]),
        distribution_row("suppressed_critical_B", score.loc[suppressed_b]),
        distribution_row("noncritical_paths", score.loc[~critical]),
    ]
    return pd.DataFrame(rows)


def aggregate_first_line_suppression(score: pd.DataFrame, suppressed: pd.Series) -> pd.DataFrame:
    subset = score.loc[suppressed].copy()
    rows = []
    for first_line, group in subset.groupby("first_line", sort=False):
        mechanisms = group["critical_mechanism"].fillna("unknown").astype(str).value_counts().to_dict()
        relay = coerce_bool(group["relay_cascade"])
        rows.append(
            {
                "first_line": first_line,
                "num_suppressed_critical": int(len(group)),
                "num_suppressed_relay": int(relay.sum()),
                "mean_p_first": float(group["p_shed_first"].mean()),
                "median_p_first": float(group["p_shed_first"].median()),
                "p10_p_first": quantile(group["p_shed_first"], 0.10),
                "p90_p_first": quantile(group["p_shed_first"], 0.90),
                "mean_p_second": float(group["p_shed_second"].mean()),
                "median_p_second": float(group["p_shed_second"].median()),
                "mean_rank_gap": float(group["rank_gap"].mean()),
                "max_rank_gap": int(group["rank_gap"].max()),
                "max_total_load_shed_mw": float(group["total_load_shed_mw"].max()),
                "representative_paths": ";".join(group.sort_values("rank_gap", ascending=False)["path"].head(5).astype(str)),
                "representative_second_lines": ";".join(group.sort_values("rank_gap", ascending=False)["second_line"].head(5).astype(str)),
                "relay_cascade_ratio": float(relay.mean()) if len(group) else 0.0,
                "mechanism_distribution": json.dumps(mechanisms, sort_keys=True),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "first_line",
                "num_suppressed_critical",
                "num_suppressed_relay",
                "mean_p_first",
                "median_p_first",
                "p10_p_first",
                "p90_p_first",
                "mean_p_second",
                "median_p_second",
                "mean_rank_gap",
                "max_rank_gap",
                "max_total_load_shed_mw",
                "representative_paths",
                "representative_second_lines",
                "relay_cascade_ratio",
                "mechanism_distribution",
            ]
        )
    return pd.DataFrame(rows).sort_values(["num_suppressed_critical", "mean_rank_gap"], ascending=[False, False])


def topk_overlap(score: pd.DataFrame, k_values: list[int]) -> pd.DataFrame:
    rows = []
    for k in k_values:
        path_top = set(score.nsmallest(k, "path_prob_rank")["path"].astype(str))
        second_top = set(score.nsmallest(k, "second_only_rank")["path"].astype(str))
        overlap = path_top & second_top
        path_only = path_top - second_top
        second_only = second_top - path_top
        path_only_df = score.loc[score["path"].isin(path_only)]
        second_only_df = score.loc[score["path"].isin(second_only)]
        rows.append(
            {
                "K": int(k),
                "overlap_count": int(len(overlap)),
                "overlap_ratio": len(overlap) / max(k, 1),
                "path_prob_only_count": int(len(path_only)),
                "second_only_only_count": int(len(second_only)),
                "path_prob_only_critical_hits": int(coerce_bool(path_only_df["critical"]).sum()) if len(path_only_df) else 0,
                "second_only_only_critical_hits": int(coerce_bool(second_only_df["critical"]).sum()) if len(second_only_df) else 0,
                "path_prob_only_relay_hits": int(coerce_bool(path_only_df["relay_cascade"]).sum()) if len(path_only_df) else 0,
                "second_only_only_relay_hits": int(coerce_bool(second_only_df["relay_cascade"]).sum()) if len(second_only_df) else 0,
                "path_prob_only_mean_p_first": float(path_only_df["p_shed_first"].mean()) if len(path_only_df) else 0.0,
                "second_only_only_mean_p_first": float(second_only_df["p_shed_first"].mean()) if len(second_only_df) else 0.0,
                "path_prob_only_mean_p_second": float(path_only_df["p_shed_second"].mean()) if len(path_only_df) else 0.0,
                "second_only_only_mean_p_second": float(second_only_df["p_shed_second"].mean()) if len(second_only_df) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def s0_label_conflict_summary(score: pd.DataFrame, first_step_summary_csv: Path, first_prob_csv: Path) -> pd.DataFrame:
    first_prob = pd.read_csv(first_prob_csv)
    p_first = {str(row["line_label"]): float(row["p_shed_first"]) for _, row in first_prob.iterrows()}
    if first_step_summary_csv.exists():
        first = pd.read_csv(first_step_summary_csv)
        first["first_step_critical"] = coerce_bool(first["first_step_critical"])
        first_critical = set(first.loc[first["first_step_critical"], "first_line"].astype(str))
    else:
        first_critical = set()
    valid_first = set(score["first_line"].astype(str))
    critical = coerce_bool(score["critical"])
    valid_critical_first = set(score.loc[critical, "first_line"].astype(str))
    valid_noncritical_first = set(score.loc[~critical, "first_line"].astype(str))

    def mean_for(labels: set[str]) -> float:
        vals = [p_first[label] for label in labels if label in p_first]
        return float(np.mean(vals)) if vals else 0.0

    positive_label_paths = score["first_line"].isin(first_critical)
    row = {
        "num_total_first_lines": int(len(p_first)),
        "num_first_step_critical_lines": int(len(first_critical)),
        "num_valid_n2_first_lines": int(len(valid_first)),
        "num_valid_n2_paths": int(len(score)),
        "num_valid_n2_paths_with_first_step_positive_label": int(positive_label_paths.sum()),
        "num_valid_n2_paths_with_first_step_negative_label": int((~positive_label_paths).sum()),
        "mean_p_first_for_valid_n2_first_lines": mean_for(valid_first),
        "mean_p_first_for_first_step_critical_lines": mean_for(first_critical),
        "mean_p_first_for_valid_critical_n2_first_lines": mean_for(valid_critical_first),
        "mean_p_first_for_valid_noncritical_n2_first_lines": mean_for(valid_noncritical_first),
    }
    return pd.DataFrame([row])


def mechanism_summary(score: pd.DataFrame, suppressed: pd.Series) -> pd.DataFrame:
    df = score.copy()
    critical = coerce_bool(df["critical"])
    df["mechanism_group"] = np.where(critical, df["critical_mechanism"].fillna("unknown").astype(str), "noncritical")
    df["mechanism_group"] = df["mechanism_group"].replace({"": "unknown"})
    df["suppressed"] = suppressed
    rows = []
    for mechanism, group in df.groupby("mechanism_group", sort=False):
        group_critical = coerce_bool(group["critical"])
        rows.append(
            {
                "mechanism": mechanism,
                "num_paths": int(len(group)),
                "num_critical": int(group_critical.sum()),
                "mean_p_first": float(group["p_shed_first"].mean()),
                "median_p_first": float(group["p_shed_first"].median()),
                "mean_p_second": float(group["p_shed_second"].mean()),
                "median_p_second": float(group["p_shed_second"].median()),
                "path_prob_top1000_hits": int((group_critical & group["path_prob_rank"].le(1000)).sum()),
                "second_only_top1000_hits": int((group_critical & group["second_only_rank"].le(1000)).sum()),
                "suppressed_count": int(group["suppressed"].sum()),
                "suppressed_ratio": float(group["suppressed"].mean()) if len(group) else 0.0,
                "mean_rank_gap": float(group["rank_gap"].mean()),
            }
        )
    return pd.DataFrame(rows)


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_ready(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if pd.isna(value) if not isinstance(value, (list, dict, str, bytes)) else False:
        return None
    return value


def run_diagnostics(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path, label in [
        (args.fulltruth_csv, "full-truth CSV"),
        (args.path_index_csv, "path index CSV"),
        (args.dataset_npz, "dataset NPZ"),
        (args.model_path, "paper-aligned model checkpoint"),
        (args.feature_normalizer_json, "feature normalizer JSON"),
        (args.first_step_probabilities_csv, "first-step probabilities CSV"),
        (args.search_summary_csv, "search summary CSV"),
        (args.topk_paths_csv, "top-K paths CSV"),
    ]:
        require_file(path, label)

    truth = load_truth(args.fulltruth_csv)
    s1_probability, _ = predict_s1_probabilities(args.dataset_npz, args.model_path, args.feature_normalizer_json)
    score = make_path_score_table(args.path_index_csv, args.first_step_probabilities_csv, s1_probability, truth)
    extra_cols = [
        col
        for col in ["path", "critical_mechanism", "relay_trip_labels", "final_outage_labels", "first_step_critical", "valid_ordered_n2"]
        if col in truth.columns
    ]
    score = score.merge(truth[extra_cols].drop_duplicates("path"), on="path", how="left")
    score = rank_score_table(score)
    suppressed_a, suppressed_b = suppressed_masks(
        score,
        class_a_second_rank=args.suppressed_second_rank,
        class_a_path_rank=args.suppressed_path_rank,
    )
    suppressed_any = suppressed_a | suppressed_b

    columns = [
        "path",
        "first_line",
        "second_line",
        "critical",
        "relay_cascade",
        "total_load_shed_mw",
        "critical_mechanism",
        "p_shed_first",
        "p_shed_second",
        "path_prob_score",
        "second_only_score",
        "path_prob_rank",
        "second_only_rank",
        "rank_gap",
        "relay_trip_labels",
        "final_outage_labels",
        "full_cascade_path",
    ]
    suppressed_top = score.loc[suppressed_any, [col for col in columns if col in score.columns]].sort_values("rank_gap", ascending=False).head(500)
    suppressed_top.to_csv(args.output_dir / "suppressed_critical_paths_top.csv", index=False, encoding="utf-8-sig")

    first_line_summary = aggregate_first_line_suppression(score, suppressed_any)
    first_line_summary.to_csv(args.output_dir / "first_line_s0_suppression_summary.csv", index=False, encoding="utf-8-sig")
    distribution = build_probability_distribution(score, suppressed_a, suppressed_b)
    distribution.to_csv(args.output_dir / "s0_probability_distribution_summary.csv", index=False, encoding="utf-8-sig")
    conflict = s0_label_conflict_summary(score, args.fulltruth_csv.with_name("ieee118_first_step_summary.csv"), args.first_step_probabilities_csv)
    conflict.to_csv(args.output_dir / "s0_label_conflict_summary.csv", index=False, encoding="utf-8-sig")
    overlap = topk_overlap(score, args.k_values)
    overlap.to_csv(args.output_dir / "path_prob_vs_second_only_overlap.csv", index=False, encoding="utf-8-sig")
    mechanisms = mechanism_summary(score, suppressed_any)
    mechanisms.to_csv(args.output_dir / "mechanism_s0_bottleneck_summary.csv", index=False, encoding="utf-8-sig")

    local_full_score = args.output_dir / "s0_bottleneck_full_score_table_local_only.csv"
    score.to_csv(local_full_score, index=False, encoding="utf-8-sig")

    search_summary = pd.read_csv(args.search_summary_csv)
    at_1000 = search_summary.loc[search_summary["K"].eq(1000)]
    method_metrics = {
        str(row["method"]): {
            "critical_hit_count": float(row["critical_hit_count"]),
            "recall_critical": float(row["recall_critical"]),
            "precision_at_k": float(row["precision_at_k"]),
        }
        for _, row in at_1000.iterrows()
    }
    top_first = first_line_summary.head(10).to_dict("records")
    overlap_1000 = overlap.loc[overlap["K"].eq(1000)].to_dict("records")
    overlap_5000 = overlap.loc[overlap["K"].eq(5000)].to_dict("records")
    summary = {
        "input_paths": {
            "fulltruth_csv": str(args.fulltruth_csv),
            "path_index_csv": str(args.path_index_csv),
            "dataset_npz": str(args.dataset_npz),
            "model_path": str(args.model_path),
            "feature_normalizer_json": str(args.feature_normalizer_json),
            "first_step_probabilities_csv": str(args.first_step_probabilities_csv),
            "search_summary_csv": str(args.search_summary_csv),
            "topk_paths_csv": str(args.topk_paths_csv),
        },
        "model_name": "PaperStyleRts79Gcn",
        "dataset_name": "IEEE118 flow_scaled=8.0 paper-aligned pilot-2000",
        "eval_seed": int(args.eval_seed),
        "num_valid_n2_paths": int(len(score)),
        "num_critical_paths": int(coerce_bool(score["critical"]).sum()),
        "num_relay_cascade_paths": int(coerce_bool(score["relay_cascade"]).sum()),
        "num_first_step_critical_lines": int(conflict["num_first_step_critical_lines"].iloc[0]),
        "main_findings": [
            "second_only finds many high-risk paths with high p_second but low p_first.",
            "first-step early-stop makes valid ordered N-2 first lines mostly S0-negative by construction.",
            "p_shed(Li|S0) estimates direct first-step load-shed risk, not the ability of Li to create a fragile S1 state.",
        ],
        "top_level_metrics": method_metrics,
        "suppressed_critical_counts": {
            "class_A_second_rank_le_1000_path_rank_gt_5000": int(suppressed_a.sum()),
            "class_B_second_rank_le_5000_path_rank_gt_10000": int(suppressed_b.sum()),
            "union": int(suppressed_any.sum()),
        },
        "top_suppressed_first_lines": top_first,
        "path_prob_vs_second_only_overlap_at_1000": overlap_1000[0] if overlap_1000 else {},
        "path_prob_vs_second_only_overlap_at_5000": overlap_5000[0] if overlap_5000 else {},
        "s0_label_conflict_summary": conflict.iloc[0].to_dict(),
        "mechanism_summary": mechanisms.to_dict("records"),
        "interpretation": (
            "Under first-step critical early-stop, valid ordered N-2 rows exclude first lines that already shed load in S0. "
            "The learned p_first is therefore a direct N-1 load-shed probability and can suppress lines that are safe in S0 "
            "but create fragile S1 states with high second-step risk."
        ),
        "recommended_next_steps": [
            "Report strict path_prob as the paper-aligned method and second_only as an ablation.",
            "Discuss S0 fragility mismatch rather than treating second_only superiority as a bug.",
            "If changing methods later, evaluate a separate S0 fragility target in a dedicated PR.",
        ],
        "local_only_full_score_table": str(local_full_score),
        "large_artifacts_tracked": False,
    }
    (args.output_dir / "s0_first_probability_bottleneck_diagnostics.json").write_text(
        json.dumps(json_ready(summary), indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "s0_first_probability_bottleneck_readme.md").write_text(
        "# IEEE118 S0 First-Probability Bottleneck Diagnostics\n\n"
        "This diagnostic analyzes the PR #14 pilot-2000 paper-aligned model outputs. It does not rerun OPA, "
        "change the model, or change search ordering formulas. The full score table is local-only; committed "
        "outputs are compact CSV/JSON summaries.\n\n"
        f"- Valid N-2 paths: {len(score)}\n"
        f"- Critical paths: {int(coerce_bool(score['critical']).sum())}\n"
        f"- Suppressed critical paths, union: {int(suppressed_any.sum())}\n"
        f"- Class A: {int(suppressed_a.sum())}\n"
        f"- Class B: {int(suppressed_b.sum())}\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    args = parse_args()
    print(json.dumps(json_ready(run_diagnostics(args)), indent=2))


if __name__ == "__main__":
    main()
