from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(IEEE118_DIR))

from analyze_ieee118_n1_residual_n2 import (
    FIXED_BUDGETS,
    annotate_n1_residual,
    evaluate_ranking,
    load_first_step_summary,
)
from evaluate_ieee118_rts79_protocol_search import (
    build_y_p_scores,
    load_truth,
    make_path_score_table,
    predict_s1_probabilities,
)


METHOD_PATH = "N1_gate_plus_RTS79_residual_reachable_GCN_path_prob"
METHOD_SECOND = "N1_gate_plus_RTS79_residual_reachable_GCN_second_only"
METHOD_RESIDUAL_PATH = "RTS79_residual_reachable_GCN_path_prob_residual_only"
METHOD_RESIDUAL_SECOND = "RTS79_residual_reachable_GCN_second_only_residual_only"
METHOD_GATED_LINE_ORDER = "N1_gate_plus_line_order"
METHOD_GATED_LODF = "N1_gate_plus_LODF_yP"
METHOD_GATED_RANDOM = "N1_gate_plus_random"

DEFAULT_EVAL_DATA = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"
)
DEFAULT_TRUTH = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
    / "ieee118_fulltruth_summary.csv"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate N-1-gated IEEE118 residual reachable GCN rankings.")
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_EVAL_DATA / "ieee118_rts79_gcn_dataset.npz")
    parser.add_argument("--path-index-csv", type=Path, default=DEFAULT_EVAL_DATA / "ieee118_rts79_gcn_path_index.csv")
    parser.add_argument("--fulltruth-csv", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument("--first-step-summary-csv", type=Path, default=None)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--first-step-probabilities-csv", type=Path, required=True)
    parser.add_argument("--feature-normalizer-json", type=Path, required=True)
    parser.add_argument("--random-seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument("--include-lodf", action="store_true")
    parser.add_argument("--seed", type=int, default=20260708)
    parser.add_argument("--load-scale", type=float, default=1.0)
    parser.add_argument("--limit-mode", choices=["original_rate_a", "flow_scaled"], default="flow_scaled")
    parser.add_argument("--flow-limit-scale", type=float, default=8.0)
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--topk-output-rows", type=int, default=5000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_n1_residual_reachable_gcn" / "evaluation",
    )
    return parser.parse_args(argv)


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}. This evaluator will not regenerate large local data.")


def extended_budgets(total_paths: int) -> list[int]:
    values = {min(int(value), total_paths) for value in FIXED_BUDGETS if value > 0}
    values.update(
        max(1, min(total_paths, int(round(total_paths * ratio))))
        for ratio in (0.005, 0.01, 0.02, 0.05, 0.065, 0.10, 0.15, 0.20)
    )
    values.add(total_paths)
    return sorted(values)


def order_n1_gated(score: pd.DataFrame, score_column: str) -> pd.DataFrame:
    ranked = score.copy()
    ranked[score_column] = pd.to_numeric(ranked[score_column], errors="coerce").fillna(-np.inf)
    return ranked.sort_values(
        ["n1_second", score_column, "p_shed_second", "path"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def apply_n1_gate(ranked: pd.DataFrame) -> pd.DataFrame:
    """Move the physical N-1 tier first while preserving the baseline order within each tier."""
    if "n1_second" not in ranked:
        raise ValueError("N-1-gated ranking requires an n1_second column.")
    tier_a = ranked.loc[ranked["n1_second"].astype(bool)]
    residual = ranked.loc[~ranked["n1_second"].astype(bool)]
    return pd.concat([tier_a, residual], ignore_index=True)


def make_lodf_ranked(
    score: pd.DataFrame,
    first_scores: dict[str, float],
    second_scores: dict[str, dict[str, float]],
) -> pd.DataFrame:
    paths: list[str] = []
    first_lines = sorted(
        score["first_line"].astype(str).unique(),
        key=lambda line: (-float(first_scores.get(line, -np.inf)), line),
    )
    for first_line in first_lines:
        group = score.loc[score["first_line"].astype(str).eq(first_line)].copy()
        group["lodf_y_p_second"] = group["second_line"].map(
            lambda second: float(second_scores.get(first_line, {}).get(str(second), -np.inf))
        )
        group = group.sort_values(["lodf_y_p_second", "second_line"], ascending=[False, True])
        paths.extend(group["path"].astype(str).tolist())
    return score.set_index("path").reindex(paths).dropna(subset=["first_line"]).reset_index()


def evaluate_at_budgets(method: str, ranked: pd.DataFrame, *, universe: str, n1_cost: int) -> pd.DataFrame:
    total_critical = int(ranked["critical"].sum())
    total_relay = int(ranked["relay_cascade"].sum())
    total_island = int(ranked["island_only"].sum())
    rows: list[dict[str, Any]] = []
    for k in extended_budgets(len(ranked)):
        top = ranked.head(k)
        critical_hits = int(top["critical"].sum())
        relay_hits = int(top["relay_cascade"].sum())
        island_hits = int(top["island_only"].sum())
        rows.append(
            {
                "method": method,
                "universe": universe,
                "K": k,
                "candidate_path_evaluations": k,
                "n1_prescreen_evaluations": int(n1_cost),
                "total_physical_evaluations": int(k + n1_cost),
                "search_budget_ratio": k / max(len(ranked), 1),
                "critical_hit_count": critical_hits,
                "recall_critical": critical_hits / max(total_critical, 1),
                "precision_at_k": critical_hits / max(k, 1),
                "relay_cascade_hit_count": relay_hits,
                "recall_relay_cascade": relay_hits / max(total_relay, 1),
                "island_only_hit_count": island_hits,
                "recall_island_only": island_hits / max(total_island, 1),
                "captured_load_shed_mw": float(top["total_load_shed_mw"].sum()),
            }
        )
    return pd.DataFrame(rows)


def sparse_curve(method: str, ranked: pd.DataFrame, *, n1_cost: int) -> pd.DataFrame:
    points = set(extended_budgets(len(ranked)))
    points.update(range(50, min(1000, len(ranked)) + 1, 50))
    points.update(range(1500, len(ranked) + 1, 500))
    critical = ranked["critical"].to_numpy(dtype=bool)
    relay = ranked["relay_cascade"].to_numpy(dtype=bool)
    island = ranked["island_only"].to_numpy(dtype=bool)
    shed = ranked["total_load_shed_mw"].to_numpy(dtype=float)
    c_critical = np.cumsum(critical)
    c_relay = np.cumsum(relay)
    c_island = np.cumsum(island)
    c_shed = np.cumsum(shed)
    rows = []
    for k in sorted(value for value in points if 0 < value <= len(ranked)):
        rows.append(
            {
                "method": method,
                "candidate_evaluations": k,
                "total_physical_evaluations": int(k + n1_cost),
                "critical_paths_found": int(c_critical[k - 1]),
                "relay_cascade_paths_found": int(c_relay[k - 1]),
                "island_only_paths_found": int(c_island[k - 1]),
                "captured_load_shed_mw": float(c_shed[k - 1]),
            }
        )
    return pd.DataFrame(rows)


def random_summary(
    truth: pd.DataFrame,
    seeds: list[int],
    *,
    n1_cost: int,
    gated: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_parts = []
    curve_parts = []
    paths = truth["path"].astype(str).tolist()
    indexed = truth.set_index("path")
    for seed in seeds:
        order = list(paths)
        random.Random(seed).shuffle(order)
        ranked = indexed.reindex(order).reset_index()
        if gated:
            ranked = apply_n1_gate(ranked)
        seed_method = f"{'N1_gate_plus_' if gated else ''}random_seed_{seed}"
        summary_parts.append(evaluate_at_budgets(seed_method, ranked, universe="full", n1_cost=n1_cost))
        curve_parts.append(sparse_curve(seed_method, ranked, n1_cost=n1_cost))
    raw = pd.concat(summary_parts, ignore_index=True)
    group_columns = [
        "universe",
        "K",
        "candidate_path_evaluations",
        "n1_prescreen_evaluations",
        "total_physical_evaluations",
        "search_budget_ratio",
    ]
    metric_columns = [name for name in raw.columns if name not in {"method", *group_columns}]
    rows = []
    for keys, group in raw.groupby(group_columns, sort=True):
        row = {"method": METHOD_GATED_RANDOM if gated else "random", **dict(zip(group_columns, keys))}
        for name in metric_columns:
            values = pd.to_numeric(group[name], errors="coerce")
            row[name] = float(values.mean())
            row[f"{name}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        rows.append(row)
    curve_raw = pd.concat(curve_parts, ignore_index=True)
    curve_metrics = [
        "critical_paths_found",
        "relay_cascade_paths_found",
        "island_only_paths_found",
        "captured_load_shed_mw",
    ]
    curve_rows = []
    for keys, group in curve_raw.groupby(["candidate_evaluations", "total_physical_evaluations"], sort=True):
        row = {
            "method": METHOD_GATED_RANDOM if gated else "random",
            "candidate_evaluations": int(keys[0]),
            "total_physical_evaluations": int(keys[1]),
        }
        for name in curve_metrics:
            row[name] = float(group[name].mean())
            row[f"{name}_std"] = float(group[name].std(ddof=1)) if len(group) > 1 else 0.0
        curve_rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(curve_rows)


def random_threshold_summary(
    truth: pd.DataFrame,
    seeds: list[int],
    *,
    n1_cost: int,
    gated: bool,
) -> dict[str, Any]:
    indexed = truth.set_index("path")
    paths = truth["path"].astype(str).tolist()
    per_seed = []
    for seed in seeds:
        order = list(paths)
        random.Random(seed).shuffle(order)
        ranked = indexed.reindex(order).reset_index()
        if gated:
            ranked = apply_n1_gate(ranked)
        _, threshold = evaluate_ranking(f"random_seed_{seed}", ranked, universe="full")
        per_seed.append(threshold)
    result: dict[str, Any] = {
        "method": METHOD_GATED_RANDOM if gated else "random",
        "universe": "full",
        "total_paths": int(len(truth)),
        "total_critical": int(truth["critical"].sum()),
        "n1_prescreen_evaluations": int(n1_cost),
        "num_random_seeds": int(len(seeds)),
    }
    for label in ("K90", "K95", "K99", "K100"):
        values = np.asarray([row[label] for row in per_seed if row.get(label) is not None], dtype=float)
        result[label] = float(values.mean()) if len(values) else None
        result[f"{label}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        result[f"total_physical_{label}"] = (
            float(values.mean() + n1_cost) if len(values) else None
        )
        result[f"total_physical_{label}_std"] = result[f"{label}_std"]
    return result


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in (
        (args.dataset_npz, "full IEEE118 GCN evaluation dataset NPZ"),
        (args.path_index_csv, "full IEEE118 path index CSV"),
        (args.fulltruth_csv, "early-stop IEEE118 full-truth CSV"),
        (args.model_path, "residual reachable GCN checkpoint"),
        (args.first_step_probabilities_csv, "residual S0 probability CSV"),
        (args.feature_normalizer_json, "training feature normalizer JSON"),
    ):
        require_file(path, label)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    first_path = args.first_step_summary_csv or args.fulltruth_csv.with_name("ieee118_first_step_summary.csv")
    truth = load_truth(args.fulltruth_csv)
    truth["island_only"] = truth["critical_mechanism"].fillna("").astype(str).eq("island_only")
    first = load_first_step_summary(first_path)
    annotated = annotate_n1_residual(truth, first)
    n1_cost = int(first.groupby([name for name in ("scenario_id", "seed") if name in first]).size().median())

    s1_probability, _ = predict_s1_probabilities(
        args.dataset_npz,
        args.model_path,
        args.feature_normalizer_json,
    )
    score = make_path_score_table(
        args.path_index_csv,
        args.first_step_probabilities_csv,
        s1_probability,
        truth,
    )
    extra = annotated[
        ["path", "critical", "relay_cascade", "island_only", "total_load_shed_mw", "n1_second", "residual_ordered_n2"]
    ]
    score = score.drop(
        columns=["critical", "relay_cascade", "total_load_shed_mw"],
        errors="ignore",
    ).merge(extra, on="path", how="inner", validate="one_to_one")
    if len(score) != len(truth):
        raise ValueError(f"Model/path index covers {len(score)} paths but valid truth contains {len(truth)}.")
    score["residual_path_score"] = score["p_shed_first"] * score["p_shed_second"]

    ranked_by_method: dict[str, tuple[pd.DataFrame, str, int]] = {
        METHOD_PATH: (order_n1_gated(score, "residual_path_score"), "full", n1_cost),
        METHOD_SECOND: (order_n1_gated(score, "p_shed_second"), "full", n1_cost),
        METHOD_RESIDUAL_PATH: (
            score.loc[score["residual_ordered_n2"]]
            .sort_values(["residual_path_score", "p_shed_second", "path"], ascending=[False, False, True])
            .reset_index(drop=True),
            "residual",
            n1_cost,
        ),
        METHOD_RESIDUAL_SECOND: (
            score.loc[score["residual_ordered_n2"]]
            .sort_values(["p_shed_second", "path"], ascending=[False, True])
            .reset_index(drop=True),
            "residual",
            n1_cost,
        ),
        "line_order": (score.reset_index(drop=True), "full", 0),
        METHOD_GATED_LINE_ORDER: (apply_n1_gate(score.reset_index(drop=True)), "full", n1_cost),
    }
    lodf_status: dict[str, Any] = {"status": "not_run", "reason": "Pass --include-lodf to compute it."}
    if args.include_lodf:
        y_p_first, y_p_second = build_y_p_scores(args)
        lodf_ranked = make_lodf_ranked(score, y_p_first, y_p_second)
        ranked_by_method["LODF_yP"] = (lodf_ranked, "full", 0)
        ranked_by_method[METHOD_GATED_LODF] = (apply_n1_gate(lodf_ranked), "full", n1_cost)
        lodf_status = {"status": "complete", "num_ranked_paths": int(len(lodf_ranked))}

    summaries = []
    curves = []
    thresholds = []
    for method, (ranked, universe, cost) in ranked_by_method.items():
        summaries.append(evaluate_at_budgets(method, ranked, universe=universe, n1_cost=cost))
        curves.append(sparse_curve(method, ranked, n1_cost=cost))
        _, threshold = evaluate_ranking(method, ranked, universe=universe)
        threshold["n1_prescreen_evaluations"] = cost
        for label in ("K90", "K95", "K99", "K100"):
            threshold[f"total_physical_{label}"] = (
                int(threshold[label] + cost) if threshold.get(label) is not None else None
            )
        thresholds.append(threshold)
    random_rows, random_curve = random_summary(truth, args.random_seeds, n1_cost=0)
    gated_random_rows, gated_random_curve = random_summary(
        annotated,
        args.random_seeds,
        n1_cost=n1_cost,
        gated=True,
    )
    summaries.append(random_rows)
    summaries.append(gated_random_rows)
    curves.append(random_curve)
    curves.append(gated_random_curve)
    thresholds.append(random_threshold_summary(truth, args.random_seeds, n1_cost=0, gated=False))
    thresholds.append(random_threshold_summary(annotated, args.random_seeds, n1_cost=n1_cost, gated=True))

    summary_table = pd.concat(summaries, ignore_index=True, sort=False)
    curve_table = pd.concat(curves, ignore_index=True, sort=False)
    summary_table.to_csv(args.output_dir / "ieee118_n1_gated_search_summary.csv", index=False, encoding="utf-8-sig")
    curve_table.to_csv(args.output_dir / "ieee118_n1_gated_curve_points.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "ieee118_n1_gated_thresholds.json").write_text(
        json.dumps(thresholds, indent=2),
        encoding="utf-8",
    )
    top_parts = []
    for method in (METHOD_PATH, METHOD_SECOND):
        ranked = ranked_by_method[method][0].head(args.topk_output_rows).copy()
        ranked.insert(0, "method", method)
        ranked.insert(1, "rank", np.arange(1, len(ranked) + 1))
        top_parts.append(ranked)
    pd.concat(top_parts, ignore_index=True).to_csv(
        args.output_dir / "ieee118_n1_gated_topk_paths.csv",
        index=False,
        encoding="utf-8-sig",
    )
    config = {
        "status": "complete",
        "model_class": "PaperStyleRts79Gcn",
        "model_path": str(args.model_path),
        "feature_normalizer_json": str(args.feature_normalizer_json),
        "fulltruth_csv": str(args.fulltruth_csv),
        "num_valid_paths": int(len(truth)),
        "num_critical_paths": int(truth["critical"].sum()),
        "num_residual_paths": int(annotated["residual_ordered_n2"].sum()),
        "num_residual_critical_paths": int(annotated.loc[annotated["residual_ordered_n2"], "critical"].sum()),
        "n1_prescreen_evaluations": n1_cost,
        "random_seeds": [int(value) for value in args.random_seeds],
        "methods": list(ranked_by_method) + ["random", METHOD_GATED_RANDOM],
        "lodf_y_p": lodf_status,
        "thresholds": thresholds,
        "large_predictions_tracked_in_git": False,
    }
    (args.output_dir / "ieee118_n1_gated_search_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (args.output_dir / "ieee118_n1_gated_search_readme.md").write_text(
        "# IEEE118 N-1-Gated Residual Reachable GCN Evaluation\n\n"
        "The original 32,560-row early-stop truth remains unchanged. Paths ending in an S0 N-1-critical line are "
        "evaluated as Tier A; all remaining paths use residual reachable GCN scores. N-1 prescreen and N-2 candidate "
        "evaluation costs are reported separately. Fair hierarchical random, line-order, and optional LODF_yP "
        "baselines receive the same N-1 gate.\n",
        encoding="utf-8",
    )
    return config


def main() -> None:
    args = parse_args()
    print(json.dumps(evaluate(args), indent=2))


if __name__ == "__main__":
    main()
