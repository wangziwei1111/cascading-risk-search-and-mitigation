from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def check_dynamic_interpretability_gate(
    post_fault_sanity_csv: str | Path,
    negative_control_v3_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_interpretability_gate",
    method_comparison_summary_csv: str | Path | None = None,
    non_smoke_method_comparison_summary_csv: str | Path | None = None,
    non_smoke_label_dynamic_alignment_json: str | Path | None = None,
    topk_coverage_diagnostics_csv: str | Path | None = None,
    event_strength_method_comparison_summary_csv: str | Path | None = None,
    robustness_summary_json: str | Path | None = None,
    bootstrap_ci_json: str | Path | None = None,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ladder = pd.read_csv(post_fault_sanity_csv)
    v3 = pd.read_csv(negative_control_v3_csv)
    no_trip_passed = _group_passed(ladder, "no_trip")
    single_mild_passed = _group_passed(ladder, "single_mild_trip")
    low_risk_not_all = _group_unstable(ladder, "low_risk_ordered_n2") < 1.0
    random_not_all = _group_unstable(ladder, "random_ordered_n2") < 1.0
    controls = v3[v3["group"].astype(str) != "learned_top20"]
    controls_have_variation = bool(not controls.empty and controls["unstable_fraction_post_fault_calibrated"].astype(float).nunique() > 1)
    if not controls.empty:
        controls_have_variation = controls_have_variation or bool((controls["unstable_fraction_post_fault_calibrated"].astype(float) < 1.0).any())
    default_interpretable = bool(no_trip_passed and controls_have_variation and low_risk_not_all and random_not_all)
    method_has_variation = False
    learned_higher_stress = False
    learned_higher_precision = False
    if method_comparison_summary_csv and Path(method_comparison_summary_csv).exists():
        method_summary = pd.read_csv(method_comparison_summary_csv)
        top100 = method_summary[method_summary["top_k"].astype(int) == 100] if "top_k" in method_summary.columns else method_summary
        if not top100.empty:
            method_has_variation = bool(top100["dynamic_precision_at_k"].astype(float).nunique() > 1 or top100["mean_dynamic_stress_score"].astype(float).nunique() > 1)
            learned = top100[top100["method"].astype(str) == "learned_mlp"]
            controls2 = top100[top100["method"].astype(str) != "learned_mlp"]
            if not learned.empty and not controls2.empty:
                learned_higher_stress = bool(float(learned["mean_dynamic_stress_score"].iloc[0]) > float(controls2["mean_dynamic_stress_score"].max()) * 1.05)
                learned_higher_precision = bool(float(learned["dynamic_precision_at_k"].iloc[0]) > float(controls2["dynamic_precision_at_k"].max()))
    non_smoke_has_variation = False
    non_smoke_all_stable_or_unstable = False
    non_smoke_learned_signal = False
    if non_smoke_method_comparison_summary_csv and Path(non_smoke_method_comparison_summary_csv).exists():
        non_smoke_summary = pd.read_csv(non_smoke_method_comparison_summary_csv)
        top100 = non_smoke_summary[non_smoke_summary["top_k"].astype(int) == 100] if "top_k" in non_smoke_summary.columns else non_smoke_summary
        if not top100.empty:
            precision = top100["dynamic_precision_at_k"].astype(float)
            stress = top100["mean_dynamic_stress_score"].astype(float)
            non_smoke_has_variation = bool(precision.nunique() > 1 or stress.nunique() > 1)
            non_smoke_all_stable_or_unstable = bool((precision == 0.0).all() or (precision == 1.0).all())
            learned = top100[top100["method"].astype(str) == "learned_mlp"]
            controls2 = top100[top100["method"].astype(str) != "learned_mlp"]
            if not learned.empty and not controls2.empty:
                non_smoke_learned_signal = bool(
                    float(learned["mean_dynamic_stress_score"].iloc[0]) > float(controls2["mean_dynamic_stress_score"].max()) * 1.05
                    or float(learned["dynamic_precision_at_k"].iloc[0]) > float(controls2["dynamic_precision_at_k"].max())
                )
    alignment_available = bool(non_smoke_label_dynamic_alignment_json and Path(non_smoke_label_dynamic_alignment_json).exists())
    topk_coverage_passed = _coverage_passed(topk_coverage_diagnostics_csv)
    event_strength_calibrated = bool(event_strength_method_comparison_summary_csv and Path(event_strength_method_comparison_summary_csv).exists())
    event_nondegenerate = False
    event_learned_signal = False
    if event_strength_calibrated:
        event_summary = pd.read_csv(event_strength_method_comparison_summary_csv)
        top100 = event_summary[event_summary["top_k"].astype(int) == 100] if "top_k" in event_summary.columns else event_summary
        if not top100.empty:
            precision = top100["dynamic_precision_at_k"].astype(float)
            event_nondegenerate = bool(not ((precision == 0.0).all() or (precision == 1.0).all()))
            learned = top100[top100["method"].astype(str) == "learned_mlp"]
            controls2 = top100[top100["method"].astype(str) != "learned_mlp"]
            if not learned.empty and not controls2.empty:
                event_learned_signal = bool(
                    float(learned["mean_dynamic_stress_score"].iloc[0]) > float(controls2["mean_dynamic_stress_score"].max()) * 1.05
                    or float(learned["dynamic_precision_at_k"].iloc[0]) > float(controls2["dynamic_precision_at_k"].max())
                )
    if topk_coverage_diagnostics_csv and not topk_coverage_passed:
        allowed_next_step = "fix_topk_coverage"
    elif event_strength_calibrated:
        if not event_nondegenerate:
            allowed_next_step = "tune_post_fault_event_strength"
        elif event_learned_signal:
            allowed_next_step = "prepare_preliminary_figures"
        else:
            allowed_next_step = "report_no_dynamic_advantage_preliminary"
    elif non_smoke_method_comparison_summary_csv and Path(non_smoke_method_comparison_summary_csv).exists():
        if non_smoke_all_stable_or_unstable:
            allowed_next_step = "tune_post_fault_event_strength"
        elif non_smoke_learned_signal:
            allowed_next_step = "prepare_paper_figures_preliminary"
        elif non_smoke_has_variation:
            allowed_next_step = "expand_full_dataset"
        else:
            allowed_next_step = "continue_dynamic_calibration"
    elif method_comparison_summary_csv and Path(method_comparison_summary_csv).exists():
        allowed_next_step = "expand_non_smoke_dataset" if method_has_variation else "continue_dynamic_calibration"
    else:
        allowed_next_step = "expand_top50_top100" if default_interpretable else "continue_dynamic_calibration"
    robustness_checked = bool(robustness_summary_json and Path(robustness_summary_json).exists())
    bootstrap_ci_available = bool(bootstrap_ci_json and Path(bootstrap_ci_json).exists())
    learned_dynamic_advantage_robust = False
    if robustness_checked:
        payload = json.loads(Path(robustness_summary_json).read_text(encoding="utf-8"))
        learned_dynamic_advantage_robust = bool(payload.get("learned_advantage_robust", False))
    if not event_strength_calibrated or not event_nondegenerate:
        report_conclusion = "inconclusive_due_to_calibration_warning"
    elif learned_dynamic_advantage_robust or event_learned_signal:
        report_conclusion = "learned_advantage_observed_preliminary"
    else:
        report_conclusion = "no_dynamic_advantage_observed_preliminary"
    summary = {
        "no_trip_passed": no_trip_passed,
        "single_mild_trip_passed": single_mild_passed,
        "low_risk_not_all_unstable": low_risk_not_all,
        "random_not_all_unstable": random_not_all,
        "controls_have_variation": controls_have_variation,
        "default_dynamic_precision_interpretable": default_interpretable,
        "method_comparison_has_variation": method_has_variation,
        "learned_has_higher_stress_than_controls": learned_higher_stress,
        "learned_has_higher_dynamic_precision_than_controls": learned_higher_precision,
        "non_smoke_method_comparison_has_variation": non_smoke_has_variation,
        "non_smoke_all_stable_or_unstable": non_smoke_all_stable_or_unstable,
        "non_smoke_label_dynamic_alignment_available": alignment_available,
        "topk_coverage_passed": topk_coverage_passed,
        "nondegenerate_dynamic_layer": event_nondegenerate,
        "event_strength_calibrated": event_strength_calibrated,
        "preliminary_dynamic_discrimination_signal": event_learned_signal,
        "robustness_checked": robustness_checked,
        "bootstrap_ci_available": bootstrap_ci_available,
        "learned_dynamic_advantage_robust": learned_dynamic_advantage_robust,
        "report_conclusion": report_conclusion,
        "dynamic_discrimination_signal": "preliminary_diagnostic_only" if learned_higher_stress or learned_higher_precision or non_smoke_learned_signal or event_learned_signal else "false",
        "allowed_next_step": allowed_next_step,
    }
    csv_path = out / "dynamic_interpretability_gate_summary.csv"
    json_path = out / "dynamic_interpretability_gate_summary.json"
    pd.DataFrame([summary]).to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _group_passed(table: pd.DataFrame, group: str) -> bool:
    sub = table.loc[table["case_group"].astype(str) == group]
    if sub.empty:
        return False
    return str(sub["sanity_level_passed"].iloc[0]).lower() in {"true", "1", "yes"}


def _group_unstable(table: pd.DataFrame, group: str) -> float:
    sub = table.loc[table["case_group"].astype(str) == group]
    if sub.empty:
        return 1.0
    return float(sub["unstable_fraction"].iloc[0])


def _coverage_passed(path: str | Path | None) -> bool:
    if path is None or not Path(path).exists():
        return True
    table = pd.read_csv(path)
    if table.empty or "coverage_ratio" not in table.columns:
        return False
    return bool((table["coverage_ratio"].astype(float) >= 0.95).all())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether dynamic Top-K precision is interpretable.")
    parser.add_argument("--post-fault-sanity-csv", required=True)
    parser.add_argument("--negative-control-v3-csv", required=True)
    parser.add_argument("--method-comparison-summary-csv")
    parser.add_argument("--non-smoke-method-comparison-summary-csv")
    parser.add_argument("--non-smoke-label-dynamic-alignment-json")
    parser.add_argument("--topk-coverage-diagnostics-csv")
    parser.add_argument("--event-strength-method-comparison-summary-csv")
    parser.add_argument("--robustness-summary-json")
    parser.add_argument("--bootstrap-ci-json")
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_interpretability_gate")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_dynamic_interpretability_gate(
        args.post_fault_sanity_csv,
        args.negative_control_v3_csv,
        args.output_dir,
        args.method_comparison_summary_csv,
        args.non_smoke_method_comparison_summary_csv,
        args.non_smoke_label_dynamic_alignment_json,
        args.topk_coverage_diagnostics_csv,
        args.event_strength_method_comparison_summary_csv,
        args.robustness_summary_json,
        args.bootstrap_ci_json,
    )


if __name__ == "__main__":
    main()
