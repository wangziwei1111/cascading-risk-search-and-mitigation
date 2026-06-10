"""Check review-ready GCN Simulink dynamic validation artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


REQUIRED_FILES = [
    "src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py",
    "src/gcn_search/legacy_rts79/export_rts79_simulink_basecase.py",
    "src/gcn_search/legacy_rts79/make_mock_simulink_dynamic_results.py",
    "src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py",
    "src/gcn_search/legacy_rts79/analyze_dynamic_smoke_degeneracy.py",
    "src/gcn_search/legacy_rts79/compare_default_vs_calibrated_dynamic_smoke.py",
    "src/gcn_search/legacy_rts79/analyze_dynamic_instability_reasons.py",
    "src/gcn_search/legacy_rts79/compute_dynamic_stress_score.py",
    "src/gcn_search/legacy_rts79/prepare_dynamic_negative_control_inputs.py",
    "src/gcn_search/legacy_rts79/run_dynamic_negative_control_pipeline.py",
    "src/gcn_search/legacy_rts79/analyze_swing_equilibrium_diagnostics.py",
    "src/gcn_search/legacy_rts79/analyze_dynamic_threshold_sensitivity.py",
    "src/gcn_search/legacy_rts79/summarize_dynamic_negative_controls_v2.py",
    "src/gcn_search/legacy_rts79/check_dynamic_interpretability_gate.py",
    "src/gcn_search/legacy_rts79/export_dynamic_method_comparison_cases.py",
    "src/gcn_search/legacy_rts79/analyze_dynamic_method_comparison.py",
    "src/gcn_search/legacy_rts79/analyze_dynamic_rank_depth_curve.py",
    "src/gcn_search/legacy_rts79/analyze_non_smoke_label_dynamic_alignment.py",
    "src/gcn_search/legacy_rts79/diagnose_dynamic_topk_case_coverage.py",
    "src/gcn_search/legacy_rts79/calibrate_post_fault_event_strength.py",
    "src/gcn_search/legacy_rts79/analyze_event_strength_robustness.py",
    "src/gcn_search/legacy_rts79/bootstrap_dynamic_method_comparison.py",
    "src/gcn_search/legacy_rts79/make_dynamic_method_comparison_figures.py",
    "matlab/simulink_rts79/build_rts79_swing_simulink_model.m",
    "matlab/simulink_rts79/simulate_rts79_swing_case.m",
    "matlab/simulink_rts79/run_rts79_dynamic_path_case.m",
    "matlab/simulink_rts79/run_rts79_dynamic_batch.m",
    "matlab/simulink_rts79/check_rts79_swing_model_sanity.m",
    "matlab/simulink_rts79/calibrate_rts79_swing_scales.m",
    "matlab/simulink_rts79/calibrate_event_driven_dynamic_scales.m",
    "matlab/simulink_rts79/run_dynamic_negative_control_batch.m",
    "matlab/simulink_rts79/run_real_topk_dynamic_validation.m",
    "matlab/simulink_rts79/run_real_topk_event_driven_dynamic_validation.m",
    "matlab/simulink_rts79/update_swing_power_after_load_shed.m",
    "matlab/simulink_rts79/initialize_swing_equilibrium.m",
    "matlab/simulink_rts79/run_swing_equilibrium_sanity_demo.m",
    "matlab/simulink_rts79/run_post_fault_sanity_ladder.m",
    "matlab/simulink_rts79/calibrate_post_fault_dynamic_response.m",
    "matlab/simulink_rts79/run_dynamic_method_comparison_batch.m",
    "matlab/simulink_rts79/run_mild_overload_security_demo.m",
    "matlab/simulink_rts79/run_severe_overload_relay_demo.m",
    "matlab/simulink_rts79/README.md",
    "src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py",
    "src/gcn_search/legacy_rts79/prepare_dynamic_method_comparison_topk.py",
    "src/gcn_search/legacy_rts79/export_path_reranker_per_path_ranking.py",
    "src/gcn_search/legacy_rts79/build_path_reranker_dataset.py",
    "src/gcn_search/legacy_rts79/train_path_reranker.py",
    "src/gcn_search/legacy_rts79/evaluate_path_reranker_strict_heldout.py",
    "src/gcn_search/legacy_rts79/run_real_topk_dynamic_validation_pipeline.py",
    "src/gcn_search/legacy_rts79/summarize_real_topk_dynamic_validation.py",
    "src/gcn_search/legacy_rts79/check_simulink_dynamic_sanity_artifacts.py",
    "src/gcn_search/legacy_rts79/analyze_opa_dynamic_disagreement.py",
    "src/gcn_search/legacy_rts79/analyze_relay_vs_security_events.py",
    "src/gcn_search/legacy_rts79/check_relay_security_demo_artifacts.py",
    "tests/test_simulink_dynamic_case_export.py",
    "tests/test_simulink_dynamic_result_analysis.py",
    "tests/test_simulink_dynamic_disagreement.py",
    "tests/test_simulink_real_topk_preparation.py",
    "tests/test_relay_vs_security_logic.py",
    "tests/test_event_driven_dynamic_loop.py",
    "tests/test_real_topk_dynamic_pipeline.py",
    "tests/test_dynamic_method_comparison_inputs.py",
    "tests/test_export_path_reranker_per_path_ranking.py",
    "tests/test_real_topk_dynamic_validation_pipeline.py",
    "tests/test_real_topk_dynamic_summary.py",
    "tests/test_path_reranker_minimal_pipeline.py",
    "tests/test_real_topk_dynamic_smoke_summary.py",
    "tests/test_dynamic_smoke_degeneracy.py",
    "tests/test_default_vs_calibrated_dynamic_smoke.py",
    "tests/test_dynamic_instability_reasons.py",
    "tests/test_dynamic_stress_score.py",
    "tests/test_dynamic_negative_controls.py",
    "tests/test_swing_equilibrium_diagnostics.py",
    "tests/test_dynamic_threshold_sensitivity.py",
    "tests/test_negative_controls_v2_summary.py",
    "tests/test_post_fault_sanity_ladder.py",
    "tests/test_dynamic_interpretability_gate.py",
    "tests/test_negative_control_v3_summary.py",
    "tests/test_dynamic_method_comparison_cases.py",
    "tests/test_dynamic_method_comparison_analysis.py",
    "tests/test_dynamic_rank_depth_curve.py",
    "tests/test_non_smoke_path_reranker_dataset.py",
    "tests/test_non_smoke_dynamic_method_comparison.py",
    "tests/test_non_smoke_label_dynamic_alignment.py",
    "tests/test_dynamic_topk_case_coverage.py",
    "tests/test_post_fault_event_strength_calibration.py",
    "tests/test_event_strength_dynamic_summary.py",
    "tests/test_event_strength_robustness.py",
    "tests/test_dynamic_method_bootstrap_ci.py",
    "tests/test_dynamic_method_figures.py",
    "tests/test_preliminary_diagnostic_report.py",
    "docs/pio_gcn_simulink_dynamic_validation_plan.md",
    "docs/pio_gcn_simulink_real_topk_validation.md",
    "docs/pio_gcn_simulink_real_topk_event_driven_validation.md",
    "docs/pio_gcn_simulink_real_topk_dynamic_smoke.md",
    "docs/pio_gcn_simulink_dynamic_negative_controls.md",
    "docs/pio_gcn_swing_equilibrium_and_threshold_calibration.md",
    "docs/pio_gcn_post_fault_sanity_ladder.md",
    "docs/pio_gcn_dynamic_method_comparison_top100.md",
    "docs/pio_gcn_dynamic_method_comparison_non_smoke.md",
    "docs/pio_gcn_dynamic_event_strength_calibration.md",
    "docs/pio_gcn_dynamic_preliminary_diagnostic_report.md",
    "docs/pio_gcn_relay_vs_security_constraint.md",
    "docs/gcn_pio_validation_log.md",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/real_topk_dynamic_smoke_summary.csv",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/real_topk_dynamic_smoke_summary.json",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/default_top20_dynamic_smoke_summary.csv",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/calibrated_top20_dynamic_smoke_summary.csv",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/default_vs_calibrated_dynamic_smoke_comparison.csv",
]


DISALLOWED_TRACKED_SUBSTRINGS = [
    ".pt",
    ".npz",
    ".pkl",
    ".slx",
    ".mat",
    ".mdl",
    "full_truth",
    "smoke_truth",
    "simulation_results",
    "scenario_checkpoints",
    "raw_trajectories",
    "dynamic_trajectories",
    "simulink_dynamic_results",
    "learned_mlp_per_path_ranking.csv",
    "per_path_ranking.csv",
    "path_reranker_dataset.csv",
    "path_reranker_train.csv",
    "path_reranker_val.csv",
    "path_reranker_test.csv",
    "large_simulink_log",
    "event_grid_",
]


def _git_ls_files(path: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", path],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _git_changed_files_against_main() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    failures: list[str] = []

    for rel_path in REQUIRED_FILES:
        path = ROOT / rel_path
        if not path.exists():
            failures.append(f"Missing required artifact: {rel_path}")
        elif path.is_file() and path.stat().st_size == 0:
            failures.append(f"Required artifact is empty: {rel_path}")

    log_path = ROOT / "docs/gcn_pio_validation_log.md"
    if log_path.exists():
        log_text = _read_text("docs/gcn_pio_validation_log.md")
        if "Round 10" not in log_text:
            failures.append("Validation log does not contain the Round 10 record.")
        if "Round 11" not in log_text:
            failures.append("Validation log does not contain the Round 11 record.")
        if "Round 12" not in log_text:
            failures.append("Validation log does not contain the Round 12 record.")
        if "Round 13" not in log_text:
            failures.append("Validation log does not contain the Round 13 record.")
        if "Round 14" not in log_text:
            failures.append("Validation log does not contain the Round 14 record.")
        if "Round 15" not in log_text:
            failures.append("Validation log does not contain the Round 15 record.")
        if "Round 16" not in log_text:
            failures.append("Validation log does not contain the Round 16 record.")
        if "Round 17" not in log_text:
            failures.append("Validation log does not contain the Round 17 record.")
        if "Round 18" not in log_text:
            failures.append("Validation log does not contain the Round 18 record.")
        if "Round 19" not in log_text:
            failures.append("Validation log does not contain the Round 19 record.")
        if "Round 20" not in log_text:
            failures.append("Validation log does not contain the Round 20 record.")
        if "Round 21" not in log_text:
            failures.append("Validation log does not contain the Round 21 record.")
        if "Round 22" not in log_text:
            failures.append("Validation log does not contain the Round 22 record.")
        if "Round 23" not in log_text:
            failures.append("Validation log does not contain the Round 23 record.")
        if "Round 24" not in log_text:
            failures.append("Validation log does not contain the Round 24 record.")
        if "Round 25" not in log_text:
            failures.append("Validation log does not contain the Round 25 record.")

    plan_path = ROOT / "docs/pio_gcn_simulink_dynamic_validation_plan.md"
    if plan_path.exists():
        plan_text = _read_text("docs/pio_gcn_simulink_dynamic_validation_plan.md").lower()
        overstated_phrases = [
            "final dynamic proof",
            "emt validation completed",
            "production ready",
            "real scada/pmu integration completed",
            "renewable dynamic validation completed",
            "real-time deployment completed",
            "engineering-grade dynamic model completed",
            "loading_ratio > 1.0 triggers relay trip",
            "full OPF redispatch completed",
            "工程级动态模型已完成",
            "真实动态稳定结论已完成",
            "新能源动态验证已完成",
        ]
        for phrase in overstated_phrases:
            if phrase in plan_text:
                failures.append(f"Overstated phrase in Simulink validation plan: {phrase}")

    for rel_matlab in [
        "matlab/simulink_rts79/run_rts79_dynamic_path_case.m",
        "matlab/simulink_rts79/run_rts79_dynamic_batch.m",
        "matlab/simulink_rts79/simulate_rts79_swing_case.m",
    ]:
        matlab_text = _read_text(rel_matlab).lower() if (ROOT / rel_matlab).exists() else ""
        if "placeholder metrics" in matlab_text:
            failures.append(f"MATLAB file still refers to placeholder metrics: {rel_matlab}")

    mock_script = ROOT / "src/gcn_search/legacy_rts79/make_mock_simulink_dynamic_results.py"
    if mock_script.exists() and '"result_source": "mock"' not in _read_text(str(mock_script.relative_to(ROOT)).replace("\\", "/")):
        failures.append("Mock dynamic result script does not mark result_source as mock.")

    real_topk_doc = ROOT / "docs/pio_gcn_simulink_real_topk_validation.md"
    if real_topk_doc.exists():
        real_topk_text = _read_text("docs/pio_gcn_simulink_real_topk_validation.md").lower()
        if "demo precision is not a formal dynamic conclusion" not in real_topk_text:
            failures.append("Real Top-K validation doc does not warn against treating demo precision as a formal conclusion.")

    event_real_topk_doc = ROOT / "docs/pio_gcn_simulink_real_topk_event_driven_validation.md"
    if event_real_topk_doc.exists():
        event_doc_text = _read_text("docs/pio_gcn_simulink_real_topk_event_driven_validation.md").lower()
        required_terms = [
            "real per-path ranking csv",
            "real_topk_input_paths.csv",
            "run_real_topk_event_driven_dynamic_validation",
            "prepare_dynamic_method_comparison_topk.py",
            "dynamic_precision_at_k",
        ]
        for required in required_terms:
            if required not in event_doc_text:
                failures.append(f"Round 15 real Top-K event-driven doc is missing required term: {required}")
        forbidden_terms = [
            "final dynamic proof",
            "emt validation completed",
            "renewable dynamic validation completed",
            "engineering-grade dynamic model completed",
            "full opf redispatch completed",
            "dynamic recall@k",
            "dynamic recall@20",
            "dynamic recall@50",
            "dynamic recall@100",
        ]
        for term in forbidden_terms:
            if term in event_doc_text:
                failures.append(f"Round 15 real Top-K event-driven doc contains an overstatement: {term}")

    smoke_doc = ROOT / "docs/pio_gcn_simulink_real_topk_dynamic_smoke.md"
    if smoke_doc.exists():
        smoke_text = _read_text("docs/pio_gcn_simulink_real_topk_dynamic_smoke.md").lower()
        for required in [
            "per-path ranking csv",
            "preliminary dynamic smoke",
            "dynamic_precision@k",
            "opa/dynamic overlap",
            "relay/security",
            "no dynamic recall",
            "not emt",
            "not full opf",
        ]:
            if required not in smoke_text:
                failures.append(f"Round 16 smoke doc is missing required term: {required}")
        for forbidden in [
            "final dynamic proof",
            "emt validation completed",
            "renewable dynamic validation completed",
            "engineering-grade dynamic model completed",
            "full opf redispatch completed",
            "dynamic recall@k",
        ]:
            if forbidden in smoke_text:
                failures.append(f"Round 16 smoke doc contains an overstatement: {forbidden}")

    smoke_summary = ROOT / "results/gcn_search/simulink_dynamic_real_pipeline_summary/real_topk_dynamic_smoke_summary.csv"
    if smoke_summary.exists():
        try:
            import pandas as pd

            table = pd.read_csv(smoke_summary)
            if "result_scope" not in table.columns:
                failures.append("Real Top-K dynamic smoke summary is missing result_scope.")
            elif not table["result_scope"].astype(str).isin(
                [
                    "top20_preliminary_dynamic_smoke",
                    "default_top20_preliminary_dynamic_smoke",
                    "calibrated_top20_preliminary_dynamic_smoke",
                ]
            ).all():
                failures.append("Real Top-K dynamic smoke summary result_scope must be a Top20 preliminary dynamic smoke scope.")
            if any("dynamic_recall" in col.lower() for col in table.columns):
                failures.append("Real Top-K dynamic smoke summary must not contain dynamic recall columns.")
        except Exception as exc:
            failures.append(f"Failed to read real Top-K dynamic smoke summary: {exc}")

    calibrated_summary = ROOT / "results/gcn_search/simulink_dynamic_real_pipeline_summary/calibrated_top20_dynamic_smoke_summary.csv"
    if calibrated_summary.exists():
        try:
            import pandas as pd

            table = pd.read_csv(calibrated_summary)
            if "result_scope" not in table.columns or not (table["result_scope"].astype(str) == "calibrated_top20_preliminary_dynamic_smoke").all():
                failures.append("Calibrated Top20 smoke summary result_scope must be calibrated_top20_preliminary_dynamic_smoke.")
            if "degeneracy_warning" not in table.columns:
                failures.append("Calibrated Top20 smoke summary must contain degeneracy_warning.")
            if any("dynamic_recall" in col.lower() for col in table.columns):
                failures.append("Calibrated Top20 smoke summary must not contain dynamic recall columns.")
        except Exception as exc:
            failures.append(f"Failed to read calibrated Top20 smoke summary: {exc}")

    comparison_path = ROOT / "results/gcn_search/simulink_dynamic_real_pipeline_summary/default_vs_calibrated_dynamic_smoke_comparison.csv"
    if comparison_path.exists():
        try:
            import pandas as pd

            comparison = pd.read_csv(comparison_path)
            if "variant" not in comparison.columns or set(comparison["variant"].astype(str)) != {"default", "calibrated"}:
                failures.append("Default-vs-calibrated comparison must contain default and calibrated variants.")
        except Exception as exc:
            failures.append(f"Failed to read default-vs-calibrated comparison: {exc}")

    relay_doc = ROOT / "docs/pio_gcn_relay_vs_security_constraint.md"
    if relay_doc.exists():
        relay_text = _read_text("docs/pio_gcn_relay_vs_security_constraint.md").lower()
        for required in ["1.0 < loading_ratio <= beta", "security redispatch/load shedding", "loading_ratio > beta", "passive relay trip"]:
            if required not in relay_text:
                failures.append(f"Relay/security doc is missing required term: {required}")

    negative_doc = ROOT / "docs/pio_gcn_simulink_dynamic_negative_controls.md"
    if negative_doc.exists():
        negative_text = _read_text("docs/pio_gcn_simulink_dynamic_negative_controls.md").lower()
        for required in [
            "negative controls",
            "learned_top20",
            "low_score_top20",
            "random_top20",
            "line_order_top20",
            "no dynamic recall",
            "not emt",
            "not full opf",
        ]:
            if required not in negative_text:
                failures.append(f"Negative-control doc is missing required term: {required}")

    calibration_doc = ROOT / "docs/pio_gcn_swing_equilibrium_and_threshold_calibration.md"
    if calibration_doc.exists():
        calibration_text = _read_text("docs/pio_gcn_swing_equilibrium_and_threshold_calibration.md").lower()
        for required in ["no-trip sanity", "coi reference", "threshold sensitivity", "no dynamic recall", "not emt", "not full opf"]:
            if required not in calibration_text:
                failures.append(f"Round 20 calibration doc is missing required term: {required}")
        for forbidden in [
            "final dynamic proof",
            "emt validation completed",
            "renewable dynamic validation completed",
            "engineering-grade dynamic model completed",
            "full opf redispatch completed",
            "dynamic recall@k",
        ]:
            if forbidden in calibration_text:
                failures.append(f"Round 20 calibration doc contains an overstatement: {forbidden}")

    post_fault_doc = ROOT / "docs/pio_gcn_post_fault_sanity_ladder.md"
    if post_fault_doc.exists():
        text = _read_text("docs/pio_gcn_post_fault_sanity_ladder.md").lower()
        for required in ["post-fault sanity ladder", "no dynamic recall", "not emt", "not full opf", "continue_dynamic_calibration"]:
            if required not in text:
                failures.append(f"Round 21 post-fault doc is missing required term: {required}")

    method_doc = ROOT / "docs/pio_gcn_dynamic_method_comparison_top100.md"
    if method_doc.exists():
        text = _read_text("docs/pio_gcn_dynamic_method_comparison_top100.md").lower()
        for required in ["preliminary diagnostic", "no dynamic recall", "calibration_warning", "not emt", "not full opf"]:
            if required not in text:
                failures.append(f"Round 22 method comparison doc is missing required term: {required}")

    non_smoke_doc = ROOT / "docs/pio_gcn_dynamic_method_comparison_non_smoke.md"
    if non_smoke_doc.exists():
        text = _read_text("docs/pio_gcn_dynamic_method_comparison_non_smoke.md").lower()
        for required in ["preliminary diagnostic", "non-smoke", "no dynamic recall", "calibration_warning", "not emt", "not full opf"]:
            if required not in text:
                failures.append(f"Round 23 non-smoke method comparison doc is missing required term: {required}")
        for forbidden in [
            "final dynamic proof",
            "emt validation completed",
            "renewable dynamic validation completed",
            "engineering-grade dynamic model completed",
            "full opf redispatch completed",
            "dynamic recall@k",
        ]:
            if forbidden in text:
                failures.append(f"Round 23 non-smoke doc contains an overstatement: {forbidden}")

    event_strength_doc = ROOT / "docs/pio_gcn_dynamic_event_strength_calibration.md"
    if event_strength_doc.exists():
        text = _read_text("docs/pio_gcn_dynamic_event_strength_calibration.md").lower()
        for required in ["all-stable", "all-unstable", "preliminary diagnostic", "no dynamic recall", "not emt", "not full opf"]:
            if required not in text:
                failures.append(f"Round 24 event-strength doc is missing required term: {required}")
        for forbidden in [
            "final dynamic proof",
            "emt validation completed",
            "renewable dynamic validation completed",
            "engineering-grade dynamic model completed",
            "full opf redispatch completed",
            "dynamic recall@k",
        ]:
            if forbidden in text:
                failures.append(f"Round 24 event-strength doc contains an overstatement: {forbidden}")

    preliminary_report = ROOT / "docs/pio_gcn_dynamic_preliminary_diagnostic_report.md"
    if preliminary_report.exists():
        text = _read_text("docs/pio_gcn_dynamic_preliminary_diagnostic_report.md").lower()
        for required in ["no dynamic recall", "not emt", "not full opf", "no observed learned dynamic advantage"]:
            if required not in text:
                failures.append(f"Preliminary diagnostic report is missing required term: {required}")
        for forbidden in [
            "final proof",
            "final dynamic proof",
            "engineering-grade conclusion",
            "learned superiority claim",
            "learned dynamic superiority",
        ]:
            if forbidden in text:
                failures.append(f"Preliminary diagnostic report contains an overstatement: {forbidden}")

    sanity_summary = ROOT / "results/gcn_search/simulink_dynamic_equilibrium_sanity/swing_equilibrium_sanity_summary.json"
    if sanity_summary.exists():
        try:
            payload = __import__("json").loads(sanity_summary.read_text(encoding="utf-8"))
            if "sanity_passed" not in payload:
                failures.append("No-trip sanity summary exists but does not contain sanity_passed.")
        except Exception as exc:
            failures.append(f"Failed to read no-trip sanity summary: {exc}")

    threshold_summary = ROOT / "results/gcn_search/simulink_dynamic_threshold_sensitivity/dynamic_threshold_sensitivity_summary.json"
    if threshold_summary.exists():
        text = threshold_summary.read_text(encoding="utf-8", errors="ignore").lower()
        if "formal dynamic conclusion" not in text:
            failures.append("Threshold sensitivity summary must state it is not a formal dynamic conclusion.")

    gate_summary = ROOT / "results/gcn_search/simulink_dynamic_interpretability_gate/dynamic_interpretability_gate_summary.json"
    if gate_summary.exists():
        try:
            payload = __import__("json").loads(gate_summary.read_text(encoding="utf-8"))
            allowed = payload.get("allowed_next_step")
            if allowed not in {
                "expand_top50_top100",
                "expand_non_smoke_dataset",
                "continue_dynamic_calibration",
                "tune_post_fault_event_strength",
                "expand_full_dataset",
                "prepare_paper_figures_preliminary",
                "fix_topk_coverage",
                "prepare_preliminary_figures",
                "report_no_dynamic_advantage_preliminary",
            }:
                failures.append("Interpretability gate allowed_next_step has an invalid value.")
        except Exception as exc:
            failures.append(f"Failed to read interpretability gate summary: {exc}")

    method_summary = ROOT / "results/gcn_search/simulink_dynamic_method_comparison_summary/dynamic_method_comparison_summary.csv"
    if method_summary.exists():
        try:
            import pandas as pd

            table = pd.read_csv(method_summary)
            if any("dynamic_recall" in col.lower() for col in table.columns):
                failures.append("Dynamic method comparison summary must not contain dynamic recall columns.")
            if not table.empty:
                top100 = table[table["top_k"].astype(int) == 100]
                if not top100.empty:
                    precision = top100["dynamic_precision_at_k"].astype(float)
                    all_zero_or_one = (precision == 0.0).all() or (precision == 1.0).all()
                    if all_zero_or_one and "calibration_warning" not in " ".join(_read_text("docs/pio_gcn_dynamic_method_comparison_top100.md").lower().split()):
                        failures.append("All-zero/all-one method comparison requires calibration_warning in the Round 22 doc.")
        except Exception as exc:
            failures.append(f"Failed to read dynamic method comparison summary: {exc}")

    non_smoke_summary = ROOT / "results/gcn_search/simulink_dynamic_method_comparison_non_smoke_summary/dynamic_method_comparison_non_smoke_summary.csv"
    if non_smoke_summary.exists():
        try:
            import pandas as pd

            table = pd.read_csv(non_smoke_summary)
            if any("dynamic_recall" in col.lower() for col in table.columns):
                failures.append("Non-smoke dynamic method comparison summary must not contain dynamic recall columns.")
            if not table.empty:
                top100 = table[table["top_k"].astype(int) == 100]
                if not top100.empty:
                    precision = top100["dynamic_precision_at_k"].astype(float)
                    all_zero_or_one = (precision == 0.0).all() or (precision == 1.0).all()
                    if all_zero_or_one and "calibration_warning" not in " ".join(_read_text("docs/pio_gcn_dynamic_method_comparison_non_smoke.md").lower().split()):
                        failures.append("All-zero/all-one non-smoke comparison requires calibration_warning in the Round 23 doc.")
        except Exception as exc:
            failures.append(f"Failed to read non-smoke dynamic method comparison summary: {exc}")

    coverage_diag = ROOT / "results/gcn_search/simulink_dynamic_method_comparison_non_smoke_summary/dynamic_topk_case_coverage_diagnostics.csv"
    if coverage_diag.exists():
        try:
            import pandas as pd

            table = pd.read_csv(coverage_diag)
            if not table.empty and (table["coverage_ratio"].astype(float) < 0.95).any():
                if "coverage warning" not in _read_text("docs/pio_gcn_dynamic_event_strength_calibration.md").lower():
                    failures.append("TopK coverage below 0.95 requires a coverage warning in the Round 24 doc.")
        except Exception as exc:
            failures.append(f"Failed to read TopK coverage diagnostics: {exc}")

    event_summary = ROOT / "results/gcn_search/simulink_dynamic_method_comparison_non_smoke_event_strength_summary/dynamic_method_comparison_event_strength_summary.csv"
    if event_summary.exists():
        try:
            import pandas as pd

            table = pd.read_csv(event_summary)
            if any("dynamic_recall" in col.lower() for col in table.columns):
                failures.append("Event-strength dynamic summary must not contain dynamic recall columns.")
            if not table.empty:
                top100 = table[table["top_k"].astype(int) == 100]
                if not top100.empty:
                    precision = top100["dynamic_precision_at_k"].astype(float)
                    all_zero_or_one = (precision == 0.0).all() or (precision == 1.0).all()
                    if all_zero_or_one and "calibration_warning" not in _read_text("docs/pio_gcn_dynamic_event_strength_calibration.md").lower():
                        failures.append("Degenerate event-strength summary requires calibration_warning in the Round 24 doc.")
        except Exception as exc:
            failures.append(f"Failed to read event-strength dynamic summary: {exc}")

    robustness_summary = ROOT / "results/gcn_search/simulink_dynamic_method_comparison_robustness/event_strength_robustness_summary.csv"
    if robustness_summary.exists():
        try:
            import pandas as pd

            table = pd.read_csv(robustness_summary)
            if "learned_advantage_robust" not in table.columns:
                failures.append("Robustness summary must contain learned_advantage_robust.")
        except Exception as exc:
            failures.append(f"Failed to read robustness summary: {exc}")

    bootstrap_ci = ROOT / "results/gcn_search/simulink_dynamic_method_comparison_robustness/dynamic_method_bootstrap_ci.csv"
    if bootstrap_ci.exists():
        try:
            import pandas as pd

            table = pd.read_csv(bootstrap_ci)
            if any("dynamic_recall" in col.lower() for col in table.columns):
                failures.append("Bootstrap CI summary must not contain dynamic recall columns.")
            required = {"method", "top_k", "metric", "estimate", "ci_low", "ci_high", "bootstrap_n", "random_seed"}
            if not required.issubset(table.columns):
                failures.append("Bootstrap CI summary is missing required columns.")
        except Exception as exc:
            failures.append(f"Failed to read bootstrap CI summary: {exc}")

    negative_summary = ROOT / "results/gcn_search/simulink_dynamic_negative_control_summary/dynamic_negative_control_comparison.csv"
    if negative_summary.exists():
        try:
            import pandas as pd

            table = pd.read_csv(negative_summary)
            if any("dynamic_recall" in col.lower() for col in table.columns):
                failures.append("Negative-control summary must not contain dynamic recall columns.")
            if not table.empty and (table["dynamic_precision_at_20"].astype(float) == 1.0).all():
                if "global_degeneracy_warning" not in table.columns or not table["global_degeneracy_warning"].astype(bool).all():
                    failures.append("Negative-control summary with all precision=1.0 must set global_degeneracy_warning=true.")
        except Exception as exc:
            failures.append(f"Failed to read negative-control summary: {exc}")

    tracked_results = set(_git_ls_files("results/gcn_search"))
    branch_changed = set(_git_changed_files_against_main())
    tracked = sorted(tracked_results & branch_changed)
    bad_files: list[str] = []
    for rel_path in tracked:
        lower = rel_path.lower()
        if any(token in lower for token in DISALLOWED_TRACKED_SUBSTRINGS):
            bad_files.append(rel_path)

    if bad_files:
        failures.append(
            "Disallowed tracked result artifacts:\n" + "\n".join(f"  - {path}" for path in bad_files)
        )

    if failures:
        print("FAIL: GCN Simulink dynamic validation artifact check failed.")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: GCN Simulink dynamic validation artifacts are review-ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
