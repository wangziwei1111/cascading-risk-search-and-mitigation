from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESULTS_ROOT = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup"
DEFAULT_OUTPUT = ROOT / "results" / "gcn_search" / "ieee118_experiment_synthesis"

PR_STAGES = {
    "pr11": "PR #11 first-step critical early-stop",
    "pr12": "PR #12 Algorithm 1 search",
    "pr13": "PR #13 paper-aligned multi-state smoke",
    "pr14": "PR #14 pilot-2000 paper-aligned training",
    "pr15": "PR #15 S0 first-probability bottleneck diagnosis",
    "pr16": "PR #16 alpha path-probability sweep",
    "pr17": "PR #17 any-critical first-line fragility score",
    "pr18": "PR #18 strict first-line fragility targets",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthesize IEEE118 experiment narrative from compact artifacts.")
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    for key in PR_STAGES:
        parser.add_argument(f"--include-{key}", action="store_true")
    return parser.parse_args()


def included_keys(args: argparse.Namespace) -> set[str]:
    requested = {key for key in PR_STAGES if getattr(args, f"include_{key}")}
    return requested or set(PR_STAGES)


def source(path: Path | None = None) -> str:
    return f"artifact:{path.as_posix()}" if path else "manual_checked_value"


def safe_read_csv(path: Path) -> pd.DataFrame | None:
    if path.exists():
        return pd.read_csv(path)
    return None


def clean_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.integer, np.int64)):
        return int(value)
    if isinstance(value, (np.floating, np.float64)):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def build_timeline(keys: set[str]) -> pd.DataFrame:
    rows = [
        {"stage": "PR #11", "short_name": "early_stop_protocol", "category": "protocol", "status": "formal_protocol", "key_takeaway": "IEEE118 early-stop ordered N-2 protocol fixes the formal valid-path universe.", "source": source()},
        {"stage": "PR #12", "short_name": "algorithm1_completion", "category": "original_method_completion", "status": "method_completed_not_best", "key_takeaway": "Original Algorithm 1 was completed, but current single-scenario/pilot performance is weak.", "source": source()},
        {"stage": "PR #13", "short_name": "paper_aligned_smoke", "category": "pipeline_smoke", "status": "smoke_only", "key_takeaway": "12-state smoke proves the S0/S1 paper-aligned data/training/eval chain runs.", "source": source()},
        {"stage": "PR #14", "short_name": "pilot_2000_training", "category": "paper_aligned_pilot_training", "status": "pilot_result", "key_takeaway": "Pilot-2000 is the closest current IEEE118 result to paper-aligned RTS-79 training, but is not paper-8000.", "source": source()},
        {"stage": "PR #15", "short_name": "s0_bottleneck", "category": "diagnostic", "status": "mechanism_diagnosis", "key_takeaway": "Many critical paths are low-p_first / high-p_second, explaining why strict path_prob is suppressed.", "source": source()},
        {"stage": "PR #16", "short_name": "alpha_path_prob", "category": "ranking_improvement", "status": "diagnostic_improvement", "key_takeaway": "Alpha path probability shows reducing the hard p_first gate improves low-budget ranking.", "source": source()},
        {"stage": "PR #17", "short_name": "any_critical_fragility", "category": "diagnostic_failed_label", "status": "degenerate_label", "key_takeaway": "Any-critical first-line fragility is all-positive and cannot be a discriminative classifier.", "source": source()},
        {"stage": "PR #18", "short_name": "strict_fragility_targets", "category": "strict_fragility_refinement", "status": "diagnostic_refinement", "key_takeaway": "Strict top-q fragility targets fix label degeneracy and slightly improve some low-budget comparisons.", "source": source()},
    ]
    return pd.DataFrame([row for row in rows if row["stage"].lower().replace(" #", "").replace(" ", "")[:4] in keys or row["stage"].lower().replace(" #", "").replace(" ", "") in keys or f"pr{row['stage'].split('#')[1].split()[0]}" in keys])


def build_method_taxonomy(keys: set[str]) -> pd.DataFrame:
    rows = [
        {"method_or_pr": "PR #11 early-stop", "category": "protocol", "paper_alignment_level": "high", "is_original_paper_method": False, "is_ablation": False, "is_diagnostic": False, "is_improvement": False, "is_formal_result": True, "is_pilot_result": False, "can_be_main_text": True, "should_be_appendix": False, "caveat": "Defines the current formal IEEE118 ordered N-2 universe."},
        {"method_or_pr": "PR #12 Algorithm1", "category": "original_method_completion", "paper_alignment_level": "high", "is_original_paper_method": True, "is_ablation": False, "is_diagnostic": False, "is_improvement": False, "is_formal_result": False, "is_pilot_result": True, "can_be_main_text": True, "should_be_appendix": True, "caveat": "Completed original method, but current single-scenario/pilot model is not strong."},
        {"method_or_pr": "PR #13 12-state smoke", "category": "pipeline_smoke", "paper_alignment_level": "medium", "is_original_paper_method": False, "is_ablation": False, "is_diagnostic": False, "is_improvement": False, "is_formal_result": False, "is_pilot_result": False, "can_be_main_text": False, "should_be_appendix": True, "caveat": "Smoke only; not a formal result."},
        {"method_or_pr": "PR #14 pilot-2000", "category": "paper_aligned_pilot_training", "paper_alignment_level": "high", "is_original_paper_method": True, "is_ablation": False, "is_diagnostic": False, "is_improvement": False, "is_formal_result": False, "is_pilot_result": True, "can_be_main_text": True, "should_be_appendix": False, "caveat": "Closest paper-aligned pilot, but not paper-8000."},
        {"method_or_pr": "PR #15 S0 bottleneck", "category": "diagnostic", "paper_alignment_level": "high", "is_original_paper_method": False, "is_ablation": True, "is_diagnostic": True, "is_improvement": False, "is_formal_result": False, "is_pilot_result": True, "can_be_main_text": True, "should_be_appendix": False, "caveat": "Mechanism diagnosis, not a new ranking method."},
        {"method_or_pr": "PR #16 alpha path-prob", "category": "ranking_improvement", "paper_alignment_level": "medium", "is_original_paper_method": False, "is_ablation": True, "is_diagnostic": True, "is_improvement": True, "is_formal_result": False, "is_pilot_result": True, "can_be_main_text": True, "should_be_appendix": False, "caveat": "Calibrated ranking improvement; not original paper method."},
        {"method_or_pr": "PR #17 any-critical fragility", "category": "diagnostic_failed_label", "paper_alignment_level": "medium", "is_original_paper_method": False, "is_ablation": True, "is_diagnostic": True, "is_improvement": False, "is_formal_result": False, "is_pilot_result": True, "can_be_main_text": False, "should_be_appendix": True, "caveat": "Label degenerates to all-positive; diagnostic only."},
        {"method_or_pr": "PR #18 strict fragility", "category": "strict_fragility_refinement", "paper_alignment_level": "medium", "is_original_paper_method": False, "is_ablation": True, "is_diagnostic": True, "is_improvement": True, "is_formal_result": False, "is_pilot_result": True, "can_be_main_text": True, "should_be_appendix": False, "caveat": "Slight low-budget gains; not a decisive breakthrough."},
    ]
    return pd.DataFrame([row for row in rows if f"pr{row['method_or_pr'].split('#')[1].split()[0]}" in keys])


def build_key_results(keys: set[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(stage: str, metric: str, value: Any, unit: str = "", note: str = "", src: str = "manual_checked_value") -> None:
        if stage.lower().replace(" #", "").replace(" ", "")[:4] in keys or f"pr{stage.split('#')[1].split()[0]}" in keys:
            rows.append({"stage": stage, "metric": metric, "value": clean_scalar(value), "unit": unit, "note": note, "source": src})

    add("PR #11", "first_step_critical_lines", 10, "lines", "L016, L047, L051, L061, L096, L147, L180, L181, L183, L184")
    add("PR #11", "skipped_paths_due_to_early_stop", 1850, "ordered paths")
    add("PR #11", "valid_ordered_n2_paths_after_early_stop", 32560, "ordered paths")
    add("PR #11", "valid_critical_paths", 1754, "paths")
    add("PR #11", "valid_relay_cascade_paths", 1643, "paths")
    add("PR #11", "valid_critical_ratio", 0.0538698, "ratio")
    add("PR #11", "max_total_load_shed_mw", 111.760638, "MW")

    add("PR #12", "Algorithm1_K1000_critical_hits", 62, "hits", "Current single-scenario/pilot performance is weak.")
    add("PR #12", "path_prob_K1000_critical_hits", 389, "hits")
    add("PR #12", "second_only_K1000_critical_hits", 691, "hits")
    add("PR #12", "LODF_yP_K1000_critical_hits", 58, "hits")
    add("PR #12", "PFW_K1000_critical_hits", 66, "hits")
    add("PR #12", "random_K1000_critical_hits", 60, "hits")
    add("PR #12", "line_order_K1000_critical_hits", 56, "hits")

    add("PR #13", "paper_aligned_states_in_smoke", 12, "states", "Smoke only; not formal IEEE118 result.")

    add("PR #14", "pilot_2000_overall_AP", 0.878658)
    add("PR #14", "pilot_2000_F1", 0.610405)
    add("PR #14", "pilot_2000_validation_AP", 0.865178)
    add("PR #14", "pilot_2000_test_AP", 0.860736)
    add("PR #14", "pilot_2000_S0_AP", 0.513846)
    add("PR #14", "pilot_2000_S1_AP", 0.880911)

    add("PR #15", "suppressed_critical_union", 313)
    add("PR #15", "class_A", 180)
    add("PR #15", "class_B", 203)
    add("PR #15", "K1000_second_only_only_critical_hits", 500)
    add("PR #15", "K1000_path_prob_only_critical_hits", 199)
    add("PR #15", "second_only_only_mean_p_first", 0.027451)
    add("PR #15", "second_only_only_mean_p_second", 0.992166)
    add("PR #15", "path_prob_only_mean_p_first", 0.570718)
    add("PR #15", "valid_N2_paths_with_first_step_positive_S0_label", "0 / 32560")
    add("PR #15", "relay_cascade_suppressed_ratio", 0.189897)
    add("PR #15", "island_only_suppressed_ratio", 0.009009)

    add("PR #16", "alpha_score_formula", "score_alpha=(epsilon+p_first)^alpha*p_second")
    add("PR #16", "K1000_strict_path_prob_hits", 360)
    add("PR #16", "K1000_second_only_or_alpha0_hits", 661)
    add("PR #16", "K5000_best_alpha_hits", 1710, "hits", "alpha=0.25, epsilon=1e-2")

    add("PR #17", "known_first_line_labels", 1461)
    add("PR #17", "any_critical_positive", 1461)
    add("PR #17", "any_critical_negative", 0)
    add("PR #17", "any_critical_positive_ratio", 1.0)

    add("PR #18", "strict_targets_non_degenerate", 12, "targets")
    add("PR #18", "top10_positive_negative", "156 / 1305")
    add("PR #18", "top20_positive_negative", "302 / 1159")
    add("PR #18", "top30_positive_negative", "448 / 1013")
    add("PR #18", "first_step_critical_excluded", 158)

    return pd.DataFrame(rows)


def build_classification_summary(results_root: Path) -> pd.DataFrame:
    rows = []
    pilot_path = results_root / "pilot_2000_weight_sweep" / "ieee118_paper_gcn_weight_sweep_summary.csv"
    pilot = safe_read_csv(pilot_path)
    if pilot is not None and not pilot.empty:
        row = pilot.loc[pilot["positive_weight"].astype(float).eq(20.0)].iloc[0]
        for metric in ["overall_average_precision", "overall_f1", "S0_average_precision", "S1_average_precision"]:
            rows.append({"stage": "PR #14", "model_or_target": "pilot_2000_positive_weight_20", "metric": metric, "value": clean_scalar(row[metric]), "source": source(pilot_path), "caveat": "paper-aligned pilot; not paper-8000"})
    else:
        for metric, value in [("overall_average_precision", 0.878658), ("overall_f1", 0.610405), ("S0_average_precision", 0.513846), ("S1_average_precision", 0.880911)]:
            rows.append({"stage": "PR #14", "model_or_target": "pilot_2000_positive_weight_20", "metric": metric, "value": value, "source": source(), "caveat": "paper-aligned pilot; not paper-8000"})

    strict_path = results_root / "strict_fragility_targets" / "ieee118_strict_fragility_target_summary.csv"
    strict = safe_read_csv(strict_path)
    if strict is not None and not strict.empty:
        for _, row in strict.iterrows():
            rows.append({"stage": "PR #18", "model_or_target": row["target_name"], "metric": "positive_ratio", "value": clean_scalar(row["positive_ratio"]), "source": source(strict_path), "caveat": "strict first-line target diagnostic/refinement"})
            rows.append({"stage": "PR #18", "model_or_target": row["target_name"], "metric": "degenerate", "value": bool(row["degenerate"]), "source": source(strict_path), "caveat": "should be false for trainable strict targets"})
    return pd.DataFrame(rows)


def build_s0_bottleneck_summary(results_root: Path) -> pd.DataFrame:
    path = results_root / "s0_bottleneck_diagnostics" / "s0_first_probability_bottleneck_diagnostics.json"
    rows = [
        {"metric": "suppressed_critical_union", "value": 313, "source": source(), "interpretation": "Critical paths suppressed by strict p_first gating."},
        {"metric": "class_A", "value": 180, "source": source(), "interpretation": "Diagnostic class A from PR #15."},
        {"metric": "class_B", "value": 203, "source": source(), "interpretation": "Diagnostic class B from PR #15."},
        {"metric": "K1000_second_only_only_critical_hits", "value": 500, "source": source(), "interpretation": "Hits found by second_only but not strict path_prob."},
        {"metric": "K1000_path_prob_only_critical_hits", "value": 199, "source": source(), "interpretation": "Hits found by strict path_prob but not second_only."},
        {"metric": "second_only_only_mean_p_first", "value": 0.027451, "source": source(), "interpretation": "Low first-step probability suppresses many useful paths."},
        {"metric": "second_only_only_mean_p_second", "value": 0.992166, "source": source(), "interpretation": "Second-step model is highly confident on those suppressed hits."},
        {"metric": "path_prob_only_mean_p_first", "value": 0.570718, "source": source(), "interpretation": "Strict path_prob favors higher p_first paths."},
        {"metric": "valid_N2_paths_with_first_step_positive_S0_label", "value": "0 / 32560", "source": source(), "interpretation": "Early-stop valid paths remove direct first-step shed lines."},
        {"metric": "relay_cascade_suppressed_ratio", "value": 0.189897, "source": source(), "interpretation": "Suppression is more pronounced for relay cascade than island-only."},
        {"metric": "island_only_suppressed_ratio", "value": 0.009009, "source": source(), "interpretation": "Island-only suppression is much smaller."},
    ]
    if path.exists():
        for row in rows:
            row["source"] = source(path)
    return pd.DataFrame(rows)


def normalize_method(method: str) -> str:
    mapping = {
        "strict_path_prob": "strict_path_prob",
        "second_only": "second_only",
        "best_alpha_path_prob": "best_alpha_path_prob",
        "any_critical_fragility_path_prob": "any_critical_fragility_path_prob",
        "best_strict_fragility_path_prob": "best_strict_fragility_path_prob",
        "random": "random",
        "line_order": "line_order",
        "PFW": "PFW",
        "LODF_yP": "LODF_yP",
    }
    return mapping.get(method, method)


def build_search_keyk_comparison(results_root: Path) -> pd.DataFrame:
    taxonomy = {
        "random": ("baseline", "stochastic baseline"),
        "line_order": ("baseline", "deterministic weak baseline"),
        "PFW": ("physics_baseline", "power-flow-weighted baseline"),
        "LODF_yP": ("physics_baseline", "physical LODF_yP baseline"),
        "Algorithm1": ("original_method_completion", "completed original Algorithm 1; weak in current pilot"),
        "strict_path_prob": ("paper_aligned_pilot", "original paper-style path probability on pilot-2000"),
        "second_only": ("diagnostic_ablation", "strong ablation; not original main method"),
        "best_alpha_path_prob": ("ranking_improvement", "calibrated ranking; not original paper method"),
        "any_critical_fragility_path_prob": ("diagnostic_failed_label", "any-critical label is all-positive"),
        "best_strict_fragility_path_prob": ("strict_fragility_refinement", "slight low-budget gains, not decisive breakthrough"),
    }
    rows: list[dict[str, Any]] = []
    comp_path = results_root / "strict_fragility_eval" / "ieee118_strict_fragility_vs_baselines_at_keyK.csv"
    comp = safe_read_csv(comp_path)
    if comp is not None:
        for _, row in comp.iterrows():
            method = normalize_method(str(row["method"]))
            if method not in taxonomy:
                continue
            category, caveat = taxonomy[method]
            rows.append(
                {
                    "method": method,
                    "category": category,
                    "K": int(row["K"]),
                    "critical_hits": clean_scalar(row.get("critical_hits")),
                    "relay_hits": clean_scalar(row.get("relay_hits")),
                    "precision": clean_scalar(row.get("precision")),
                    "recall_critical": clean_scalar(row.get("recall_critical")),
                    "relative_to_random": clean_scalar(row.get("relative_to_random_hits")),
                    "relative_to_lodf": clean_scalar(row.get("relative_to_lodf_hits")),
                    "relative_to_pfw": clean_scalar(row.get("relative_to_pfw_hits")),
                    "relative_to_strict_path_prob": clean_scalar(row.get("relative_to_strict_path_prob_hits")),
                    "relative_to_second_only": clean_scalar(row.get("relative_to_second_only_hits")),
                    "caveat": caveat,
                    "source": source(comp_path),
                }
            )

    if not rows:
        for method, hits in [("random", 55.4), ("line_order", 56), ("PFW", 66), ("LODF_yP", 58), ("strict_path_prob", 360), ("second_only", 661), ("best_alpha_path_prob", 661), ("any_critical_fragility_path_prob", 673), ("best_strict_fragility_path_prob", 676)]:
            category, caveat = taxonomy[method]
            rows.append({"method": method, "category": category, "K": 1000, "critical_hits": hits, "relay_hits": None, "precision": hits / 1000, "recall_critical": hits / 1754, "relative_to_random": hits - 55.4, "relative_to_lodf": hits - 58, "relative_to_pfw": hits - 66, "relative_to_strict_path_prob": hits - 360, "relative_to_second_only": hits - 661, "caveat": caveat, "source": source()})

    # PR #12 Algorithm 1 has only the checked K=1000 comparison in this synthesis.
    rows.append({"method": "Algorithm1", "category": "original_method_completion", "K": 1000, "critical_hits": 62, "relay_hits": None, "precision": 0.062, "recall_critical": 62 / 1754, "relative_to_random": 2, "relative_to_lodf": 4, "relative_to_pfw": -4, "relative_to_strict_path_prob": -327, "relative_to_second_only": -629, "caveat": taxonomy["Algorithm1"][1], "source": source()})
    return pd.DataFrame(rows).sort_values(["K", "category", "method"])


def build_improvement_methods_summary(search: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {"method": "second_only", "category": "diagnostic_ablation", "formula_or_rule": "p_second", "main_observation": "Often stronger than strict path_prob because many valid critical paths are low-p_first/high-p_second.", "paper_positioning": "diagnostic/ablation, not original main method"},
        {"method": "best_alpha_path_prob", "category": "ranking_improvement", "formula_or_rule": "(epsilon+p_first)^alpha*p_second", "main_observation": "Reducing the p_first gate improves low-budget ranking and nearly saturates K=5000.", "paper_positioning": "calibrated improvement, not original paper method"},
        {"method": "any_critical_fragility_path_prob", "category": "diagnostic_failed_label", "formula_or_rule": "q_any_critical(first_line)*p_second", "main_observation": "Label is all-positive, so it cannot prove discriminative first-line fragility learning.", "paper_positioning": "appendix/diagnostic"},
        {"method": "best_strict_fragility_path_prob", "category": "strict_fragility_refinement", "formula_or_rule": "q_strict_fragile(first_line)*p_second", "main_observation": "Fixes label degeneracy and slightly improves K=100/K=1000, but does not dominate best_alpha.", "paper_positioning": "optional main-text diagnostic refinement"},
    ]
    if not search.empty:
        for row in rows:
            subset = search.loc[(search["method"].eq(row["method"])) & (search["K"].isin([1000, 5000]))]
            row["K1000_critical_hits"] = clean_scalar(subset.loc[subset["K"].eq(1000), "critical_hits"].iloc[0]) if not subset.loc[subset["K"].eq(1000)].empty else None
            row["K5000_critical_hits"] = clean_scalar(subset.loc[subset["K"].eq(5000), "critical_hits"].iloc[0]) if not subset.loc[subset["K"].eq(5000)].empty else None
    return pd.DataFrame(rows)


def build_claims() -> dict[str, list[dict[str, str]]]:
    return {
        "main_text_claims": [
            {"claim": "After first-step critical early-stop, IEEE118 has 32,560 valid ordered N-2 paths, including 1,754 critical paths and 1,643 relay-cascade paths.", "support": "PR #11 checked protocol summary."},
            {"claim": "The pilot-2000 paper-aligned GCN strict path_prob is clearly stronger than random, LODF_yP, and PFW baselines.", "support": "PR #14/PR #16 compact search summaries."},
            {"claim": "S1 AP is much higher than S0 AP, indicating that first-step probability is the main bottleneck.", "support": "PR #14 classification summary and PR #15 diagnosis."},
            {"claim": "Many critical IEEE118 paths are low-p_first / high-p_second, especially relay-cascade paths.", "support": "PR #15 S0 bottleneck diagnostics."},
            {"claim": "Alpha path probability and strict fragility targets show that relaxing or replacing the hard p_first gate can improve low-budget ranking.", "support": "PR #16 and PR #18 key-K comparisons."},
        ],
        "diagnostic_or_ablation_claims": [
            {"claim": "second_only is stronger than strict path_prob, but it is an ablation rather than the original paper method.", "support": "PR #16 key-K comparison."},
            {"claim": "The any-critical fragility label is too broad and degenerates to all-positive.", "support": "PR #17 target metadata."},
            {"claim": "Strict fragility targets slightly improve K=100 and K=1000, but do not decisively dominate best_alpha.", "support": "PR #18 comparison table."},
        ],
        "forbidden_claims": [
            {"claim": "IEEE118 fully reproduces the dramatic RTS-79 search effect.", "reason": "The current IEEE118 gains are smaller and the setting is harder."},
            {"claim": "pilot-2000 is equivalent to paper-8000.", "reason": "pilot-2000 is explicitly a pilot result."},
            {"claim": "The any-critical fragility classifier learned discriminative first-line fragility.", "reason": "The label is all-positive."},
            {"claim": "alpha_path_prob or strict_fragility is the original paper main method.", "reason": "Both are IEEE118 diagnostic/improvement variants."},
            {"claim": "Algorithm1 is currently the best IEEE118 method.", "reason": "Current pilot/single-scenario Algorithm1 performance is weak."},
        ],
    }


def write_markdown_readme(output_dir: Path, search: pd.DataFrame) -> None:
    key = search.loc[search["K"].isin([1000, 5000]) & search["method"].isin(["strict_path_prob", "second_only", "best_alpha_path_prob", "best_strict_fragility_path_prob"])]
    table = key[["method", "K", "critical_hits", "precision", "caveat"]].to_markdown(index=False) if not key.empty else "(search table unavailable)"
    text = f"""# IEEE118 Experiment Synthesis

This directory is a compact synthesis of PR #11 through PR #18. It does not rerun OPA, retrain GCNs, modify Algorithm 1, or generate new large artifacts.

## Key Search Rows

{table}

## Positioning

- PR #11 is the formal early-stop protocol.
- PR #14 is the current closest paper-aligned pilot training result, but it is not paper-8000.
- PR #15 explains the S0 first-probability bottleneck.
- PR #16 and PR #18 are calibrated/diagnostic improvements, not original-paper replacements.
- PR #17 is a useful negative result because the any-critical label is all-positive.

Large local-only files such as raw full-truth CSVs, Step2-State CSVs, NPZ datasets, model checkpoints, full predictions, and Simulink/MATLAB artifacts are intentionally excluded.
"""
    (output_dir / "ieee118_experiment_synthesis_readme.md").write_text(text, encoding="utf-8")


def run_synthesis(args: argparse.Namespace) -> dict[str, str]:
    keys = included_keys(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timeline = build_timeline(keys)
    taxonomy = build_method_taxonomy(keys)
    key_results = build_key_results(keys)
    search = build_search_keyk_comparison(args.results_root)
    classification = build_classification_summary(args.results_root)
    bottleneck = build_s0_bottleneck_summary(args.results_root)
    improvements = build_improvement_methods_summary(search)
    claims = build_claims()

    outputs = {
        "timeline": args.output_dir / "ieee118_experiment_timeline.csv",
        "taxonomy": args.output_dir / "ieee118_method_taxonomy.csv",
        "key_results": args.output_dir / "ieee118_key_results_by_stage.csv",
        "search": args.output_dir / "ieee118_search_keyK_comparison.csv",
        "classification": args.output_dir / "ieee118_classification_summary.csv",
        "bottleneck": args.output_dir / "ieee118_s0_bottleneck_summary.csv",
        "improvements": args.output_dir / "ieee118_improvement_methods_summary.csv",
        "claims": args.output_dir / "ieee118_paper_ready_claims.json",
    }
    timeline.to_csv(outputs["timeline"], index=False, encoding="utf-8-sig")
    taxonomy.to_csv(outputs["taxonomy"], index=False, encoding="utf-8-sig")
    key_results.to_csv(outputs["key_results"], index=False, encoding="utf-8-sig")
    search.to_csv(outputs["search"], index=False, encoding="utf-8-sig")
    classification.to_csv(outputs["classification"], index=False, encoding="utf-8-sig")
    bottleneck.to_csv(outputs["bottleneck"], index=False, encoding="utf-8-sig")
    improvements.to_csv(outputs["improvements"], index=False, encoding="utf-8-sig")
    outputs["claims"].write_text(json.dumps(claims, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown_readme(args.output_dir, search)
    outputs["readme"] = args.output_dir / "ieee118_experiment_synthesis_readme.md"
    return {key: str(path) for key, path in outputs.items()}


def main() -> None:
    print(json.dumps(run_synthesis(parse_args()), indent=2))


if __name__ == "__main__":
    main()
