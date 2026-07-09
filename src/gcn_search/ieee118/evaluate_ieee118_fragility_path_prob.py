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
    build_heatmap_data,
    build_score_table,
    build_topk_paths,
    build_vs_baselines,
    coerce_bool,
    evaluate_ranked_frame,
    make_budget_table,
    ranked_by_score,
    select_best_configs,
    write_json,
)


DEFAULT_FRAGILITY = DEFAULT_BASE / "first_line_fragility"
DEFAULT_ALPHA = DEFAULT_BASE / "alpha_path_prob_sweep"
DEFAULT_OUTPUT = DEFAULT_BASE / "first_line_fragility_eval"
DEFAULT_FULLTRUTH = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
DEFAULT_PATH_INDEX_DIR = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate IEEE118 first-line fragility path probability ranking.")
    parser.add_argument("--fulltruth-csv", type=Path, default=DEFAULT_FULLTRUTH / "ieee118_fulltruth_summary.csv")
    parser.add_argument("--path-index-csv", type=Path, default=DEFAULT_PATH_INDEX_DIR / "ieee118_rts79_gcn_path_index.csv")
    parser.add_argument("--s1-score-table-csv", type=Path, default=DEFAULT_SCORE_TABLE)
    parser.add_argument("--first-line-fragility-probabilities-csv", type=Path, default=DEFAULT_FRAGILITY / "ieee118_first_line_fragility_probabilities.csv")
    parser.add_argument("--first-step-probabilities-csv", type=Path, default=DEFAULT_BASE / "pilot_2000_eval" / "ieee118_paper_aligned_pilot2000_first_step_probabilities.csv")
    parser.add_argument("--alpha-sweep-summary-csv", type=Path, default=DEFAULT_ALPHA / "alpha_path_prob_sweep_summary.csv")
    parser.add_argument("--alpha-sweep-best-configs-csv", type=Path, default=DEFAULT_ALPHA / "alpha_path_prob_sweep_best_configs.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--k-values", type=int, nargs="+", default=[100, 500, 1000, 2000, 5000, 10000])
    parser.add_argument("--ratio-k-values", type=float, nargs="+", default=[0.005, 0.01, 0.02, 0.05, 0.10])
    parser.add_argument("--fragility-alpha-values", type=float, nargs="*", default=[0.25, 0.5, 0.75, 1.0])
    parser.add_argument("--fragility-epsilon-values", type=float, nargs="*", default=[1e-3, 1e-2])
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label}: {path}. This evaluator reuses compact/local score artifacts and will not rerun OPA."
        )


def load_fragility_probabilities(path: Path, seed: int = 20260708) -> pd.DataFrame:
    require_file(path, "first-line fragility probabilities CSV")
    prob = pd.read_csv(path)
    required = {"seed", "line_label", "q_fragile", "fragility_label", "loss_mask", "first_step_direct_shed_label", "first_step_critical"}
    missing = sorted(required - set(prob.columns))
    if missing:
        raise ValueError(f"Fragility probabilities CSV missing required columns: {missing}")
    prob = prob.loc[pd.to_numeric(prob["seed"], errors="coerce").eq(int(seed))].copy()
    if prob.empty:
        raise ValueError(f"No fragility probabilities for heldout seed {seed}.")
    prob["q_fragile"] = pd.to_numeric(prob["q_fragile"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    return prob.drop_duplicates("line_label")


def attach_q_fragile(score: pd.DataFrame, q_table: pd.DataFrame) -> pd.DataFrame:
    q = q_table[["line_label", "q_fragile", "fragility_label", "loss_mask", "first_step_direct_shed_label", "first_step_critical"]].rename(
        columns={"line_label": "first_line"}
    )
    out = score.merge(q, on="first_line", how="left")
    out["q_fragile"] = pd.to_numeric(out["q_fragile"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    out["fragility_label"] = pd.to_numeric(out["fragility_label"], errors="coerce").fillna(0).astype(int)
    out["q_loss_mask"] = coerce_bool(out["loss_mask"]) if "loss_mask" in out.columns else False
    out["first_step_direct_shed_label"] = pd.to_numeric(out["first_step_direct_shed_label"], errors="coerce").fillna(0).astype(int)
    out["first_step_critical"] = coerce_bool(out["first_step_critical"]) if "first_step_critical" in out.columns else False
    return out


def evaluate_fragility_ranked(method: str, ranked: pd.DataFrame, budgets: pd.DataFrame, *, alpha: float | None = None, epsilon: float | None = None) -> pd.DataFrame:
    base = evaluate_ranked_frame(method, ranked, budgets, alpha=alpha, epsilon=epsilon)
    rows = []
    for _, row in base.iterrows():
        top = ranked.head(int(row["K"]))
        high_q = top[top["critical"] & top["q_fragile"].gt(0.5) & top["p_shed_second"].gt(0.8)]
        extra = {
            "mean_q_fragile_topk": float(top["q_fragile"].mean()) if len(top) else 0.0,
            "median_q_fragile_topk": float(top["q_fragile"].median()) if len(top) else 0.0,
            "num_high_q_high_p_second_hits": int(len(high_q)),
        }
        rows.append({**row.to_dict(), **extra})
    return pd.DataFrame(rows)


def score_fragility_variants(score: pd.DataFrame, budgets: pd.DataFrame, alpha_values: list[float], epsilon_values: list[float]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    ranked_frames: dict[str, pd.DataFrame] = {}
    parts = []
    base = score.copy()
    base["score_fragility"] = base["q_fragile"] * base["p_shed_second"]
    ranked = ranked_by_score(base.rename(columns={"score_fragility": "score_alpha"}), "score_alpha")
    ranked_frames["fragility_path_prob"] = ranked
    parts.append(evaluate_fragility_ranked("fragility_path_prob", ranked, budgets))

    for alpha in alpha_values:
        for eps in epsilon_values:
            method = f"fragility_path_prob_alpha_a{str(alpha).replace('.', '')}_eps{str(eps).replace('.', '').replace('-', 'm')}"
            frame = score.copy()
            frame["score_alpha"] = np.power(eps + frame["q_fragile"], alpha) * frame["p_shed_second"]
            ranked = ranked_by_score(frame, "score_alpha")
            ranked_frames[method] = ranked
            parts.append(evaluate_fragility_ranked(method, ranked, budgets, alpha=float(alpha), epsilon=float(eps)))
    return pd.concat(parts, ignore_index=True), ranked_frames


def load_alpha_baseline_rows(alpha_summary_csv: Path, alpha_best_configs_csv: Path, budgets: pd.DataFrame) -> pd.DataFrame:
    require_file(alpha_summary_csv, "alpha sweep summary CSV")
    summary = pd.read_csv(alpha_summary_csv)
    wanted = {"random", "line_order", "LODF_yP", "PFW", "strict_path_prob", "second_only"}
    if alpha_best_configs_csv.exists():
        best = pd.read_csv(alpha_best_configs_csv)
        wanted.update(best["method"].dropna().astype(str).tolist())
    target_k = set(budgets["K"].astype(int))
    rows = summary.loc[summary["method"].astype(str).isin(wanted) & summary["K"].astype(int).isin(target_k)].copy()
    alpha_rows = summary.loc[summary["method"].astype(str).str.startswith("alpha_path_prob_") & summary["K"].astype(int).isin(target_k)].copy()
    best_rows = []
    for _, group in alpha_rows.groupby("K", sort=False):
        best = group.sort_values(["critical_hit_count", "precision_at_k", "method"], ascending=[False, False, True]).iloc[0].copy()
        best["source_alpha_method"] = best["method"]
        best["method"] = "best_alpha_path_prob"
        best_rows.append(best)
    if best_rows:
        rows = pd.concat([rows, pd.DataFrame(best_rows)], ignore_index=True, sort=False)
    if "mean_q_fragile_topk" not in rows.columns:
        rows["mean_q_fragile_topk"] = np.nan
        rows["median_q_fragile_topk"] = np.nan
        rows["num_high_q_high_p_second_hits"] = np.nan
    return rows


def build_key_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    key_k = {100, 500, 1000, 5000}
    methods = ["strict_path_prob", "second_only", "best_alpha_path_prob", "fragility_path_prob", "random", "LODF_yP", "PFW"]
    subset = summary.loc[summary["K"].isin(key_k) & summary["method"].isin(methods)].copy()
    pivots = {}
    for base in ["random", "LODF_yP", "PFW", "strict_path_prob", "second_only"]:
        pivots[base] = subset.loc[subset["method"].eq(base), ["K", "critical_hit_count"]].rename(columns={"critical_hit_count": f"{base}_hits"})
    pivots["best_alpha"] = subset.loc[subset["method"].eq("best_alpha_path_prob"), ["K", "critical_hit_count"]].rename(columns={"critical_hit_count": "best_alpha_hits"})
    out = subset.rename(
        columns={
            "critical_hit_count": "critical_hits",
            "relay_cascade_hit_count": "relay_hits",
            "precision_at_k": "precision",
            "recall_relay_cascade": "recall_relay",
        }
    )
    for base, table in pivots.items():
        out = out.merge(table, on="K", how="left")
    for base, col in [
        ("random", "random_hits"),
        ("lodf", "LODF_yP_hits"),
        ("pfw", "PFW_hits"),
        ("strict_path_prob", "strict_path_prob_hits"),
        ("second_only", "second_only_hits"),
        ("best_alpha", "best_alpha_hits"),
    ]:
        if col in out.columns:
            out[f"relative_to_{base}_hits"] = out["critical_hits"] - out[col]
    keep = [
        "method",
        "K",
        "critical_hits",
        "relay_hits",
        "precision",
        "recall_critical",
        "recall_relay",
        "relative_to_random_hits",
        "relative_to_lodf_hits",
        "relative_to_pfw_hits",
        "relative_to_strict_path_prob_hits",
        "relative_to_second_only_hits",
        "relative_to_best_alpha_hits",
    ]
    return out[[col for col in keep if col in out.columns]].sort_values(["K", "method"])


def build_first_line_diagnostics(score: pd.DataFrame, summary_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rank_maps = {}
    for method, ranked in summary_frames.items():
        rank_maps[method] = {path: rank for rank, path in enumerate(ranked["path"].astype(str), start=1)}
    rows = []
    for first_line, group in score.groupby("first_line", sort=True):
        critical = group.loc[group["critical"]]
        row = {
            "first_line": first_line,
            "q_fragile": float(group["q_fragile"].iloc[0]),
            "p_first": float(group["p_shed_first"].iloc[0]),
            "fragility_label": int(group["fragility_label"].iloc[0]),
            "first_step_critical": bool(group["first_step_critical"].iloc[0]),
            "num_valid_n2_paths": int(len(group)),
            "num_valid_critical_paths": int(group["critical"].sum()),
            "num_valid_relay_cascade_paths": int(group["relay_cascade"].sum()),
            "max_total_load_shed_mw": float(group["total_load_shed_mw"].max()),
            "mean_p_second_for_critical_paths": float(critical["p_shed_second"].mean()) if len(critical) else 0.0,
            "max_p_second_for_critical_paths": float(critical["p_shed_second"].max()) if len(critical) else 0.0,
            "representative_critical_paths": ";".join(critical.sort_values("total_load_shed_mw", ascending=False)["path"].head(5).astype(str)),
        }
        for method, ranks in rank_maps.items():
            vals = [ranks[path] for path in group["path"].astype(str) if path in ranks]
            row[f"mean_rank_{method}"] = float(np.mean(vals)) if vals else np.nan
        if "fragility_path_prob" in rank_maps and "strict_path_prob" in rank_maps:
            row["rank_improvement_vs_strict"] = row.get("mean_rank_strict_path_prob", np.nan) - row.get("mean_rank_fragility_path_prob", np.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    score_args = argparse.Namespace(
        score_table_csv=args.s1_score_table_csv,
        fulltruth_csv=args.fulltruth_csv,
        path_index_csv=args.path_index_csv,
        dataset_npz=Path("missing.npz"),
        model_path=Path("missing.pt"),
        feature_normalizer_json=Path("missing.json"),
        first_step_probabilities_csv=args.first_step_probabilities_csv,
    )
    score = build_score_table(score_args)
    q = load_fragility_probabilities(args.first_line_fragility_probabilities_csv)
    score = attach_q_fragile(score, q)
    budgets = make_budget_table(len(score), args.k_values, args.ratio_k_values)
    frag_summary, ranked_frames = score_fragility_variants(score, budgets, args.fragility_alpha_values, args.fragility_epsilon_values)
    alpha_rows = load_alpha_baseline_rows(args.alpha_sweep_summary_csv, args.alpha_sweep_best_configs_csv, budgets)
    summary = pd.concat([alpha_rows, frag_summary], ignore_index=True, sort=False).sort_values(["method", "K"])
    summary.to_csv(args.output_dir / "ieee118_fragility_path_prob_summary.csv", index=False, encoding="utf-8-sig")
    write_json(args.output_dir / "ieee118_fragility_path_prob_summary.json", summary.to_dict("records"))
    best = select_best_configs(summary)
    best.to_csv(args.output_dir / "ieee118_fragility_path_prob_best_configs.csv", index=False, encoding="utf-8-sig")
    selected = ["fragility_path_prob"] + [m for m in ranked_frames if m.startswith("fragility_path_prob_alpha")][:2]
    curve_rows = []
    for method in selected:
        ranked = ranked_frames[method]
        for k in sorted(set(int(v) for v in budgets["K"])):
            top = ranked.head(k)
            curve_rows.append(
                {
                    "method": method,
                    "candidate_evaluations": k,
                    "critical_paths_found": int(top["critical"].sum()),
                    "relay_cascade_paths_found": int(top["relay_cascade"].sum()),
                    "captured_load_shed_mw": float(top["total_load_shed_mw"].sum()),
                }
            )
    pd.DataFrame(curve_rows).to_csv(args.output_dir / "ieee118_fragility_path_prob_curve_points_sparse.csv", index=False, encoding="utf-8-sig")
    build_topk_paths(ranked_frames, selected, 500).to_csv(args.output_dir / "ieee118_fragility_path_prob_topk_paths.csv", index=False, encoding="utf-8-sig")
    comparison = build_key_comparison(summary)
    comparison.to_csv(args.output_dir / "ieee118_fragility_vs_alpha_baselines_at_keyK.csv", index=False, encoding="utf-8-sig")
    diagnostics = build_first_line_diagnostics(score, {"fragility_path_prob": ranked_frames["fragility_path_prob"], "strict_path_prob": ranked_by_score(score.assign(score_alpha=score["p_shed_first"] * score["p_shed_second"]), "score_alpha"), "second_only": ranked_by_score(score.assign(score_alpha=score["p_shed_second"]), "score_alpha")})
    diagnostics.to_csv(args.output_dir / "first_line_fragility_diagnostics.csv", index=False, encoding="utf-8-sig")
    write_json(args.output_dir / "first_line_fragility_diagnostics.json", diagnostics.to_dict("records"))
    config = {
        "fulltruth_csv": str(args.fulltruth_csv),
        "s1_score_table_csv": str(args.s1_score_table_csv),
        "first_line_fragility_probabilities_csv": str(args.first_line_fragility_probabilities_csv),
        "alpha_sweep_summary_csv": str(args.alpha_sweep_summary_csv),
        "num_paths": int(len(score)),
        "num_critical_paths": int(score["critical"].sum()),
        "num_relay_cascade_paths": int(score["relay_cascade"].sum()),
        "scoring_rule": "fragility_path_prob = q_fragile(Li|S0) * p_second(Lj|S1(i))",
        "no_opa_rerun": True,
    }
    write_json(args.output_dir / "ieee118_fragility_path_prob_config.json", config)
    (args.output_dir / "ieee118_fragility_path_prob_readme.md").write_text(
        "# IEEE118 Fragility Path Probability Evaluation\n\n"
        "This evaluation replaces the strict first-step direct-shed probability with a learned first-line fragility score. "
        "It preserves strict path_prob, second_only, alpha_path_prob, random, LODF_yP, and PFW as baselines. "
        "No OPA rerun or GCN architecture change is performed.\n",
        encoding="utf-8",
    )
    return {
        "summary_csv": str(args.output_dir / "ieee118_fragility_path_prob_summary.csv"),
        "comparison_csv": str(args.output_dir / "ieee118_fragility_vs_alpha_baselines_at_keyK.csv"),
    }


def main() -> None:
    print(json.dumps(run_evaluation(parse_args()), indent=2))


if __name__ == "__main__":
    main()
