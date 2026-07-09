from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_ieee118_rts79_protocol_search import load_truth, make_path_score_table, predict_s1_probabilities


DEFAULT_BASE = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup"
DEFAULT_EVAL = DEFAULT_BASE / "pilot_2000_eval"
DEFAULT_TRAIN = DEFAULT_BASE / "pilot_2000"
DEFAULT_ORIGINAL = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"
DEFAULT_FULLTRUTH = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
DEFAULT_SCORE_TABLE = DEFAULT_BASE / "s0_bottleneck_diagnostics" / "s0_bottleneck_full_score_table_local_only.csv"
DEFAULT_OUTPUT = DEFAULT_BASE / "alpha_path_prob_sweep"
DEFAULT_BASELINE_SUMMARY = DEFAULT_EVAL / "ieee118_paper_aligned_pilot2000_search_summary.csv"
DEFAULT_BASELINE_TOPK = DEFAULT_EVAL / "ieee118_paper_aligned_pilot2000_topk_paths.csv"

STRICT_PATH_PROB_METHOD = "strict_path_prob"
SECOND_ONLY_METHOD = "second_only"
LOW_P_FIRST_THRESHOLD = 0.05
HIGH_P_SECOND_THRESHOLD = 0.8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep alpha-smoothed IEEE118 path probability rankings without retraining or rerunning OPA."
    )
    parser.add_argument("--score-table-csv", type=Path, default=DEFAULT_SCORE_TABLE)
    parser.add_argument("--fulltruth-csv", type=Path, default=DEFAULT_FULLTRUTH / "ieee118_fulltruth_summary.csv")
    parser.add_argument("--path-index-csv", type=Path, default=DEFAULT_ORIGINAL / "ieee118_rts79_gcn_path_index.csv")
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_ORIGINAL / "ieee118_rts79_gcn_dataset.npz")
    parser.add_argument("--model-path", type=Path, default=DEFAULT_TRAIN / "ieee118_paper_gcn_model.pt")
    parser.add_argument("--feature-normalizer-json", type=Path, default=DEFAULT_TRAIN / "ieee118_paper_gcn_feature_normalizer.json")
    parser.add_argument("--first-step-probabilities-csv", type=Path, default=DEFAULT_EVAL / "ieee118_paper_aligned_pilot2000_first_step_probabilities.csv")
    parser.add_argument("--baseline-summary-csv", type=Path, default=DEFAULT_BASELINE_SUMMARY)
    parser.add_argument("--baseline-topk-paths-csv", type=Path, default=DEFAULT_BASELINE_TOPK)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--alphas", type=float, nargs="+", default=[0.0, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0])
    parser.add_argument("--epsilons", type=float, nargs="+", default=[0.0, 1e-6, 1e-4, 1e-3, 1e-2])
    parser.add_argument("--k-values", type=int, nargs="+", default=[100, 500, 1000, 2000, 5000, 10000])
    parser.add_argument("--ratio-k-values", type=float, nargs="+", default=[0.005, 0.01, 0.02, 0.05, 0.10])
    parser.add_argument("--random-seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument("--topk-output-rows", type=int, default=500)
    parser.add_argument("--method-suffix", default="")
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label}: {path}. This alpha sweep reads local PR #14/#15 score artifacts "
            "and will not retrain the GCN, rerun OPA, or regenerate full-truth data."
        )


def coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_ready(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if not math.isfinite(float(value)):
            return None
        return float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(json_ready(value), indent=2), encoding="utf-8")


def _compact_decimal(value: float) -> str:
    if abs(value) < 1e-15:
        return "0"
    text = f"{value:.12g}"
    if "e" in text or "E" in text:
        base, exp = text.lower().split("e")
        exp_int = int(exp)
        base_digits = base.replace(".", "").replace("-", "m")
        return f"{base_digits}em{abs(exp_int)}" if exp_int < 0 else f"{base_digits}e{exp_int}"
    return text.rstrip("0").rstrip(".").replace(".", "")


def format_alpha(alpha: float) -> str:
    return f"a{_compact_decimal(alpha)}"


def format_epsilon(epsilon: float) -> str:
    if abs(epsilon) < 1e-15:
        return "eps0"
    text = f"{epsilon:.12e}"
    base, exp = text.split("e")
    exp_int = int(exp)
    base_value = float(base)
    if abs(base_value - round(base_value)) < 1e-12:
        base_token = str(int(round(base_value)))
    else:
        base_token = f"{base_value:.12g}".replace(".", "")
    exp_token = f"em{abs(exp_int)}" if exp_int < 0 else f"e{exp_int}"
    return f"eps{base_token}{exp_token}"


def alpha_method_name(alpha: float, epsilon: float, suffix: str = "") -> str:
    base = f"alpha_path_prob_{format_alpha(alpha)}_{format_epsilon(epsilon)}"
    return f"{base}{suffix}" if suffix else base


def normalize_score_table(score: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    if "p_first" in score.columns and "p_shed_first" not in score.columns:
        rename["p_first"] = "p_shed_first"
    if "p_second" in score.columns and "p_shed_second" not in score.columns:
        rename["p_second"] = "p_shed_second"
    score = score.rename(columns=rename).copy()
    required = {
        "path",
        "first_line",
        "second_line",
        "p_shed_first",
        "p_shed_second",
        "critical",
        "relay_cascade",
        "total_load_shed_mw",
    }
    missing = sorted(required - set(score.columns))
    if missing:
        raise ValueError(f"Score table missing required columns: {missing}")
    score["path"] = score["path"].astype(str)
    score["first_line"] = score["first_line"].astype(str)
    score["second_line"] = score["second_line"].astype(str)
    score["p_shed_first"] = pd.to_numeric(score["p_shed_first"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    score["p_shed_second"] = pd.to_numeric(score["p_shed_second"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    score["critical"] = coerce_bool(score["critical"])
    score["relay_cascade"] = coerce_bool(score["relay_cascade"])
    score["total_load_shed_mw"] = pd.to_numeric(score["total_load_shed_mw"], errors="coerce").fillna(0.0)
    if "path_product_score" not in score.columns:
        score["path_product_score"] = score["p_shed_first"] * score["p_shed_second"]
    if "critical_mechanism" not in score.columns:
        score["critical_mechanism"] = np.where(score["relay_cascade"], "relay_cascade", np.where(score["critical"], "critical", "non_critical"))
    return score.reset_index(drop=True)


def build_score_table(args: argparse.Namespace) -> pd.DataFrame:
    if args.score_table_csv.exists():
        return normalize_score_table(pd.read_csv(args.score_table_csv))
    for path, label in [
        (args.fulltruth_csv, "full-truth CSV"),
        (args.path_index_csv, "path index CSV"),
        (args.dataset_npz, "dataset NPZ"),
        (args.model_path, "paper-aligned model checkpoint"),
        (args.feature_normalizer_json, "feature normalizer JSON"),
        (args.first_step_probabilities_csv, "first-step probabilities CSV"),
    ]:
        require_file(path, label)
    truth = load_truth(args.fulltruth_csv)
    s1_probability, _ = predict_s1_probabilities(args.dataset_npz, args.model_path, args.feature_normalizer_json)
    return normalize_score_table(make_path_score_table(args.path_index_csv, args.first_step_probabilities_csv, s1_probability, truth))


def alpha_score(p_first: pd.Series, p_second: pd.Series, alpha: float, epsilon: float) -> pd.Series:
    p_first = pd.to_numeric(p_first, errors="coerce").fillna(0.0).clip(0.0, 1.0)
    p_second = pd.to_numeric(p_second, errors="coerce").fillna(0.0).clip(0.0, 1.0)
    if abs(alpha) < 1e-15:
        return p_second.copy()
    return np.power(epsilon + p_first, alpha) * p_second


def add_alpha_score(score: pd.DataFrame, alpha: float, epsilon: float, score_col: str = "score_alpha") -> pd.DataFrame:
    out = score.copy()
    out[score_col] = alpha_score(out["p_shed_first"], out["p_shed_second"], alpha, epsilon)
    return out


def ranked_by_score(score: pd.DataFrame, score_col: str) -> pd.DataFrame:
    return score.sort_values(
        [score_col, "p_shed_second", "p_shed_first", "path"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def make_budget_table(total_paths: int, k_values: list[int], ratio_k_values: list[float]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for k in k_values:
        bounded = min(max(int(k), 1), total_paths)
        if bounded not in seen:
            rows.append({"budget_type": "fixed", "budget_label": str(int(k)), "K": bounded, "search_budget_ratio": bounded / total_paths})
            seen.add(bounded)
    for ratio in ratio_k_values:
        bounded = min(max(int(round(total_paths * float(ratio))), 1), total_paths)
        if bounded not in seen:
            label = f"{float(ratio) * 100:g}%"
            rows.append({"budget_type": "percent", "budget_label": label, "K": bounded, "search_budget_ratio": bounded / total_paths})
            seen.add(bounded)
    return pd.DataFrame(rows).sort_values("K").reset_index(drop=True)


def evaluate_ranked_frame(method: str, ranked: pd.DataFrame, budgets: pd.DataFrame, *, alpha: float | None, epsilon: float | None) -> pd.DataFrame:
    total_paths = len(ranked)
    total_critical = int(ranked["critical"].sum())
    total_relay = int(ranked["relay_cascade"].sum())
    total_shed = float(ranked["total_load_shed_mw"].sum())
    total_relay_shed = float(ranked.loc[ranked["relay_cascade"], "total_load_shed_mw"].sum())
    rows: list[dict[str, Any]] = []
    for _, budget in budgets.iterrows():
        k = int(budget["K"])
        top = ranked.head(k)
        critical_hits = int(top["critical"].sum())
        relay_hits = int(top["relay_cascade"].sum())
        shed = float(top["total_load_shed_mw"].sum())
        relay_shed = float(top.loc[top["relay_cascade"], "total_load_shed_mw"].sum())
        low_high = top[
            top["critical"]
            & top["p_shed_first"].lt(LOW_P_FIRST_THRESHOLD)
            & top["p_shed_second"].gt(HIGH_P_SECOND_THRESHOLD)
        ]
        rows.append(
            {
                "method": method,
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
                "captured_total_load_shed_mw": shed,
                "captured_total_load_shed_ratio": shed / max(total_shed, 1e-12),
                "captured_relay_cascade_load_shed_mw": relay_shed,
                "captured_relay_cascade_load_shed_ratio": relay_shed / max(total_relay_shed, 1e-12),
                "mean_p_first_topk": float(top["p_shed_first"].mean()) if len(top) else 0.0,
                "median_p_first_topk": float(top["p_shed_first"].median()) if len(top) else 0.0,
                "mean_p_second_topk": float(top["p_shed_second"].mean()) if len(top) else 0.0,
                "median_p_second_topk": float(top["p_shed_second"].median()) if len(top) else 0.0,
                "num_low_p_first_high_p_second_hits": int(len(low_high)),
            }
        )
    return pd.DataFrame(rows)


def summarize_random(score: pd.DataFrame, budgets: pd.DataFrame, random_seeds: list[int]) -> pd.DataFrame:
    parts = []
    for seed in random_seeds:
        ranked = score.sample(frac=1.0, random_state=int(seed)).reset_index(drop=True)
        parts.append(evaluate_ranked_frame(f"random_seed_{seed}", ranked, budgets, alpha=None, epsilon=None))
    raw = pd.concat(parts, ignore_index=True).assign(method="random")
    group_cols = ["method", "alpha", "epsilon", "budget_type", "budget_label", "K", "search_budget_ratio"]
    rows = []
    for key, group in raw.groupby(group_cols, dropna=False, sort=False):
        row = dict(zip(group_cols, key))
        for col in raw.columns:
            if col in group_cols:
                continue
            vals = pd.to_numeric(group[col], errors="coerce")
            row[col] = float(vals.mean())
            row[f"{col}_std"] = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_alpha_sweep(
    score: pd.DataFrame,
    *,
    alphas: list[float],
    epsilons: list[float],
    budgets: pd.DataFrame,
    random_seeds: list[int],
    method_suffix: str = "",
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    score = normalize_score_table(score)
    ranked_frames: dict[str, pd.DataFrame] = {}
    parts = []

    strict = ranked_by_score(add_alpha_score(score, 1.0, 0.0), "score_alpha")
    second = ranked_by_score(add_alpha_score(score, 0.0, 0.0), "score_alpha")
    ranked_frames[STRICT_PATH_PROB_METHOD] = strict
    ranked_frames[SECOND_ONLY_METHOD] = second
    parts.append(evaluate_ranked_frame(STRICT_PATH_PROB_METHOD, strict, budgets, alpha=1.0, epsilon=0.0))
    parts.append(evaluate_ranked_frame(SECOND_ONLY_METHOD, second, budgets, alpha=0.0, epsilon=0.0))

    line_order = score.reset_index(drop=True)
    ranked_frames["line_order"] = line_order
    parts.append(evaluate_ranked_frame("line_order", line_order, budgets, alpha=None, epsilon=None))
    parts.append(summarize_random(score, budgets, random_seeds))

    for alpha in alphas:
        for epsilon in epsilons:
            method = alpha_method_name(float(alpha), float(epsilon), method_suffix)
            ranked = ranked_by_score(add_alpha_score(score, float(alpha), float(epsilon)), "score_alpha")
            ranked_frames[method] = ranked
            parts.append(evaluate_ranked_frame(method, ranked, budgets, alpha=float(alpha), epsilon=float(epsilon)))

    return pd.concat(parts, ignore_index=True, sort=False), ranked_frames


def load_external_baseline_rows(
    score: pd.DataFrame,
    budgets: pd.DataFrame,
    baseline_summary_csv: Path,
    baseline_topk_paths_csv: Path,
    methods: tuple[str, ...] = ("LODF_yP", "PFW"),
) -> pd.DataFrame:
    if not baseline_summary_csv.exists():
        return pd.DataFrame()
    summary = pd.read_csv(baseline_summary_csv)
    summary = summary.loc[summary["method"].isin(methods)].copy()
    if summary.empty:
        return pd.DataFrame()
    target_k = set(int(k) for k in budgets["K"])
    summary = summary.loc[summary["K"].astype(int).isin(target_k)].copy()
    if summary.empty:
        return pd.DataFrame()
    summary["alpha"] = np.nan
    summary["epsilon"] = np.nan
    if "captured_total_load_shed_mw" not in summary.columns and "captured_load_shed_mw" in summary.columns:
        summary["captured_total_load_shed_mw"] = summary["captured_load_shed_mw"]
    if "captured_total_load_shed_ratio" not in summary.columns and "captured_load_shed_ratio" in summary.columns:
        summary["captured_total_load_shed_ratio"] = summary["captured_load_shed_ratio"]
    score_by_path = score.set_index("path")
    topk = pd.read_csv(baseline_topk_paths_csv) if baseline_topk_paths_csv.exists() else pd.DataFrame()
    for col in [
        "mean_p_first_topk",
        "median_p_first_topk",
        "mean_p_second_topk",
        "median_p_second_topk",
        "num_low_p_first_high_p_second_hits",
    ]:
        summary[col] = np.nan
    if not topk.empty:
        for idx, row in summary.iterrows():
            method = str(row["method"])
            k = int(row["K"])
            subset = topk.loc[topk["method"].eq(method) & topk["rank"].le(k)].copy()
            if len(subset) < k:
                continue
            subset = subset.set_index("path")
            enriched = subset.join(score_by_path[["p_shed_first", "p_shed_second", "critical"]], rsuffix="_score", how="left")
            p_first = enriched.get("p_shed_first_score", enriched.get("p_shed_first"))
            p_second = enriched.get("p_shed_second_score", enriched.get("p_shed_second"))
            critical = coerce_bool(enriched.get("critical_score", enriched.get("critical")))
            summary.at[idx, "mean_p_first_topk"] = float(pd.to_numeric(p_first, errors="coerce").mean())
            summary.at[idx, "median_p_first_topk"] = float(pd.to_numeric(p_first, errors="coerce").median())
            summary.at[idx, "mean_p_second_topk"] = float(pd.to_numeric(p_second, errors="coerce").mean())
            summary.at[idx, "median_p_second_topk"] = float(pd.to_numeric(p_second, errors="coerce").median())
            summary.at[idx, "num_low_p_first_high_p_second_hits"] = int(
                (critical & pd.to_numeric(p_first, errors="coerce").lt(LOW_P_FIRST_THRESHOLD) & pd.to_numeric(p_second, errors="coerce").gt(HIGH_P_SECOND_THRESHOLD)).sum()
            )
    keep = [
        "method",
        "alpha",
        "epsilon",
        "budget_type",
        "budget_label",
        "K",
        "search_budget_ratio",
        "critical_hit_count",
        "relay_cascade_hit_count",
        "recall_critical",
        "recall_relay_cascade",
        "precision_at_k",
        "captured_total_load_shed_mw",
        "captured_total_load_shed_ratio",
        "captured_relay_cascade_load_shed_mw",
        "captured_relay_cascade_load_shed_ratio",
        "mean_p_first_topk",
        "median_p_first_topk",
        "mean_p_second_topk",
        "median_p_second_topk",
        "num_low_p_first_high_p_second_hits",
    ]
    return summary[[col for col in keep if col in summary.columns]]


def select_best_configs(summary: pd.DataFrame) -> pd.DataFrame:
    alpha_rows = summary.loc[summary["method"].astype(str).str.startswith("alpha_path_prob_")].copy()
    criteria = [
        ("best_by_critical_hits_at_1000", 1000, "critical_hit_count"),
        ("best_by_precision_at_1000", 1000, "precision_at_k"),
        ("best_by_recall_at_5000", 5000, "recall_critical"),
        ("best_by_relay_hits_at_1000", 1000, "relay_cascade_hit_count"),
        ("best_by_captured_load_shed_at_1000", 1000, "captured_total_load_shed_mw"),
    ]
    rows = []
    for criterion, k, metric in criteria:
        subset = alpha_rows.loc[alpha_rows["K"].eq(k)].copy()
        if subset.empty and not alpha_rows.empty:
            available_k = int(alpha_rows["K"].max())
            subset = alpha_rows.loc[alpha_rows["K"].eq(available_k)].copy()
        if subset.empty:
            continue
        subset = subset.sort_values(
            [metric, "critical_hit_count", "relay_cascade_hit_count", "precision_at_k", "method"],
            ascending=[False, False, False, False, True],
        )
        row = subset.iloc[0].to_dict()
        row["criterion"] = criterion
        rows.append(row)
    cols = [
        "criterion",
        "alpha",
        "epsilon",
        "method",
        "K",
        "critical_hit_count",
        "recall_critical",
        "precision_at_k",
        "relay_cascade_hit_count",
        "recall_relay_cascade",
        "captured_total_load_shed_mw",
        "mean_p_first_topk",
        "mean_p_second_topk",
    ]
    return pd.DataFrame(rows)[cols] if rows else pd.DataFrame(columns=cols)


def build_heatmap_data(summary: pd.DataFrame) -> pd.DataFrame:
    alpha_rows = summary.loc[summary["method"].astype(str).str.startswith("alpha_path_prob_")].copy()
    return alpha_rows.loc[alpha_rows["K"].isin([1000, 5000])][
        [
            "method",
            "alpha",
            "epsilon",
            "K",
            "critical_hit_count",
            "recall_critical",
            "precision_at_k",
            "relay_cascade_hit_count",
            "recall_relay_cascade",
            "captured_total_load_shed_mw",
            "mean_p_first_topk",
            "mean_p_second_topk",
        ]
    ].sort_values(["K", "alpha", "epsilon"])


def build_vs_baselines(summary: pd.DataFrame, best_configs: pd.DataFrame) -> pd.DataFrame:
    key_methods = ["random", "line_order", "LODF_yP", "PFW", STRICT_PATH_PROB_METHOD, SECOND_ONLY_METHOD]
    best_methods = best_configs["method"].dropna().astype(str).unique().tolist() if not best_configs.empty else []
    key_methods.extend([method for method in best_methods if method not in key_methods])
    rows = []
    strict = summary.loc[summary["method"].eq(STRICT_PATH_PROB_METHOD)][["K", "critical_hit_count"]].rename(columns={"critical_hit_count": "strict_critical_hit_count"})
    second = summary.loc[summary["method"].eq(SECOND_ONLY_METHOD)][["K", "critical_hit_count"]].rename(columns={"critical_hit_count": "second_only_critical_hit_count"})
    for method in key_methods:
        subset = summary.loc[summary["method"].eq(method)].copy()
        if subset.empty:
            continue
        subset = subset.merge(strict, on="K", how="left").merge(second, on="K", how="left")
        subset["critical_hits_vs_strict"] = subset["critical_hit_count"] - subset["strict_critical_hit_count"]
        subset["critical_hits_vs_second_only"] = subset["critical_hit_count"] - subset["second_only_critical_hit_count"]
        rows.append(subset)
    return pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()


def build_curve_points(ranked_frames: dict[str, pd.DataFrame], budgets: pd.DataFrame, methods: list[str]) -> pd.DataFrame:
    rows = []
    for method in methods:
        if method not in ranked_frames:
            continue
        ranked = ranked_frames[method]
        for k in sorted(set(int(v) for v in budgets["K"])):
            top = ranked.head(k)
            rows.append(
                {
                    "method": method,
                    "candidate_evaluations": k,
                    "critical_paths_found": int(top["critical"].sum()),
                    "relay_cascade_paths_found": int(top["relay_cascade"].sum()),
                    "captured_load_shed_mw": float(top["total_load_shed_mw"].sum()),
                }
            )
    return pd.DataFrame(rows)


def build_topk_paths(ranked_frames: dict[str, pd.DataFrame], methods: list[str], max_rows: int) -> pd.DataFrame:
    rows = []
    for method in methods:
        if method not in ranked_frames:
            continue
        top = ranked_frames[method].head(max_rows).copy()
        top.insert(0, "rank", np.arange(1, len(top) + 1))
        top.insert(0, "method", method)
        rows.append(top)
    if not rows:
        return pd.DataFrame()
    keep = [
        "method",
        "rank",
        "path",
        "first_line",
        "second_line",
        "score_alpha",
        "p_shed_first",
        "p_shed_second",
        "path_product_score",
        "critical",
        "relay_cascade",
        "critical_mechanism",
        "total_load_shed_mw",
    ]
    return pd.concat(rows, ignore_index=True, sort=False)[[col for col in keep if col in pd.concat(rows, ignore_index=True, sort=False).columns]]


def run_alpha_sweep(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    score = build_score_table(args)
    budgets = make_budget_table(len(score), args.k_values, args.ratio_k_values)
    summary, ranked_frames = evaluate_alpha_sweep(
        score,
        alphas=args.alphas,
        epsilons=args.epsilons,
        budgets=budgets,
        random_seeds=args.random_seeds,
        method_suffix=args.method_suffix,
    )
    external = load_external_baseline_rows(score, budgets, args.baseline_summary_csv, args.baseline_topk_paths_csv)
    if not external.empty:
        summary = pd.concat([summary, external], ignore_index=True, sort=False)
    summary = summary.sort_values(["method", "K"]).reset_index(drop=True)
    best = select_best_configs(summary)
    heatmap = build_heatmap_data(summary)
    vs_baselines = build_vs_baselines(summary, best)
    selected_methods = [
        STRICT_PATH_PROB_METHOD,
        SECOND_ONLY_METHOD,
        "line_order",
    ] + best["method"].dropna().astype(str).unique().tolist()
    selected_methods = list(dict.fromkeys(selected_methods))
    curve = build_curve_points(ranked_frames, budgets, selected_methods)
    topk = build_topk_paths(ranked_frames, selected_methods, args.topk_output_rows)

    summary_path = args.output_dir / "alpha_path_prob_sweep_summary.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    write_json(args.output_dir / "alpha_path_prob_sweep_summary.json", summary.to_dict("records"))
    curve.to_csv(args.output_dir / "alpha_path_prob_sweep_curve_points_sparse.csv", index=False, encoding="utf-8-sig")
    topk.to_csv(args.output_dir / "alpha_path_prob_sweep_topk_paths.csv", index=False, encoding="utf-8-sig")
    best.to_csv(args.output_dir / "alpha_path_prob_sweep_best_configs.csv", index=False, encoding="utf-8-sig")
    vs_baselines.to_csv(args.output_dir / "alpha_path_prob_vs_baselines_at_keyK.csv", index=False, encoding="utf-8-sig")
    heatmap.to_csv(args.output_dir / "alpha_path_prob_heatmap_data.csv", index=False, encoding="utf-8-sig")
    config = {
        "score_table_csv": str(args.score_table_csv),
        "score_table_used": bool(args.score_table_csv.exists()),
        "fulltruth_csv": str(args.fulltruth_csv),
        "output_dir": str(args.output_dir),
        "num_paths": int(len(score)),
        "num_critical_paths": int(score["critical"].sum()),
        "num_relay_cascade_paths": int(score["relay_cascade"].sum()),
        "alphas": [float(v) for v in args.alphas],
        "epsilons": [float(v) for v in args.epsilons],
        "k_values": [int(v) for v in args.k_values],
        "ratio_k_values": [float(v) for v in args.ratio_k_values],
        "scoring_rule": "score_alpha = (epsilon + p_first(Li|S0))^alpha * p_second(Lj|S1(i)); alpha=0 uses p_second exactly.",
        "no_retraining": True,
        "no_opa_rerun": True,
    }
    write_json(args.output_dir / "alpha_path_prob_sweep_config.json", config)
    readme = [
        "# IEEE118 Alpha Path-Probability Sweep",
        "",
        "This compact run reuses existing PR #14/#15 pilot-2000 model scores. It does not retrain the GCN, rerun OPA, or modify Algorithm 1.",
        "",
        f"- Paths evaluated: {len(score)}",
        f"- Critical paths: {int(score['critical'].sum())}",
        f"- Relay-cascade paths: {int(score['relay_cascade'].sum())}",
        f"- Score table used: `{args.score_table_csv}`",
        "",
        "Scoring rule:",
        "",
        "`score_alpha(Li -> Lj) = (epsilon + p_first(Li | S0))^alpha * p_second(Lj | S1(i))`",
        "",
        "- `alpha=1, epsilon=0` is the strict paper-aligned path probability.",
        "- `alpha=0` is exactly the second-step-only ablation, independent of epsilon.",
        "- Intermediate `alpha` values soften the first-step probability from a hard multiplicative gate into a ranking prior.",
    ]
    if not best.empty:
        for _, row in best.iterrows():
            readme.append(
                f"- {row['criterion']}: `{row['method']}` at K={int(row['K'])}, "
                f"critical hits={float(row['critical_hit_count']):.0f}, precision={float(row['precision_at_k']):.3f}."
            )
    (args.output_dir / "alpha_path_prob_sweep_readme.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    return {
        "summary_csv": str(summary_path),
        "best_configs": best.to_dict("records"),
        "num_paths": int(len(score)),
        "num_critical_paths": int(score["critical"].sum()),
        "num_relay_cascade_paths": int(score["relay_cascade"].sum()),
    }


def main() -> None:
    print(json.dumps(json_ready(run_alpha_sweep(parse_args())), indent=2))


if __name__ == "__main__":
    main()
