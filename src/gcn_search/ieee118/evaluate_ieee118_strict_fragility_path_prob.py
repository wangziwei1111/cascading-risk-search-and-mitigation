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

from evaluate_ieee118_alpha_path_prob_sweep import (
    DEFAULT_BASE,
    DEFAULT_SCORE_TABLE,
    build_score_table,
    coerce_bool,
    make_budget_table,
    ranked_by_score,
    write_json,
)


DEFAULT_STRICT = DEFAULT_BASE / "strict_fragility_targets"
DEFAULT_STRICT_EVAL = DEFAULT_BASE / "strict_fragility_eval"
DEFAULT_ALPHA = DEFAULT_BASE / "alpha_path_prob_sweep"
DEFAULT_ANY = DEFAULT_BASE / "first_line_fragility_eval"
DEFAULT_FULLTRUTH = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
DEFAULT_PATH_INDEX = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate strict IEEE118 first-line fragility path-probability rankings.")
    parser.add_argument("--fulltruth-csv", type=Path, default=DEFAULT_FULLTRUTH / "ieee118_fulltruth_summary.csv")
    parser.add_argument("--path-index-csv", type=Path, default=DEFAULT_PATH_INDEX / "ieee118_rts79_gcn_path_index.csv")
    parser.add_argument("--s1-score-table-csv", type=Path, default=DEFAULT_SCORE_TABLE)
    parser.add_argument("--strict-fragility-probabilities-csv", type=Path, default=DEFAULT_STRICT / "ieee118_strict_fragility_probabilities_compact.csv")
    parser.add_argument("--first-step-probabilities-csv", type=Path, default=DEFAULT_BASE / "pilot_2000_eval" / "ieee118_paper_aligned_pilot2000_first_step_probabilities.csv")
    parser.add_argument("--alpha-sweep-summary-csv", type=Path, default=DEFAULT_ALPHA / "alpha_path_prob_sweep_summary.csv")
    parser.add_argument("--fragility-eval-summary-csv", type=Path, default=DEFAULT_ANY / "ieee118_fragility_path_prob_summary.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_STRICT_EVAL)
    parser.add_argument("--k-values", type=int, nargs="+", default=[100, 500, 1000, 2000, 5000, 10000])
    parser.add_argument("--ratio-k-values", type=float, nargs="+", default=[0.005, 0.01, 0.02, 0.05, 0.10])
    parser.add_argument("--alpha-values", type=float, nargs="*", default=[0.25, 0.5, 0.75, 1.0])
    parser.add_argument("--epsilon-values", type=float, nargs="*", default=[1e-3, 1e-2])
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}. This evaluator will not rerun OPA or regenerate full score tables.")


def evaluate_ranked(method: str, ranked: pd.DataFrame, budgets: pd.DataFrame, *, target_mode: str = "", top_quantile: float | None = None, alpha: float | None = None, epsilon: float | None = None) -> pd.DataFrame:
    total_critical = int(ranked["critical"].sum())
    total_relay = int(ranked["relay_cascade"].sum())
    total_shed = float(ranked["total_load_shed_mw"].sum())
    rows = []
    for _, budget in budgets.iterrows():
        k = int(budget["K"])
        top = ranked.head(k)
        critical_hits = int(top["critical"].sum())
        relay_hits = int(top["relay_cascade"].sum())
        low_high = top[top["critical"] & top["p_shed_first"].lt(0.05) & top["p_shed_second"].gt(0.8)]
        high_q_high_p = top[top["critical"] & top["q_strict_fragile"].gt(0.5) & top["p_shed_second"].gt(0.8)]
        high_q_relay = top[top["relay_cascade"] & top["q_strict_fragile"].gt(0.5)]
        rows.append(
            {
                "method": method,
                "target_mode": target_mode,
                "top_quantile": top_quantile,
                "alpha": alpha,
                "epsilon": epsilon,
                "budget_type": budget["budget_type"],
                "budget_label": budget["budget_label"],
                "K": k,
                "search_budget_ratio": float(budget["search_budget_ratio"]),
                "critical_hit_count": critical_hits,
                "relay_cascade_hit_count": relay_hits,
                "recall_critical": critical_hits / max(total_critical, 1),
                "recall_relay_cascade": relay_hits / max(total_relay, 1),
                "precision_at_k": critical_hits / max(k, 1),
                "captured_total_load_shed_mw": float(top["total_load_shed_mw"].sum()),
                "captured_total_load_shed_ratio": float(top["total_load_shed_mw"].sum()) / max(total_shed, 1e-12),
                "mean_q_strict_topk": float(top["q_strict_fragile"].mean()) if len(top) else 0.0,
                "median_q_strict_topk": float(top["q_strict_fragile"].median()) if len(top) else 0.0,
                "mean_p_first_topk": float(top["p_shed_first"].mean()) if len(top) else 0.0,
                "median_p_first_topk": float(top["p_shed_first"].median()) if len(top) else 0.0,
                "mean_p_second_topk": float(top["p_shed_second"].mean()) if len(top) else 0.0,
                "median_p_second_topk": float(top["p_shed_second"].median()) if len(top) else 0.0,
                "num_low_p_first_high_p_second_hits": int(len(low_high)),
                "num_high_q_high_p_second_hits": int(len(high_q_high_p)),
                "num_high_q_relay_hits": int(len(high_q_relay)),
            }
        )
    return pd.DataFrame(rows)


def load_baselines(alpha_summary_csv: Path, fragility_eval_summary_csv: Path, budgets: pd.DataFrame) -> pd.DataFrame:
    require_file(alpha_summary_csv, "alpha sweep summary CSV")
    alpha = pd.read_csv(alpha_summary_csv)
    target_k = set(budgets["K"].astype(int))
    rows = alpha.loc[alpha["K"].astype(int).isin(target_k) & alpha["method"].isin(["random", "line_order", "LODF_yP", "PFW", "strict_path_prob", "second_only"])].copy()
    alpha_rows = alpha.loc[alpha["K"].astype(int).isin(target_k) & alpha["method"].astype(str).str.startswith("alpha_path_prob_")].copy()
    best = []
    for _, group in alpha_rows.groupby("K", sort=False):
        row = group.sort_values(["critical_hit_count", "precision_at_k", "method"], ascending=[False, False, True]).iloc[0].copy()
        row["source_alpha_method"] = row["method"]
        row["method"] = "best_alpha_path_prob"
        best.append(row)
    if best:
        rows = pd.concat([rows, pd.DataFrame(best)], ignore_index=True, sort=False)
    if fragility_eval_summary_csv.exists():
        any_frag = pd.read_csv(fragility_eval_summary_csv)
        any_frag = any_frag.loc[any_frag["method"].eq("fragility_path_prob") & any_frag["K"].astype(int).isin(target_k)].copy()
        any_frag["method"] = "any_critical_fragility_path_prob"
        rows = pd.concat([rows, any_frag], ignore_index=True, sort=False)
    for col in ["target_mode", "top_quantile", "alpha", "epsilon", "mean_q_strict_topk", "median_q_strict_topk", "num_high_q_high_p_second_hits", "num_high_q_relay_hits"]:
        if col not in rows.columns:
            rows[col] = np.nan
    return rows


def attach_q(score: pd.DataFrame, q: pd.DataFrame, target_name: str) -> pd.DataFrame:
    subset = q.loc[q["target_name"].astype(str).eq(target_name)].copy()
    if subset.empty:
        raise ValueError(f"No strict fragility probabilities for target {target_name}")
    subset = subset.loc[pd.to_numeric(subset["seed"], errors="coerce").eq(20260708)].copy()
    subset = subset.drop_duplicates("line_label")
    out = score.merge(
        subset[["line_label", "q_strict_fragile", "strict_fragility_label", "target_mode", "top_quantile", "critical_count", "relay_cascade_count", "max_load_shed_mw", "sum_load_shed_mw", "critical_ratio", "relay_ratio", "composite_score"]].rename(columns={"line_label": "first_line"}),
        on="first_line",
        how="left",
    )
    out["q_strict_fragile"] = pd.to_numeric(out["q_strict_fragile"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    return out


def build_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    key_k = {100, 500, 1000, 5000}
    methods = ["strict_path_prob", "second_only", "best_alpha_path_prob", "any_critical_fragility_path_prob", "random", "line_order", "LODF_yP", "PFW"]
    strict_methods = summary.loc[summary["method"].astype(str).str.startswith("strict_fragility_path_prob"), "method"].unique().tolist()
    rows = summary.loc[summary["K"].isin(key_k) & summary["method"].isin(methods + strict_methods)].copy()
    best_strict = []
    for _, group in rows.loc[rows["method"].astype(str).str.startswith("strict_fragility_path_prob")].groupby("K"):
        row = group.sort_values(["critical_hit_count", "precision_at_k", "method"], ascending=[False, False, True]).iloc[0].copy()
        row["source_strict_method"] = row["method"]
        row["method"] = "best_strict_fragility_path_prob"
        best_strict.append(row)
    if best_strict:
        rows = pd.concat([rows, pd.DataFrame(best_strict)], ignore_index=True, sort=False)
    out = rows.rename(columns={"critical_hit_count": "critical_hits", "relay_cascade_hit_count": "relay_hits", "precision_at_k": "precision", "recall_relay_cascade": "recall_relay"})
    for base in ["random", "line_order", "LODF_yP", "PFW", "strict_path_prob", "second_only", "best_alpha_path_prob", "any_critical_fragility_path_prob"]:
        table = out.loc[out["method"].eq(base), ["K", "critical_hits"]].rename(columns={"critical_hits": f"{base}_hits"})
        out = out.merge(table, on="K", how="left")
    mapping = {
        "random": "random",
        "line_order": "line_order",
        "lodf": "LODF_yP",
        "pfw": "PFW",
        "strict_path_prob": "strict_path_prob",
        "second_only": "second_only",
        "best_alpha": "best_alpha_path_prob",
        "any_critical_fragility": "any_critical_fragility_path_prob",
    }
    for label, colbase in mapping.items():
        col = f"{colbase}_hits"
        if col in out:
            out[f"relative_to_{label}_hits"] = out["critical_hits"] - out[col]
    keep = ["method", "target_mode", "top_quantile", "K", "critical_hits", "relay_hits", "precision", "recall_critical", "recall_relay", "relative_to_random_hits", "relative_to_line_order_hits", "relative_to_lodf_hits", "relative_to_pfw_hits", "relative_to_strict_path_prob_hits", "relative_to_second_only_hits", "relative_to_best_alpha_hits", "relative_to_any_critical_fragility_hits"]
    return out[[c for c in keep if c in out.columns]].sort_values(["K", "method"])


def build_diagnostics(score_by_target: dict[str, pd.DataFrame], ranked_by_target: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for method, score in score_by_target.items():
        target_mode = str(score["target_mode"].dropna().iloc[0]) if "target_mode" in score and score["target_mode"].notna().any() else ""
        top_quantile = float(score["top_quantile"].dropna().iloc[0]) if "top_quantile" in score and score["top_quantile"].notna().any() else np.nan
        rank_map = {path: rank for rank, path in enumerate(ranked_by_target[method]["path"].astype(str), start=1)}
        strict_rank = {path: rank for rank, path in enumerate(ranked_by_score(score.assign(score_alpha=score["p_shed_first"] * score["p_shed_second"]), "score_alpha")["path"].astype(str), start=1)}
        second_rank = {path: rank for rank, path in enumerate(ranked_by_score(score.assign(score_alpha=score["p_shed_second"]), "score_alpha")["path"].astype(str), start=1)}
        for first, group in score.groupby("first_line", sort=True):
            critical = group.loc[group["critical"]]
            vals = [rank_map[p] for p in group["path"].astype(str)]
            strict_vals = [strict_rank[p] for p in group["path"].astype(str)]
            second_vals = [second_rank[p] for p in group["path"].astype(str)]
            rows.append(
                {
                    "first_line": first,
                    "target_mode": target_mode,
                    "top_quantile": top_quantile,
                    "q_strict_fragile": float(group["q_strict_fragile"].iloc[0]),
                    "strict_fragility_label": int(group["strict_fragility_label"].iloc[0]),
                    "p_first": float(group["p_shed_first"].iloc[0]),
                    "first_step_critical": False,
                    "critical_count": int(group["critical_count"].iloc[0]),
                    "relay_cascade_count": int(group["relay_cascade_count"].iloc[0]),
                    "max_load_shed_mw": float(group["max_load_shed_mw"].iloc[0]),
                    "sum_load_shed_mw": float(group["sum_load_shed_mw"].iloc[0]),
                    "critical_ratio": float(group["critical_ratio"].iloc[0]),
                    "relay_ratio": float(group["relay_ratio"].iloc[0]),
                    "composite_score": float(group["composite_score"].iloc[0]),
                    "num_valid_n2_paths": int(len(group)),
                    "num_valid_critical_paths": int(group["critical"].sum()),
                    "num_valid_relay_cascade_paths": int(group["relay_cascade"].sum()),
                    "mean_p_second_for_critical_paths": float(critical["p_shed_second"].mean()) if len(critical) else 0.0,
                    "max_p_second_for_critical_paths": float(critical["p_shed_second"].max()) if len(critical) else 0.0,
                    "mean_rank_strict_fragility_path_prob": float(np.mean(vals)),
                    "mean_rank_strict_path_prob": float(np.mean(strict_vals)),
                    "mean_rank_second_only": float(np.mean(second_vals)),
                    "rank_improvement_vs_strict_path_prob": float(np.mean(strict_vals) - np.mean(vals)),
                    "representative_critical_paths": ";".join(critical.sort_values("total_load_shed_mw", ascending=False)["path"].head(5).astype(str)),
                    "representative_relay_paths": ";".join(group.loc[group["relay_cascade"]].sort_values("total_load_shed_mw", ascending=False)["path"].head(5).astype(str)),
                }
            )
    return pd.DataFrame(rows)


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    require_file(args.strict_fragility_probabilities_csv, "strict fragility probabilities CSV")
    score_args = argparse.Namespace(score_table_csv=args.s1_score_table_csv, fulltruth_csv=args.fulltruth_csv, path_index_csv=args.path_index_csv, dataset_npz=Path("missing.npz"), model_path=Path("missing.pt"), feature_normalizer_json=Path("missing.json"), first_step_probabilities_csv=args.first_step_probabilities_csv)
    score = build_score_table(score_args)
    q = pd.read_csv(args.strict_fragility_probabilities_csv)
    budgets = make_budget_table(len(score), args.k_values, args.ratio_k_values)
    parts = [load_baselines(args.alpha_sweep_summary_csv, args.fragility_eval_summary_csv, budgets)]
    ranked_map: dict[str, pd.DataFrame] = {}
    score_map: dict[str, pd.DataFrame] = {}
    for target_name in sorted(q["target_name"].dropna().astype(str).unique()):
        frame = attach_q(score, q, target_name)
        mode = str(frame["target_mode"].dropna().iloc[0])
        quantile = float(frame["top_quantile"].dropna().iloc[0])
        method = f"strict_fragility_path_prob_{target_name}"
        ranked = ranked_by_score(frame.assign(score_alpha=frame["q_strict_fragile"] * frame["p_shed_second"]), "score_alpha")
        ranked_map[method] = ranked
        score_map[method] = frame
        parts.append(evaluate_ranked(method, ranked, budgets, target_mode=mode, top_quantile=quantile))
        for alpha in args.alpha_values:
            for eps in args.epsilon_values:
                amethod = f"strict_fragility_alpha_path_prob_{target_name}_a{str(alpha).replace('.', '')}_eps{str(eps).replace('.', '').replace('-', 'm')}"
                aranked = ranked_by_score(frame.assign(score_alpha=np.power(eps + frame["q_strict_fragile"], alpha) * frame["p_shed_second"]), "score_alpha")
                ranked_map[amethod] = aranked
                parts.append(evaluate_ranked(amethod, aranked, budgets, target_mode=mode, top_quantile=quantile, alpha=float(alpha), epsilon=float(eps)))
    summary = pd.concat(parts, ignore_index=True, sort=False)
    summary.to_csv(args.output_dir / "ieee118_strict_fragility_path_prob_summary.csv", index=False, encoding="utf-8-sig")
    write_json(args.output_dir / "ieee118_strict_fragility_path_prob_summary.json", summary.to_dict("records"))
    comparison = build_comparison(summary)
    comparison.to_csv(args.output_dir / "ieee118_strict_fragility_vs_baselines_at_keyK.csv", index=False, encoding="utf-8-sig")
    best = comparison.loc[comparison["method"].eq("best_strict_fragility_path_prob")].copy()
    best.to_csv(args.output_dir / "ieee118_strict_fragility_best_configs.csv", index=False, encoding="utf-8-sig")
    curve_rows = []
    for method, ranked in ranked_map.items():
        if not method.startswith("strict_fragility_path_prob_"):
            continue
        for k in sorted(set(budgets["K"].astype(int))):
            top = ranked.head(k)
            curve_rows.append({"method": method, "candidate_evaluations": k, "critical_paths_found": int(top["critical"].sum()), "relay_cascade_paths_found": int(top["relay_cascade"].sum()), "captured_load_shed_mw": float(top["total_load_shed_mw"].sum())})
    pd.DataFrame(curve_rows).to_csv(args.output_dir / "ieee118_strict_fragility_curve_points_sparse.csv", index=False, encoding="utf-8-sig")
    top_rows = []
    for method, ranked in ranked_map.items():
        if method.startswith("strict_fragility_path_prob_"):
            top = ranked.head(300).copy()
            top.insert(0, "rank", np.arange(1, len(top) + 1))
            top.insert(0, "method", method)
            top_rows.append(top)
    pd.concat(top_rows, ignore_index=True, sort=False).to_csv(args.output_dir / "ieee118_strict_fragility_topk_paths.csv", index=False, encoding="utf-8-sig")
    diag = build_diagnostics(score_map, ranked_map)
    diag.to_csv(args.output_dir / "strict_first_line_fragility_diagnostics.csv", index=False, encoding="utf-8-sig")
    write_json(args.output_dir / "strict_first_line_fragility_diagnostics.json", diag.to_dict("records"))
    heat = summary.loc[summary["method"].astype(str).str.startswith("strict_fragility_path_prob_") & summary["K"].isin([1000, 5000])]
    heat.to_csv(args.output_dir / "ieee118_strict_fragility_heatmap_data.csv", index=False, encoding="utf-8-sig")
    config = {"s1_score_table_csv": str(args.s1_score_table_csv), "strict_fragility_probabilities_csv": str(args.strict_fragility_probabilities_csv), "num_paths": int(len(score)), "no_opa_rerun": True}
    write_json(args.output_dir / "ieee118_strict_fragility_config.json", config)
    (args.output_dir / "ieee118_strict_fragility_readme.md").write_text(
        "# IEEE118 Strict Fragility Path Probability Evaluation\n\n"
        "Strict first-line fragility targets are evaluated as `q_strict_fragile * p_second`. "
        "Baselines include strict path_prob, second_only, best alpha, any-critical fragility, random, LODF_yP, and PFW.\n",
        encoding="utf-8",
    )
    return {"summary_csv": str(args.output_dir / "ieee118_strict_fragility_path_prob_summary.csv"), "comparison_csv": str(args.output_dir / "ieee118_strict_fragility_vs_baselines_at_keyK.csv")}


def main() -> None:
    print(json.dumps(run_evaluation(parse_args()), indent=2))


if __name__ == "__main__":
    main()
