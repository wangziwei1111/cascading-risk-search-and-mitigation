"""Check review-ready GCN Simulink dynamic validation artifacts."""

from __future__ import annotations

import json
import os
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
    "src/gcn_search/legacy_rts79/inventory_ieee39_simulink_models.py",
    "src/gcn_search/legacy_rts79/export_ieee39_dynamic_labels.py",
    "src/gcn_search/legacy_rts79/compare_ieee39_graphical_vs_simplified.py",
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
    "matlab/simulink_ieee39/check_ieee39_model_toolboxes.m",
    "matlab/simulink_ieee39/setup_ieee39_dynamic_experiment_wrapper.m",
    "matlab/simulink_ieee39/map_ieee39_lines_and_breakers.m",
    "matlab/simulink_ieee39/add_ieee39_basic_relay_proxy.m",
    "matlab/simulink_ieee39/configure_ieee39_three_phase_fault_case.m",
    "matlab/simulink_ieee39/configure_ieee39_pilot_line_trip_case.m",
    "matlab/simulink_ieee39/inspect_ieee39_line_ports.m",
    "matlab/simulink_ieee39/find_compatible_ieee39_breaker_blocks.m",
    "matlab/simulink_ieee39/probe_ieee39_breaker_insertion_standalone.m",
    "matlab/simulink_ieee39/insert_ieee39_timed_line_switch.m",
    "matlab/simulink_ieee39/configure_ieee39_short_filegen_paths.m",
    "matlab/simulink_ieee39/validate_ieee39_handwired_breaker_model.m",
    "matlab/simulink_ieee39/validate_ieee39_multi_handwired_breakers.m",
    "matlab/simulink_ieee39/run_ieee39_multi_handwired_line_trip_suite.m",
    "matlab/simulink_ieee39/prepare_ieee39_clean_handwired_breaker_lab.m",
    "matlab/simulink_ieee39/prepare_ieee39_clean_handwired_breaker_lab_for_line.m",
    "matlab/simulink_ieee39/prepare_ieee39_clean_handwired_breaker_labs_for_lines.m",
    "matlab/simulink_ieee39/inspect_ieee39_wrapper_grid_line_blocks.m",
    "matlab/simulink_ieee39/validate_ieee39_clean_breaker_lab_line.m",
    "matlab/simulink_ieee39/validate_ieee39_clean_breaker_lab_lines_batch.m",
    "matlab/simulink_ieee39/inventory_ieee39_simlog_tree.m",
    "matlab/simulink_ieee39/extract_ieee39_signal_summary.m",
    "matlab/simulink_ieee39/run_ieee39_fault_test_suite.m",
    "matlab/simulink_ieee39/prepare_ieee39_bus_fault_temp_lab_copy.m",
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
    "src/gcn_search/legacy_rts79/merge_ieee39_handwired_fault_summaries.py",
    "scripts/gcn_search/print_ieee39_handwired_breaker_checklist.py",
    "scripts/gcn_search/print_ieee39_multi_handwired_breaker_checklist.py",
    "scripts/gcn_search/print_ieee39_clean_breaker_lab_checklist.py",
    "scripts/gcn_search/print_ieee39_clean_breaker_lab_per_line_checklist.py",
    "scripts/gcn_search/print_ieee39_clean_breaker_lab_batch_checklist.py",
    "scripts/gcn_search/diagnose_ieee39_l12_islanding_case.py",
    "scripts/gcn_search/train_ieee39_dynamic_aware_reranker_preview.py",
    "scripts/gcn_search/compare_ieee39_dynamic_aware_preview_runs.py",
    "scripts/gcn_search/run_ieee39_dynamic_aware_stricter_comparison.py",
    "scripts/gcn_search/prepare_ieee39_non_line_trip_fault_expansion.py",
    "scripts/gcn_search/run_ieee39_non_line_trip_fault_smoke_tests.py",
    "scripts/gcn_search/export_ieee39_non_line_trip_dynamic_labels.py",
    "scripts/gcn_search/train_ieee39_dynamic_aware_reranker_v2_preview.py",
    "scripts/gcn_search/compare_ieee39_dynamic_aware_v2_preview_runs.py",
    "scripts/gcn_search/audit_ieee39_bus_fault_injection_points.py",
    "scripts/gcn_search/run_ieee39_bus_fault_smoke_tests.py",
    "scripts/gcn_search/prepare_ieee39_bus_fault_temp_lab.py",
    "scripts/gcn_search/run_ieee39_bus_fault_temp_lab_smoke.py",
    "scripts/gcn_search/collect_ieee39_bus_fault_manual_review.py",
    "scripts/gcn_search/prepare_ieee39_all_remaining_bus_fault_batch_readiness.py",
    "scripts/gcn_search/run_ieee39_all_remaining_bus_fault_batch_smoke.py",
    "scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trip_isolated.py",
    "scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py",
    "scripts/gcn_search/update_ieee39_line_breaker_map_from_inventory.py",
    "scripts/gcn_search/build_ieee39_full_line_map.py",
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
    "tests/test_ieee39_model_inventory.py",
    "tests/test_ieee39_dynamic_label_schema.py",
    "tests/test_ieee39_graphical_status_docs.py",
    "tests/test_ieee39_line_breaker_mapping.py",
    "tests/test_ieee39_fault_test_summary.py",
    "tests/test_ieee39_dynamic_label_quality_gate.py",
    "tests/test_ieee39_relay_proxy_docs.py",
    "tests/test_ieee39_real_fault_summary_schema.py",
    "tests/test_ieee39_signal_extraction_summary.py",
    "tests/test_ieee39_training_ready_label_gate.py",
    "tests/test_ieee39_real_fault_docs.py",
    "tests/test_ieee39_simlog_inventory.py",
    "tests/test_ieee39_measurement_quality_gate.py",
    "tests/test_ieee39_timed_trip_summary.py",
    "tests/test_ieee39_measurement_docs.py",
    "tests/test_ieee39_line_port_inventory.py",
    "tests/test_ieee39_breaker_candidate_inventory.py",
    "tests/test_ieee39_breaker_probe_summary.py",
    "tests/test_ieee39_timed_switch_insertion_summary.py",
    "tests/test_ieee39_timed_trip_docs.py",
    "tests/test_ieee39_handwired_breaker_validation_schema.py",
    "tests/test_ieee39_handwired_label_gate.py",
    "tests/test_ieee39_handwired_docs.py",
    "tests/test_ieee39_handwired_checklist.py",
    "tests/test_ieee39_multi_handwired_checklist.py",
    "tests/test_ieee39_multi_handwired_validation_schema.py",
    "tests/test_ieee39_multi_handwired_line_trip_summary.py",
    "tests/test_ieee39_handwired_fault_summary_merge.py",
    "tests/test_ieee39_multi_handwired_label_gate.py",
    "tests/test_ieee39_multi_handwired_docs.py",
    "tests/test_ieee39_clean_breaker_lab_prepare.py",
    "tests/test_ieee39_clean_breaker_lab_checklist.py",
    "tests/test_ieee39_clean_breaker_lab_validation_schema.py",
    "tests/test_ieee39_clean_breaker_lab_isolated_summary.py",
    "tests/test_ieee39_clean_breaker_lab_docs.py",
    "tests/test_ieee39_wrapper_grid_line_inventory.py",
    "tests/test_ieee39_line_breaker_map_extension.py",
    "tests/test_ieee39_line_map_extension_docs.py",
    "tests/test_ieee39_clean_breaker_lab_batch_prepare.py",
    "tests/test_ieee39_clean_breaker_lab_batch_checklist.py",
    "tests/test_ieee39_clean_breaker_lab_batch_validation_schema.py",
    "tests/test_ieee39_clean_breaker_lab_batch_isolated_summary.py",
    "tests/test_ieee39_batch_per_line_clean_breaker_lab_docs.py",
    "tests/test_ieee39_dynamic_aware_training_readiness.py",
    "tests/test_ieee39_dynamic_aware_reranker_preview_training.py",
    "tests/test_ieee39_dynamic_aware_reranker_preview_expanded.py",
    "tests/test_ieee39_dynamic_aware_preview_comparison.py",
    "tests/test_ieee39_dynamic_aware_stricter_comparison.py",
    "tests/test_ieee39_dynamic_aware_stricter_comparison_docs.py",
    "tests/test_ieee39_non_line_trip_fault_expansion_manifest.py",
    "tests/test_ieee39_non_line_trip_fault_expansion_docs.py",
    "tests/test_ieee39_non_line_trip_fault_expansion_dry_run.py",
    "tests/test_ieee39_non_line_trip_fault_smoke_tests.py",
    "tests/test_ieee39_non_line_trip_fault_smoke_docs.py",
    "tests/test_ieee39_non_line_trip_label_export.py",
    "tests/test_ieee39_dynamic_label_schema_v2_candidates.py",
    "tests/test_ieee39_non_line_trip_label_export_docs.py",
    "tests/test_ieee39_remaining_line_map_full.py",
    "tests/test_ieee39_remaining_clean_breaker_lab_prepare.py",
    "tests/test_ieee39_remaining_clean_breaker_lab_checklist.py",
    "tests/test_ieee39_all_remaining_clean_breaker_lab_validation.py",
    "tests/test_ieee39_all_remaining_clean_breaker_lab_merge.py",
    "tests/test_ieee39_all_remaining_label_gate.py",
    "tests/test_ieee39_all_remaining_docs.py",
    "tests/test_ieee39_l12_islanding_diagnosis.py",
    "tests/test_ieee39_l12_islanding_docs.py",
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
    "docs/ieee39_graphical_dynamic_model_selection.md",
    "docs/ieee39_graphical_dynamic_model_plan.md",
    "docs/ieee39_graphical_dynamic_model_status.md",
    "docs/ieee39_fault_breaker_relay_wrapper.md",
    "docs/ieee39_real_fault_execution_status.md",
    "docs/ieee39_measurement_extraction_and_timed_trip.md",
    "docs/ieee39_timed_line_trip_probe_status.md",
    "docs/ieee39_timed_breaker_manual_wiring_guide.md",
    "docs/ieee39_handwired_breaker_validation.md",
    "docs/ieee39_multi_handwired_breaker_expansion.md",
    "docs/ieee39_clean_breaker_lab_workflow.md",
    "docs/ieee39_per_line_clean_breaker_lab_workflow.md",
    "docs/ieee39_batch_per_line_clean_breaker_lab_workflow.md",
    "docs/ieee39_line_map_extension_workflow.md",
    "docs/ieee39_l12_islanding_timeout_case.md",
    "docs/ieee39_dynamic_aware_reranker_preview_training.md",
    "docs/ieee39_dynamic_aware_stricter_independent_test_comparison.md",
    "docs/ieee39_non_line_trip_fault_type_expansion.md",
    "docs/ieee39_non_line_trip_fault_smoke_tests.md",
    "docs/ieee39_non_line_trip_label_export.md",
    "docs/ieee39_dynamic_aware_reranker_v2_preview_training.md",
    "docs/ieee39_bus_fault_smoke_tests.md",
    "docs/ieee39_bus_fault_temp_lab_injection.md",
    "docs/ieee39_bus_fault_gui_manual_checklist.md",
    "docs/ieee39_bus_fault_b39_manual_review_result.md",
    "docs/ieee39_b39_temp_smoke_readiness.md",
    "docs/ieee39_b39_temporary_bus_fault_smoke.md",
    "docs/ieee39_b39_temp_smoke_quality_review.md",
    "docs/ieee39_b39_bus_fault_candidate_label_export.md",
    "docs/ieee39_v2_plus_b39_no_training_composition_review.md",
    "docs/ieee39_v2_plus_b39_preview_training.md",
    "docs/ieee39_v2_plus_b39_preview_interpretation.md",
    "docs/ieee39_b26_manual_bus_fault_verification_plan.md",
    "docs/ieee39_b26_temp_smoke_readiness.md",
    "docs/ieee39_b26_temporary_bus_fault_smoke.md",
    "docs/pio_gcn_relay_vs_security_constraint.md",
    "docs/gcn_pio_validation_log.md",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/real_topk_dynamic_smoke_summary.csv",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/real_topk_dynamic_smoke_summary.json",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/default_top20_dynamic_smoke_summary.csv",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/calibrated_top20_dynamic_smoke_summary.csv",
    "results/gcn_search/simulink_dynamic_real_pipeline_summary/default_vs_calibrated_dynamic_smoke_comparison.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/model_inventory.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/model_inventory.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/toolbox_check_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_event_log.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_signal_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_relay_trip_log.csv",
    "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_preview.csv",
    "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_schema.json",
    "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json",
    "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_fault_taxonomy.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_fault_taxonomy.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_scenario_manifest.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_scenario_manifest.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_feasibility_report.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_feasibility_report.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_dry_run_commands.txt",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_summary.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_report.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_report.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_non_line_trip_dynamic_label_candidates.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_non_line_trip_dynamic_label_candidates.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_label_schema_v2_combined_candidates.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_label_schema_v2_combined_candidates.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_label_quality_summary_v2_with_non_line_trip_candidates.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_aware_training_readiness_v2_with_non_line_trip_candidates.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_non_line_trip_duplicate_provenance_report.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_non_line_trip_duplicate_provenance_report.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/include_all_candidates/preview_training_dataset.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/include_all_candidates/preview_training_config.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/include_all_candidates/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/include_all_candidates/preview_training_predictions.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/include_all_candidates/preview_model_coefficients.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/include_all_candidates/preview_dynamic_aware_reranker_model.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/include_all_candidates/preview_training_readme.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/exclude_provenance_required/preview_training_dataset.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/exclude_provenance_required/preview_training_config.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/exclude_provenance_required/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/exclude_provenance_required/preview_training_predictions.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/exclude_provenance_required/preview_model_coefficients.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/exclude_provenance_required/preview_dynamic_aware_reranker_model.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/exclude_provenance_required/preview_training_readme.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/v2_preview_comparison.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/v2_preview_comparison.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_injection_feasibility.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_injection_feasibility.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_scenario_manifest.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_scenario_manifest.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_test_summary.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_test_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_test_report.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_test_report.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B39_plan.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B39_plan.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/matlab_bus_fault_injection_inventory_B39.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/matlab_bus_fault_injection_inventory_B39.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B26_plan.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B26_plan.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/matlab_bus_fault_injection_inventory_B26.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/matlab_bus_fault_injection_inventory_B26.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_feasibility_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_feasibility_summary.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_summary.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B39.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B39.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B26.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B26.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_quality_review.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_quality_review.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_b39_bus_fault_dynamic_label_candidate.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_b39_bus_fault_dynamic_label_candidate.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_dynamic_label_schema_v2_plus_b39_candidate.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_dynamic_label_quality_summary_v2_plus_b39_candidate.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_dynamic_aware_training_readiness_v2_plus_b39_candidate.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_b39_candidate_duplicate_provenance_report.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_composition_review.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_composition_review.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_label_family_counts.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_fault_type_counts.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_bus_fault_comparison.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/v2_plus_b39_preview_comparison.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/v2_plus_b39_preview_comparison.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/include_all_41_candidates/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/exclude_provenance_required/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/no_dynamic_measurement_features/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/label_family_holdout/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/bus_fault_holdout/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_gui_check_commands.md",
    "docs/ieee39_b26_manual_bus_fault_review_result.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_dry_run_readiness.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_dry_run_readiness.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_summary.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_report.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_report.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_quality_review.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_quality_review.md",
    "docs/ieee39_b26_temp_smoke_quality_review.md",
    "docs/ieee39_b26_bus_fault_candidate_label_export.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_dynamic_label_candidate.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_dynamic_label_candidate.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_dynamic_label_schema_v2_plus_b39_b26_candidate.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_candidate_export_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_candidate_export_summary.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_v2_plus_b39_b26_training_readiness.json",
    "docs/ieee39_v2_plus_b39_b26_no_training_composition_review.md",
    "docs/ieee39_v2_plus_b39_b26_preview_no_leakage_comparison.md",
    "docs/ieee39_all_remaining_bus_fault_manual_wiring_plan.md",
    "docs/ieee39_all_remaining_bus_fault_manual_connection_evidence.md",
    "scripts/gcn_search/train_ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview.py",
    "scripts/gcn_search/prepare_ieee39_all_remaining_bus_fault_manual_wiring_plan.py",
    "scripts/gcn_search/collect_ieee39_all_remaining_bus_fault_manual_evidence.py",
    "scripts/gcn_search/review_ieee39_all_remaining_bus_fault_batch_smoke_quality.py",
    "scripts/gcn_search/export_ieee39_all_remaining_bus_fault_candidate_labels.py",
    "scripts/gcn_search/review_ieee39_v2_plus_all_bus_fault_composition.py",
    "tests/test_ieee39_v2_plus_b39_b26_preview_no_leakage.py",
    "tests/test_ieee39_all_remaining_bus_fault_manual_wiring_plan.py",
    "tests/test_ieee39_all_remaining_bus_fault_manual_connection_evidence.py",
    "tests/test_ieee39_all_remaining_bus_fault_batch_readiness.py",
    "tests/test_ieee39_all_remaining_bus_fault_batch_actual_smoke.py",
    "tests/test_ieee39_all_remaining_bus_fault_batch_smoke_quality_review.py",
    "tests/test_ieee39_all_remaining_bus_fault_candidate_label_export.py",
    "tests/test_ieee39_v2_plus_all_bus_fault_composition_review.py",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_composition_review.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_composition_review.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_label_family_counts.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_fault_type_counts.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_bus_fault_comparison.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/v2_plus_b39_b26_preview_comparison.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/v2_plus_b39_b26_preview_comparison.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/include_all_42_candidates/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/exclude_provenance_required/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/no_dynamic_measurement_features/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/label_family_holdout/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/bus_fault_holdout/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/b39_holdout/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/b26_holdout/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/ieee39_bus_fault_all_remaining_targets.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/ieee39_bus_fault_all_remaining_targets.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/all_remaining_manual_gui_wiring_commands.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_manual_connection_evidence_schema.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_gate_sequence.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_connection_evidence/batch_manual_connection_evidence_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_connection_evidence/batch_manual_connection_evidence_summary.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_connection_evidence/batch_manual_connection_evidence_summary.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_connection_evidence/buses_ready_for_readiness_dry_run.json",
    "docs/ieee39_all_remaining_bus_fault_batch_readiness_dry_run.md",
    "docs/ieee39_all_remaining_bus_fault_batch_actual_smoke.md",
    "docs/ieee39_all_remaining_bus_fault_batch_smoke_quality_review.md",
    "docs/ieee39_all_remaining_bus_fault_candidate_label_export.md",
    "docs/ieee39_v2_plus_all_bus_fault_no_training_composition_review.md",
    "docs/ieee39_v2_plus_all_bus_fault_preview_no_leakage_comparison.md",
    "docs/ieee39_gcn_usefulness_audit_plan.md",
    "docs/ieee39_gcn_usefulness_audit_dry_run_validator.md",
    "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_readiness_dry_run_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_readiness_dry_run_summary.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_readiness_dry_run_summary.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_actual_smoke_plan_manifest.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_actual_smoke_plan_manifest.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/batch_actual_smoke_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/batch_actual_smoke_summary.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/batch_actual_smoke_summary.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/buses_ready_for_smoke_quality_review.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/batch_smoke_quality_review_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/batch_smoke_quality_review_summary.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/batch_smoke_quality_review_summary.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/buses_eligible_for_candidate_export.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/batch_candidate_label_export_summary.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/batch_candidate_label_export_summary.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/batch_candidate_label_export_summary.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/v2_plus_all_bus_fault_training_readiness.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/all_bus_fault_candidate_coverage_report.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/all_bus_fault_candidate_coverage_report.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/v2_plus_all_bus_fault_composition_review.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/v2_plus_all_bus_fault_composition_review.md",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/v2_plus_all_bus_fault_composition_review.csv",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/all_bus_fault_coverage_check.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/schema_and_duplicate_check.json",
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/leakage_risk_and_training_boundary_check.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/v2_plus_all_bus_fault_preview_comparison.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/v2_plus_all_bus_fault_preview_comparison.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/v2_plus_all_bus_fault_preview_comparison.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/include_all_79_candidates/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/no_dynamic_measurement_features/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/label_family_holdout/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/bus_fault_holdout/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/leave_one_bus_fault_out/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/no_dynamic_measurement_leave_one_bus_fault_out/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview/existing_vs_new_bus_fault_check/preview_training_metrics.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/gcn_usefulness_audit_plan.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/gcn_usefulness_audit_plan.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/no_leakage_feature_policy.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/no_leakage_feature_policy.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/strict_holdout_split_manifest.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/strict_holdout_split_manifest.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/baseline_comparison_plan.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/baseline_comparison_plan.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/gcn_audit_execution_checklist.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_plan/gcn_audit_execution_checklist.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/gcn_audit_dry_run_validator_summary.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/gcn_audit_dry_run_validator_summary.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/gcn_audit_dry_run_validator_summary.csv",
    "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/proposed_no_leakage_gcn_inputs_manifest.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/proposed_no_leakage_gcn_inputs_manifest.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/formal_gcn_audit_execution_draft.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/formal_gcn_audit_execution_draft.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/gcn_usefulness_audit_execution_summary.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/gcn_usefulness_audit_execution_summary.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/gcn_usefulness_audit_execution_summary.csv",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/forbidden_feature_audit_report.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/forbidden_feature_audit_report.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/baseline_vs_gcn_comparison.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/baseline_vs_gcn_comparison.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/b1_special_tracking_report.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/b1_special_tracking_report.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/nf06_sensitivity_report.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/nf06_sensitivity_report.md",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/l12_exclusion_confirmation.json",
    "results/gcn_search/ieee39_gcn_usefulness_audit_execution/l12_exclusion_confirmation.md",
    "docs/ieee39_gcn_audit_evidence_diagnosis.md",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/gcn_audit_evidence_diagnosis_summary.json",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/gcn_audit_evidence_diagnosis_summary.md",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/gcn_audit_evidence_diagnosis_summary.csv",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/gcn_vs_baseline_gap_analysis.json",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/gcn_vs_baseline_gap_analysis.md",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/b1_and_classification_diagnosis.json",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/b1_and_classification_diagnosis.md",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/nf06_sensitivity_diagnosis.json",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/nf06_sensitivity_diagnosis.md",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/graph_construction_diagnosis.json",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/graph_construction_diagnosis.md",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/next_gcn_improvement_plan.json",
    "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/next_gcn_improvement_plan.md",
    "docs/ieee39_paper_aligned_branch_gcn_redesign_dry_run.md",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_method_mapping_summary.json",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_method_mapping_summary.md",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/ieee39_branch_topology_source_inventory.json",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/ieee39_branch_topology_source_inventory.md",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/ieee39_branch_as_node_graph_manifest.json",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/ieee39_branch_as_node_graph_manifest.md",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_feature_manifest.json",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_feature_manifest.md",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_label_plan.json",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_label_plan.md",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/hybrid_search_policy_plan.json",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/hybrid_search_policy_plan.md",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_branch_gcn_dry_run_validator_summary.json",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_branch_gcn_dry_run_validator_summary.md",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_branch_gcn_dry_run_validator_summary.csv",
    "docs/ieee39_paper_aligned_branch_gcn_redesign_consistency_check.md",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_consistency_check/paper_aligned_redesign_consistency_check.json",
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_consistency_check/paper_aligned_redesign_consistency_check.md",
    "docs/ieee39_paper_aligned_feature_source_dry_run.md",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/feature_source_inventory.json",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/feature_source_inventory.md",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/l01_l34_feature_readiness_matrix.json",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/l01_l34_feature_readiness_matrix.md",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/l01_l34_feature_readiness_matrix.csv",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/paper_feature_mapping_plan.json",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/paper_feature_mapping_plan.md",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/no_leakage_feature_source_audit.json",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/no_leakage_feature_source_audit.md",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/feature_source_dry_run_validator_summary.json",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/feature_source_dry_run_validator_summary.md",
    "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/feature_source_dry_run_validator_summary.csv",
    "docs/ieee39_static_operating_point_feature_source_dry_run.md",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/static_case_source_inventory.json",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/static_case_source_inventory.md",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/dc_power_flow_generation_plan.json",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/dc_power_flow_generation_plan.md",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/l01_l34_static_feature_source_matrix.json",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/l01_l34_static_feature_source_matrix.md",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/l01_l34_static_feature_source_matrix.csv",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/relay_threshold_proxy_proposal.json",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/relay_threshold_proxy_proposal.md",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/no_leakage_static_feature_audit.json",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/no_leakage_static_feature_audit.md",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/static_feature_source_dry_run_validator_summary.json",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/static_feature_source_dry_run_validator_summary.md",
    "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/static_feature_source_dry_run_validator_summary.csv",
    "docs/ieee39_relay_threshold_proxy_approval.md",
    "results/gcn_search/ieee39_relay_threshold_proxy_approval/relay_threshold_proxy_approval_summary.json",
    "results/gcn_search/ieee39_relay_threshold_proxy_approval/relay_threshold_proxy_approval_summary.md",
    "results/gcn_search/ieee39_relay_threshold_proxy_approval/relay_threshold_proxy_approval_summary.csv",
    "results/gcn_search/ieee39_relay_threshold_proxy_approval/l01_l34_approved_paper_feature_source_matrix.json",
    "results/gcn_search/ieee39_relay_threshold_proxy_approval/l01_l34_approved_paper_feature_source_matrix.md",
    "results/gcn_search/ieee39_relay_threshold_proxy_approval/l01_l34_approved_paper_feature_source_matrix.csv",
    "results/gcn_search/ieee39_relay_threshold_proxy_approval/no_leakage_proxy_feature_audit.json",
    "results/gcn_search/ieee39_relay_threshold_proxy_approval/no_leakage_proxy_feature_audit.md",
    "results/gcn_search/ieee39_relay_threshold_proxy_approval/relay_threshold_proxy_limitations.md",
    "docs/ieee39_paper_style_branch_vulnerability_label_generator_dry_run.md",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/branch_vulnerability_label_semantics.json",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/branch_vulnerability_label_semantics.md",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/state_space_manifest.json",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/state_space_manifest.md",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/state_space_manifest.csv",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/state_branch_label_generation_plan.json",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/state_branch_label_generation_plan.md",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/state_branch_label_generation_plan.csv",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/existing_label_reuse_audit.json",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/existing_label_reuse_audit.md",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/no_leakage_label_generator_audit.json",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/no_leakage_label_generator_audit.md",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/label_generator_blocker_report.json",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/label_generator_blocker_report.md",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/branch_vulnerability_label_generator_dry_run_summary.json",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/branch_vulnerability_label_generator_dry_run_summary.md",
    "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/branch_vulnerability_label_generator_dry_run_summary.csv",
    "docs/ieee39_base_state_branch_vulnerability_label_pilot.md",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_pilot_summary.json",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_pilot_summary.md",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_pilot_summary.csv",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_matrix.json",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_matrix.md",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_matrix.csv",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/existing_line_trip_label_reuse_report.json",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/existing_line_trip_label_reuse_report.md",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/no_leakage_base_state_label_pilot_audit.json",
    "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/no_leakage_base_state_label_pilot_audit.md",
    "docs/ieee39_single_outage_label_loop_dry_run.md",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_state_manifest.json",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_state_manifest.md",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_state_manifest.csv",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_state_branch_label_loop_plan.json",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_state_branch_label_loop_plan.md",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_state_branch_label_loop_plan.csv",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/base_state_label_distribution_review.json",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/base_state_label_distribution_review.md",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/existing_artifact_reuse_for_single_outage_audit.json",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/existing_artifact_reuse_for_single_outage_audit.md",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/no_leakage_single_outage_label_loop_audit.json",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/no_leakage_single_outage_label_loop_audit.md",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_label_loop_dry_run_summary.json",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_label_loop_dry_run_summary.md",
    "results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_label_loop_dry_run_summary.csv",
    "docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/pilot_pair_selection_summary.json",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/pilot_pair_selection_summary.md",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/pilot_pair_selection_summary.csv",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/selected_single_outage_pilot_pairs.json",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/selected_single_outage_pilot_pairs.md",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/selected_single_outage_pilot_pairs.csv",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/future_controlled_generation_run_plan.json",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/future_controlled_generation_run_plan.md",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/no_leakage_pilot_pair_runner_audit.json",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/no_leakage_pilot_pair_runner_audit.md",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/single_outage_pilot_pair_runner_dry_run_summary.json",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/single_outage_pilot_pair_runner_dry_run_summary.md",
    "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/single_outage_pilot_pair_runner_dry_run_summary.csv",
    "docs/ieee39_selected_single_outage_pilot_pair_execution.md",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_approval.json",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_approval.md",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_summary.json",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_summary.md",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_summary.csv",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_results.json",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_results.md",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_results.csv",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_label_distribution.json",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_label_distribution.md",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/no_leakage_selected_pair_execution_audit.json",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/no_leakage_selected_pair_execution_audit.md",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/large_file_and_artifact_safety_check.json",
    "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/large_file_and_artifact_safety_check.md",
    "docs/ieee39_controlled_execution_backend_diagnosis.md",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/backend_readiness_summary.json",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/backend_readiness_summary.md",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/backend_readiness_summary.csv",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/backend_component_inventory.json",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/backend_component_inventory.md",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/selected_pair_execution_mapping_diagnosis.json",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/selected_pair_execution_mapping_diagnosis.md",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/selected_pair_execution_mapping_diagnosis.csv",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/safe_execution_repair_plan.json",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/safe_execution_repair_plan.md",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/no_leakage_backend_diagnosis_audit.json",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/no_leakage_backend_diagnosis_audit.md",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/large_file_safety_backend_diagnosis.json",
    "results/gcn_search/ieee39_controlled_execution_backend_diagnosis/large_file_safety_backend_diagnosis.md",
    "docs/ieee39_controlled_execution_backend_repair.md",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/backend_repair_summary.json",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/backend_repair_summary.md",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/backend_repair_summary.csv",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/backend_execution_contract.json",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/backend_execution_contract.md",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/manual_execution_instruction_pack.md",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/selected_pair_backend_readiness_matrix.json",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/selected_pair_backend_readiness_matrix.md",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/selected_pair_backend_readiness_matrix.csv",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/no_leakage_backend_repair_audit.json",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/no_leakage_backend_repair_audit.md",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/large_file_safety_backend_repair.json",
    "results/gcn_search/ieee39_controlled_execution_backend_repair/large_file_safety_backend_repair.md",
    "docs/ieee39_selected_32_pair_controlled_execution_evidence.md",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_approval.json",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_approval.md",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_summary.json",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_summary.md",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_summary.csv",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_results.json",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_results.md",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_results.csv",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_label_distribution.json",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_label_distribution.md",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/no_leakage_selected_32_execution_audit.json",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/no_leakage_selected_32_execution_audit.md",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/large_file_safety_selected_32_execution.json",
    "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/large_file_safety_selected_32_execution.md",
    "docs/ieee39_matlab_selected_pair_entrypoint_repair.md",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/matlab_entrypoint_repair_summary.json",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/matlab_entrypoint_repair_summary.md",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/matlab_entrypoint_repair_summary.csv",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/single_pair_smoke_execution_contract.json",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/single_pair_smoke_execution_contract.md",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/entrypoint_component_reuse_report.json",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/entrypoint_component_reuse_report.md",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/single_pair_smoke_candidate.json",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/single_pair_smoke_candidate.md",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/no_leakage_entrypoint_repair_audit.json",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/no_leakage_entrypoint_repair_audit.md",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/large_file_safety_entrypoint_repair.json",
    "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/large_file_safety_entrypoint_repair.md",
    "docs/ieee39_spp001_single_pair_smoke_execution.md",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_approval.json",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_approval.md",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_summary.json",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_summary.md",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_summary.csv",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_result.json",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_result.md",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_result.csv",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_no_leakage_smoke_audit.json",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_no_leakage_smoke_audit.md",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_large_file_safety_check.json",
    "results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_large_file_safety_check.md",
    "docs/ieee39_l15_handwired_validation_readiness_repair.md",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/l15_readiness_repair_summary.json",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/l15_readiness_repair_summary.md",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/l15_readiness_repair_summary.csv",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/l15_evidence_inventory.json",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/l15_evidence_inventory.md",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/repaired_combined_validation_preview.json",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/repaired_combined_validation_preview.md",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/repaired_combined_validation_preview.csv",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/spp001_rerun_readiness_gate.json",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/spp001_rerun_readiness_gate.md",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/no_leakage_l15_readiness_repair_audit.json",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/no_leakage_l15_readiness_repair_audit.md",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/large_file_safety_l15_readiness_repair.json",
    "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/large_file_safety_l15_readiness_repair.md",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_build_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_block_inventory.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_signal_map.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extended.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extension_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full_summary.json",
    "scripts/gcn_search/train_ieee39_v2_plus_all_bus_fault_preview.py",
    "scripts/gcn_search/prepare_ieee39_gcn_usefulness_audit_plan.py",
    "scripts/gcn_search/run_ieee39_gcn_usefulness_audit_dry_run_validator.py",
    "scripts/gcn_search/run_ieee39_strict_no_leakage_gcn_usefulness_audit.py",
    "scripts/gcn_search/diagnose_ieee39_gcn_audit_evidence_gap.py",
    "scripts/gcn_search/prepare_ieee39_paper_aligned_branch_gcn_redesign_dry_run.py",
    "scripts/gcn_search/prepare_ieee39_paper_aligned_feature_source_dry_run.py",
    "scripts/gcn_search/prepare_ieee39_static_operating_point_feature_source_dry_run.py",
    "scripts/gcn_search/approve_ieee39_relay_threshold_proxy.py",
    "scripts/gcn_search/prepare_ieee39_paper_style_branch_vulnerability_label_generator_dry_run.py",
    "scripts/gcn_search/generate_ieee39_base_state_branch_vulnerability_label_pilot.py",
    "scripts/gcn_search/prepare_ieee39_single_outage_label_loop_dry_run.py",
    "scripts/gcn_search/prepare_ieee39_single_outage_pilot_pair_generation_runner_dry_run.py",
    "scripts/gcn_search/execute_ieee39_selected_single_outage_pilot_pairs.py",
    "scripts/gcn_search/diagnose_ieee39_controlled_execution_backend.py",
    "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
    "scripts/gcn_search/repair_ieee39_l15_handwired_validation_readiness.py",
    "scripts/gcn_search/parse_ieee39_selected_pair_execution_evidence.py",
    "matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m",
    "tests/test_ieee39_v2_plus_all_bus_fault_preview_no_leakage.py",
    "tests/test_ieee39_gcn_usefulness_audit_plan.py",
    "tests/test_ieee39_gcn_usefulness_audit_dry_run_validator.py",
    "tests/test_ieee39_strict_no_leakage_gcn_usefulness_audit_execution.py",
    "tests/test_ieee39_gcn_audit_evidence_diagnosis.py",
    "tests/test_ieee39_paper_aligned_branch_gcn_redesign_dry_run.py",
    "tests/test_ieee39_paper_aligned_branch_gcn_redesign_consistency_check.py",
    "tests/test_ieee39_paper_aligned_feature_source_dry_run.py",
    "tests/test_ieee39_static_operating_point_feature_source_dry_run.py",
    "tests/test_ieee39_relay_threshold_proxy_approval.py",
    "tests/test_ieee39_paper_style_branch_vulnerability_label_generator_dry_run.py",
    "tests/test_ieee39_base_state_branch_vulnerability_label_pilot.py",
    "tests/test_ieee39_single_outage_label_loop_dry_run.py",
    "tests/test_ieee39_single_outage_pilot_pair_generation_runner_dry_run.py",
    "tests/test_ieee39_selected_single_outage_pilot_pair_execution.py",
    "tests/test_ieee39_controlled_execution_backend_diagnosis.py",
    "tests/test_ieee39_controlled_execution_backend_repair.py",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_fault_injection_points.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_fault_block_parameter_inventory.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_pilot_trip_implementation_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_pilot_trip_implementation_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_port_inventory.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_port_inventory.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_compatible_breaker_candidates.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_compatible_breaker_candidates.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/breaker_probe/breaker_probe_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/breaker_probe/breaker_probe_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/breaker_probe/breaker_probe_error_log.txt",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_timed_switch_insertion_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_timed_switch_insertion_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/handwired_breaker_checklist.txt",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_validation_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_validation_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_block_inventory.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/multi_handwired_breaker_checklist.txt",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_prepare_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_per_line_prepare_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_prepare_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_prepare_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_block_inventory.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_remaining_prepare_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_remaining_prepare_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/clean_breaker_lab_checklist.txt",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/clean_breaker_lab_per_line_checklist.txt",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/clean_breaker_lab_batch_checklist.txt",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_l12_islanding_diagnosis.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_l12_islanding_diagnosis.md",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_validation_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_validation_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_block_inventory.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_line_trip_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_signal_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_event_log.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_merge_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_L03_line_trip_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l03_merge_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_line_trip_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_signal_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_event_log.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l04_l05_merge_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l06_l07_l08_merge_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l09_l10_merge_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10_l11_to_l34.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l11_to_l34_merge_summary.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_dataset.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_config.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_predictions.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_model_coefficients.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_dynamic_aware_reranker_model.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_readme.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_dataset.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_config.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_predictions.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_model_coefficients.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_dynamic_aware_reranker_model.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_readme.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_comparison.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_comparison.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_dataset.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_config.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_metrics.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_predictions.csv",
    "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_feature_sets.json",
    "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_summary.md",
    "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_leakage_notes.md",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_multi_handwired_line_trip_summary.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_multi_handwired.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_multi_handwired_merge_summary.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_signal_extraction_debug.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_simlog_tree_inventory.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_simlog_tree_inventory.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/protection/ieee39_basic_relay_settings.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/protection/ieee39_basic_relay_status.json",
    "results/gcn_search/ieee39_graphical_dynamic_model/ieee39_vs_simplified_comparison.csv",
    "results/gcn_search/ieee39_graphical_dynamic_model/ieee39_vs_simplified_comparison.json",
]


DISALLOWED_TRACKED_SUBSTRINGS = [
    ".venv",
    "venv/",
    "site-packages",
    ".pt",
    ".pth",
    ".ckpt",
    ".npz",
    ".pkl",
    ".whl",
    ".dll",
    ".slx",
    ".slxc",
    ".mat",
    ".mdl",
    "slprj",
    "full_truth",
    "smoke_truth",
    "simulation_results",
    "scenario_checkpoints",
    "raw_trajectories",
    "dynamic_trajectories",
    "full_timeseries",
    "full timeseries",
    "large_checkpoint",
    "simulink_dynamic_results",
    "learned_mlp_per_path_ranking.csv",
    "per_path_ranking.csv",
    "path_reranker_dataset.csv",
    "path_reranker_train.csv",
    "path_reranker_val.csv",
    "path_reranker_test.csv",
    "large_simulink_log",
    "event_grid_",
    "local_lab_copies",
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


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json_path(path: Path) -> object:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def main() -> int:
    failures: list[str] = []

    for rel_path in REQUIRED_FILES:
        path = ROOT / rel_path
        if not os.path.exists(_fs_path(path)):
            failures.append(f"Missing required artifact: {rel_path}")
        elif os.path.isfile(_fs_path(path)) and os.path.getsize(_fs_path(path)) == 0:
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
        if "Round 57" not in log_text:
            failures.append("Validation log does not contain the Round 57 record.")
        if "Round 58" not in log_text:
            failures.append("Validation log does not contain the Round 58 record.")

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

    ieee39_docs = [
        "docs/ieee39_graphical_dynamic_model_selection.md",
        "docs/ieee39_graphical_dynamic_model_plan.md",
        "docs/ieee39_graphical_dynamic_model_status.md",
    ]
    for rel_doc in ieee39_docs:
        path = ROOT / rel_doc
        if path.exists():
            text = _read_text(rel_doc).lower()
            for required in ["ieee39", "dynamic", "not"]:
                if required not in text:
                    failures.append(f"IEEE39 doc missing required conservative context '{required}': {rel_doc}")
            for overstated in [
                "is an emt",
                "emt-level conclusion",
                "is an engineering-grade conclusion",
                "is an engineering-grade protection model",
                "dynamic-aware reranker training completed",
            ]:
                if overstated in text:
                    failures.append(f"Overstated IEEE39 claim in {rel_doc}: {overstated}")

    ieee39_inventory = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/model_inventory.csv"
    if ieee39_inventory.exists():
        try:
            import pandas as pd

            table = pd.read_csv(ieee39_inventory)
            required = {
                "model_path",
                "can_open_in_matlab",
                "contains_generators",
                "contains_exciters",
                "contains_governors",
                "contains_lines",
                "contains_loads",
                "contains_measurements",
                "contains_protection",
                "likely_model_type",
            }
            if not required.issubset(table.columns):
                failures.append("IEEE39 inventory is missing required columns.")
        except Exception as exc:
            failures.append(f"Failed to read IEEE39 inventory: {exc}")

    ieee39_schema = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_schema.json"
    if ieee39_schema.exists():
        text = ieee39_schema.read_text(encoding="utf-8", errors="ignore").lower()
        for required in ["dynamic_stress_score", "relay_trip_count", "breaker_trip_count", "this round does not train"]:
            if required not in text:
                failures.append(f"IEEE39 dynamic label schema missing: {required}")

    validation_log = ROOT / "docs/gcn_pio_validation_log.md"
    if validation_log.exists() and "round 27" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 27.")
    if validation_log.exists() and "round 28" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 28.")
    if validation_log.exists() and "round 29" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 29.")
    if validation_log.exists() and "round 30" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 30.")
    if validation_log.exists() and "round 31" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 31.")
    if validation_log.exists() and "round 32" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 32.")
    if validation_log.exists() and "round 42" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 42.")
    if validation_log.exists() and "round 53: ieee39 b39 candidate label export" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 53 B39 candidate export.")
    if validation_log.exists() and "round 54: ieee39 v2-plus-b39 schema fix and no-training composition review" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 54 v2-plus-B39 composition review.")
    if validation_log.exists() and "round 55: ieee39 v2-plus-b39 dynamic-aware reranker preview training" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 55 v2-plus-B39 preview training.")
    if validation_log.exists() and "round 56: b39 preview interpretation and b26 manual verification prep" not in _read_text("docs/gcn_pio_validation_log.md").lower():
        failures.append("Validation log must contain Round 56 B26 manual verification prep.")

    non_line_dir = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion"
    non_line_manifest = non_line_dir / "ieee39_non_line_trip_scenario_manifest.csv"
    non_line_taxonomy = non_line_dir / "ieee39_non_line_trip_fault_taxonomy.json"
    non_line_feasibility = non_line_dir / "ieee39_non_line_trip_feasibility_report.json"
    non_line_dry_run = non_line_dir / "ieee39_non_line_trip_dry_run_commands.txt"
    if non_line_manifest.exists() and non_line_taxonomy.exists() and non_line_feasibility.exists():
        try:
            import json
            import pandas as pd

            manifest = pd.read_csv(non_line_manifest)
            taxonomy = json.loads(non_line_taxonomy.read_text(encoding="utf-8"))
            feasibility = json.loads(non_line_feasibility.read_text(encoding="utf-8"))
            if manifest.empty:
                failures.append("Non-line-trip scenario manifest must not be empty.")
            if manifest["scenario_id"].duplicated().any():
                failures.append("Non-line-trip scenario IDs must be unique.")
            joined = manifest.to_json().lower()
            for forbidden in ["l12", "handwired_timed_breaker", "single_line_trip"]:
                if forbidden in joined:
                    failures.append(f"Non-line-trip manifest must not contain {forbidden}.")
            if "fault_duration_sweep" not in set(manifest["fault_type"].astype(str)):
                failures.append("Non-line-trip manifest must include a fault_duration_sweep scenario.")
            if not {"requires_slx_modification", "runnable_with_existing_scripts"}.issubset(manifest.columns):
                failures.append("Non-line-trip manifest missing slx/runnable fields.")
            tax_types = {row.get("fault_type") for row in taxonomy}
            for required_type in [
                "three_phase_bus_fault_clear",
                "fault_duration_sweep",
                "relay_proxy_fault",
                "load_step_disturbance",
                "generator_trip_or_mechanical_power_step",
                "bus_voltage_disturbance_or_reference_event",
            ]:
                if required_type not in tax_types:
                    failures.append(f"Non-line-trip taxonomy missing {required_type}.")
            if feasibility.get("simulink_was_run") is not False:
                failures.append("Non-line-trip feasibility must record simulink_was_run=false.")
            if feasibility.get("slx_modified") is not False:
                failures.append("Non-line-trip feasibility must record slx_modified=false.")
            if feasibility.get("training_ready_label_count_changed") is not False:
                failures.append("Non-line-trip feasibility must not change training-ready label counts.")
        except Exception as exc:
            failures.append(f"Failed to read non-line-trip expansion artifacts: {exc}")

    if non_line_dry_run.exists():
        text = non_line_dry_run.read_text(encoding="utf-8", errors="ignore").lower()
        if "do not execute automatically" not in text:
            failures.append("Non-line-trip dry-run commands must be marked as dry run only.")
        for forbidden in ["l12", "handwired_timed_breaker", "single_line_trip"]:
            if forbidden in text:
                failures.append(f"Non-line-trip dry-run commands must not contain {forbidden}.")

    non_line_doc = ROOT / "docs/ieee39_non_line_trip_fault_type_expansion.md"
    if non_line_doc.exists():
        text = _read_text("docs/ieee39_non_line_trip_fault_type_expansion.md").lower()
        for required in [
            "does not create new training-ready labels",
            "did not run simulink",
            "no `.slx` file was modified",
            "l12 was not fixed",
            "no dynamic-aware reranker retraining",
            "phasor_rms, not emt",
            "generator_speed_proxy` is not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in text:
                failures.append(f"Non-line-trip expansion doc missing: {required}")

    non_line_smoke_summary = non_line_dir / "ieee39_non_line_trip_smoke_test_summary.csv"
    non_line_smoke_report = non_line_dir / "ieee39_non_line_trip_smoke_test_report.json"
    if non_line_smoke_summary.exists() and non_line_smoke_report.exists():
        try:
            import json
            import pandas as pd

            table = pd.read_csv(non_line_smoke_summary)
            report = json.loads(non_line_smoke_report.read_text(encoding="utf-8"))
            expected_ids = {"NF01", "NF02", "NF03", "NF04", "NF06"}
            if set(table.get("scenario_id", pd.Series(dtype=str)).astype(str)) != expected_ids:
                failures.append("Non-line-trip smoke summary must contain exactly NF01/NF02/NF03/NF04/NF06.")
            if set(report.get("scenario_ids_requested", [])) != expected_ids:
                failures.append("Non-line-trip smoke report must request exactly NF01/NF02/NF03/NF04/NF06.")
            joined = table.to_json().lower()
            for forbidden in ["l12", "handwired_timed_breaker", "single_line_trip"]:
                if forbidden in joined:
                    failures.append(f"Non-line-trip smoke summary must not contain {forbidden}.")
            successful = table[table.get("training_ready_candidate_smoke", pd.Series(dtype=bool)).astype(bool)]
            if not successful.empty:
                if not successful["measurement_extraction_status"].astype(str).eq("voltage_speed_angle").all():
                    failures.append("Successful non-line-trip smoke rows must have voltage_speed_angle measurements.")
                if not successful["signal_source_summary"].astype(str).str.contains("frequency=generator_speed_proxy", regex=False).all():
                    failures.append("Successful non-line-trip smoke rows must use generator_speed_proxy frequency.")
            if report.get("whether_formal_label_gate_changed") is not False:
                failures.append("Non-line-trip smoke report must preserve formal label gate.")
            if report.get("whether_reranker_retrained") is not False:
                failures.append("Non-line-trip smoke report must not retrain reranker.")
            if report.get("whether_slx_modified") is not False:
                failures.append("Non-line-trip smoke report must record slx_modified=false.")
            if report.get("whether_l12_touched") is not False:
                failures.append("Non-line-trip smoke report must record L12 untouched.")
        except Exception as exc:
            failures.append(f"Failed to read non-line-trip smoke artifacts: {exc}")

    non_line_smoke_doc = ROOT / "docs/ieee39_non_line_trip_fault_smoke_tests.md"
    if non_line_smoke_doc.exists():
        text = _read_text("docs/ieee39_non_line_trip_fault_smoke_tests.md").lower()
        for required in [
            "nf01",
            "nf02",
            "nf03",
            "nf04",
            "nf06",
            "did not modify `.slx`",
            "did not fix l12",
            "did not update the formal training-ready label count",
            "did not retrain the dynamic-aware reranker",
            "smoke-test success is not a formal merge into training-ready dynamic labels",
            "phasor_rms, not emt",
            "generator_speed_proxy` is not direct frequency",
            "relay proxy is not engineering-grade protection",
        ]:
            if required not in text:
                failures.append(f"Non-line-trip smoke doc missing: {required}")

    bus_fault_dir = non_line_dir / "bus_fault_smoke"
    bus_feasibility = bus_fault_dir / "ieee39_bus_fault_injection_feasibility.json"
    bus_manifest = bus_fault_dir / "ieee39_bus_fault_smoke_scenario_manifest.csv"
    bus_summary = bus_fault_dir / "ieee39_bus_fault_smoke_test_summary.csv"
    bus_report = bus_fault_dir / "ieee39_bus_fault_smoke_test_report.json"
    if bus_feasibility.exists() and bus_manifest.exists() and bus_summary.exists() and bus_report.exists():
        try:
            import json
            import pandas as pd

            feasibility = json.loads(bus_feasibility.read_text(encoding="utf-8"))
            manifest = pd.read_csv(bus_manifest)
            summary = pd.read_csv(bus_summary)
            report = json.loads(bus_report.read_text(encoding="utf-8"))
            expected_ids = {"BF01", "BF02", "BF03", "BF04"}
            if set(manifest.get("scenario_id", pd.Series(dtype=str)).astype(str)) != expected_ids:
                failures.append("Bus-fault manifest must contain exactly BF01/BF02/BF03/BF04.")
            if set(summary.get("scenario_id", pd.Series(dtype=str)).astype(str)) != expected_ids:
                failures.append("Bus-fault summary must contain exactly BF01/BF02/BF03/BF04.")
            if len(manifest.get("scenario_id", pd.Series(dtype=str))) != len(set(manifest.get("scenario_id", pd.Series(dtype=str)).astype(str))):
                failures.append("Bus-fault manifest scenario_id values must be unique.")
            joined = manifest.to_json().lower() + summary.to_json().lower()
            for forbidden in ["l12", "handwired", "single_line_trip"]:
                if forbidden in joined:
                    failures.append(f"Bus-fault artifacts must not contain {forbidden}.")
            if manifest.get("requires_source_slx_modification", pd.Series(dtype=bool)).astype(bool).any():
                failures.append("Bus-fault manifest must require no source .slx modification.")
            if "source_slx_modified" in summary.columns and summary["source_slx_modified"].astype(bool).any():
                failures.append("Bus-fault summary must record source_slx_modified=false for all rows.")
            successful = summary[summary.get("training_ready_candidate_smoke", pd.Series(dtype=bool)).astype(bool)]
            if not successful.empty:
                if not successful["measurement_extraction_status"].astype(str).eq("voltage_speed_angle").all():
                    failures.append("Successful bus-fault smoke rows must have voltage_speed_angle measurements.")
                if not successful["signal_source_summary"].astype(str).str.contains("frequency=generator_speed_proxy", regex=False).all():
                    failures.append("Successful bus-fault smoke rows must use generator_speed_proxy frequency.")
            if feasibility.get("source_slx_modified") is not False:
                failures.append("Bus-fault feasibility must record source_slx_modified=false.")
            if feasibility.get("formal_label_gate_changed") is not False:
                failures.append("Bus-fault feasibility must preserve the formal label gate.")
            if feasibility.get("reranker_retrained") is not False:
                failures.append("Bus-fault feasibility must not retrain reranker.")
            if feasibility.get("gcn_trained") is not False:
                failures.append("Bus-fault feasibility must not train GCN.")
            if feasibility.get("l12_touched") is not False:
                failures.append("Bus-fault feasibility must keep L12 untouched.")
            if feasibility.get("old_formal_gate") != "35 / 33 / 33":
                failures.append("Bus-fault feasibility must preserve old formal gate 35 / 33 / 33.")
            if feasibility.get("v2_candidate_count_unchanged") != 40:
                failures.append("Bus-fault feasibility must preserve v2 candidate count 40.")
            if report.get("whether_source_slx_modified") is not False:
                failures.append("Bus-fault report must record source .slx unchanged.")
            if report.get("whether_formal_label_gate_changed") is not False:
                failures.append("Bus-fault report must preserve formal label gate.")
            if report.get("whether_reranker_retrained") is not False:
                failures.append("Bus-fault report must not retrain reranker.")
            if report.get("whether_gcn_trained") is not False:
                failures.append("Bus-fault report must not train GCN.")
            if report.get("whether_l12_touched") is not False:
                failures.append("Bus-fault report must keep L12 untouched.")
        except Exception as exc:
            failures.append(f"Failed to read bus-fault smoke artifacts: {exc}")

    bus_fault_doc = ROOT / "docs/ieee39_bus_fault_smoke_tests.md"
    if bus_fault_doc.exists():
        text = _read_text("docs/ieee39_bus_fault_smoke_tests.md").lower()
        for required in [
            "different-bus three-phase fault",
            "bf01",
            "bf02",
            "does not train gcn",
            "does not retrain",
            "does not update the label gate",
            "does not export",
            "l12 remains excluded",
            "phasor_rms, not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in text:
                failures.append(f"Bus-fault smoke doc missing: {required}")

    temp_lab_dir = bus_fault_dir / "temp_lab_plans"
    temp_lab_smoke_dir = bus_fault_dir / "temp_lab_smoke_outputs"
    temp_summary = temp_lab_dir / "ieee39_bus_fault_temp_lab_feasibility_summary.json"
    temp_smoke_report = temp_lab_smoke_dir / "ieee39_bus_fault_temp_lab_smoke_report.json"
    if temp_summary.exists():
        try:
            import json

            summary = json.loads(temp_summary.read_text(encoding="utf-8"))
            if summary.get("preview_only") is not True:
                failures.append("Bus-fault temp-lab summary must set preview_only=true.")
            if summary.get("target_buses_attempted") != ["B26", "B39"]:
                failures.append("Bus-fault temp-lab summary must record B26/B39 attempts.")
            for key in [
                "target_buses_with_injection_point_found",
                "target_buses_safe_to_run_smoke",
                "target_buses_smoke_successful",
                "target_buses_smoke_failed",
            ]:
                if summary.get(key) != []:
                    failures.append(f"Bus-fault temp-lab summary must keep {key} empty.")
            for key in [
                "source_slx_modified",
                "source_slx_committed",
                "temporary_slx_committed",
                "formal_label_gate_changed",
                "v2_candidate_count_changed",
                "reranker_retrained",
                "gcn_trained",
                "labels_exported",
                "l12_touched",
            ]:
                if summary.get(key) is not False:
                    failures.append(f"Bus-fault temp-lab summary must record {key}=false.")
            if summary.get("old_formal_gate") != "35 / 33 / 33":
                failures.append("Bus-fault temp-lab summary must preserve old formal gate 35 / 33 / 33.")
            if summary.get("v2_candidate_count") != 40:
                failures.append("Bus-fault temp-lab summary must preserve v2 candidate count 40.")

            for target_bus in ["B39", "B26"]:
                plan_path = temp_lab_dir / f"ieee39_bus_fault_temp_lab_{target_bus}_plan.json"
                inventory_path = temp_lab_dir / f"matlab_bus_fault_injection_inventory_{target_bus}.json"
                if not plan_path.exists() or not inventory_path.exists():
                    failures.append(f"Bus-fault temp-lab missing plan/inventory for {target_bus}.")
                    continue
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
                if plan.get("target_bus") != target_bus or inventory.get("target_bus") != target_bus:
                    failures.append(f"Bus-fault temp-lab target bus mismatch for {target_bus}.")
                for key in [
                    "source_slx_modified",
                    "source_slx_committed",
                    "temporary_slx_committed",
                    "reranker_retrained",
                    "gcn_trained",
                    "labels_exported",
                    "l12_touched",
                ]:
                    if plan.get(key) is not False:
                        failures.append(f"Bus-fault temp-lab plan {target_bus} must record {key}=false.")
                if plan.get("temporary_model_is_ignored") is not True:
                    failures.append(f"Bus-fault temp-lab plan {target_bus} must use ignored temporary model.")
                if plan.get("formal_label_gate") != "35 / 33 / 33":
                    failures.append(f"Bus-fault temp-lab plan {target_bus} must preserve old formal gate.")
                if plan.get("v2_candidate_count") != 40:
                    failures.append(f"Bus-fault temp-lab plan {target_bus} must preserve v2 candidate count.")
                if inventory.get("source_model_modified") is not False:
                    failures.append(f"Bus-fault temp-lab inventory {target_bus} must keep source model unchanged.")
                if inventory.get("injection_point_found") is not False:
                    failures.append(f"Bus-fault temp-lab inventory {target_bus} must not claim injection point found.")
                if inventory.get("fault_block_added_to_temp_copy") is not False:
                    failures.append(f"Bus-fault temp-lab inventory {target_bus} must not add fault block.")
                if inventory.get("safe_to_run_smoke") is not False:
                    failures.append(f"Bus-fault temp-lab inventory {target_bus} must not allow smoke yet.")
                if inventory.get("manual_review_required") is not True:
                    failures.append(f"Bus-fault temp-lab inventory {target_bus} must require manual review.")
                if not inventory.get("candidate_block_paths"):
                    failures.append(f"Bus-fault temp-lab inventory {target_bus} must include candidate blocks.")
        except Exception as exc:
            failures.append(f"Failed to read bus-fault temp-lab artifacts: {exc}")

    if temp_smoke_report.exists():
        try:
            import json

            report = json.loads(temp_smoke_report.read_text(encoding="utf-8"))
            if report.get("preview_only") is not True:
                failures.append("Bus-fault temp-lab smoke report must set preview_only=true.")
            if report.get("target_bus") != "B39":
                failures.append("Bus-fault temp-lab smoke report must be the B39 dry-run report.")
            if report.get("safe_to_run_smoke") is not False:
                failures.append("Bus-fault temp-lab smoke report must record safe_to_run_smoke=false.")
            if report.get("smoke_executed") is True:
                if report.get("human_readiness_ready") is not True:
                    failures.append("Executed B39 temp-lab smoke must require human_readiness_ready=true.")
                if report.get("scenario_ids_requested") != ["BF_B39_TEMP_SMOKE"]:
                    failures.append("Executed B39 temp-lab smoke must request BF_B39_TEMP_SMOKE only.")
                if report.get("simulation_success") is True:
                    if report.get("scenario_ids_successful") != ["BF_B39_TEMP_SMOKE"]:
                        failures.append("Successful B39 temp-lab smoke must record BF_B39_TEMP_SMOKE as successful.")
                elif not report.get("smoke_not_run_reason"):
                    failures.append("Failed B39 temp-lab smoke must record a non-empty error reason.")
            elif report.get("human_readiness_used") is True:
                if report.get("human_readiness_ready") is not True:
                    failures.append("Bus-fault temp-lab smoke report must record human_readiness_ready=true.")
                if report.get("smoke_not_run_reason") != "ready_for_next_round_temp_smoke":
                    failures.append("Bus-fault temp-lab smoke report must record ready_for_next_round_temp_smoke.")
            elif "safe_to_run_smoke=false" not in str(report.get("smoke_not_run_reason", "")):
                failures.append("Bus-fault temp-lab smoke report must explain safe_to_run_smoke=false.")
            for key in [
                "whether_source_slx_modified",
                "whether_temporary_slx_committed",
                "whether_formal_label_gate_changed",
                "whether_v2_candidate_count_changed",
                "whether_labels_exported",
                "whether_gcn_trained",
                "whether_reranker_retrained",
                "whether_l12_touched",
            ]:
                if report.get(key) is not False:
                    failures.append(f"Bus-fault temp-lab smoke report must record {key}=false.")
            for key in [
                "source_slx_modified",
                "temporary_slx_committed",
                "formal_label_gate_changed",
                "v2_candidate_count_changed",
                "reranker_retrained",
                "gcn_trained",
                "labels_exported",
                "l12_touched",
            ]:
                if report.get(key) is not False:
                    failures.append(f"Bus-fault temp-lab smoke report must record {key}=false.")
        except Exception as exc:
            failures.append(f"Failed to read bus-fault temp-lab smoke report: {exc}")

    b39_human_readiness = temp_lab_dir / "ieee39_bus_fault_b39_human_verified_readiness.json"
    b39_dry_run_readiness = temp_lab_smoke_dir / "ieee39_b39_temp_smoke_dry_run_readiness.json"
    if b39_human_readiness.exists():
        try:
            import json

            readiness = json.loads(b39_human_readiness.read_text(encoding="utf-8"))
            expected = {
                "target_bus": "B39",
                "manual_review_recommendation": "manual_review_supports_next_round_inventory_update",
                "selected_injection_block_path": "Grid/Bus39",
                "selected_fault_block_path": "Grid/Fault_B39_TEMP",
                "formal_label_gate": "35 / 33 / 33",
                "v2_candidate_count": 40,
                "b26_status": "unverified",
                "recommended_next_step": "run B39 temporary smoke in a separate round",
            }
            for key, value in expected.items():
                if readiness.get(key) != value:
                    failures.append(f"B39 human readiness must record {key}={value!r}.")
            for key in ["human_verified_injection_point", "safe_to_run_smoke_recommendation", "update_diagram_success"]:
                if readiness.get(key) is not True:
                    failures.append(f"B39 human readiness must record {key}=true.")
            for key in [
                "source_model_saved",
                "temporary_model_committed",
                "source_slx_modified",
                "temporary_slx_committed",
                "simulink_smoke_run",
                "smoke_success",
                "labels_exported",
                "gcn_trained",
                "reranker_retrained",
                "l12_touched",
            ]:
                if readiness.get(key) is not False:
                    failures.append(f"B39 human readiness must record {key}=false.")
        except Exception as exc:
            failures.append(f"Failed to read B39 human readiness: {exc}")

    if b39_dry_run_readiness.exists():
        try:
            import json

            dry = json.loads(b39_dry_run_readiness.read_text(encoding="utf-8"))
            expected = {
                "target_bus": "B39",
                "readiness_status": "ready_for_next_round_temp_smoke",
                "selected_injection_block_path": "Grid/Bus39",
                "selected_fault_block_path": "Grid/Fault_B39_TEMP",
                "formal_label_gate": "35 / 33 / 33",
                "v2_candidate_count": 40,
            }
            for key, value in expected.items():
                if dry.get(key) != value:
                    failures.append(f"B39 dry-run readiness must record {key}={value!r}.")
            for key in ["dry_run", "would_run_smoke_next_round"]:
                if dry.get(key) is not True:
                    failures.append(f"B39 dry-run readiness must record {key}=true.")
            for key in [
                "actual_simulink_run",
                "source_slx_modified",
                "temporary_slx_committed",
                "labels_exported",
                "gcn_trained",
                "reranker_retrained",
                "simulink_smoke_run",
                "smoke_success",
                "source_model_saved",
                "temporary_model_committed",
            ]:
                if dry.get(key) is not False:
                    failures.append(f"B39 dry-run readiness must record {key}=false.")
        except Exception as exc:
            failures.append(f"Failed to read B39 dry-run readiness: {exc}")

    b26_human_readiness = temp_lab_dir / "ieee39_bus_fault_b26_human_verified_readiness.json"
    b26_dry_run_readiness = temp_lab_smoke_dir / "ieee39_b26_temp_smoke_dry_run_readiness.json"
    if b26_human_readiness.exists():
        try:
            import json

            readiness = json.loads(b26_human_readiness.read_text(encoding="utf-8"))
            expected = {
                "target_bus": "B26",
                "manual_review_recommendation": "manual_review_supports_next_round_inventory_update",
                "selected_injection_block_path": "Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node",
                "selected_fault_block_path": "Grid/Fault_B26_TEMP",
                "formal_label_gate": "35 / 33 / 33",
                "v2_plus_b39_count": 41,
                "b39_status": "candidate_label_not_formal",
                "recommended_next_step": "run B26 temporary smoke in a separate round",
            }
            for key, value in expected.items():
                if readiness.get(key) != value:
                    failures.append(f"B26 human readiness must record {key}={value!r}.")
            for key in [
                "human_verified_injection_point",
                "safe_to_run_smoke_recommendation",
                "update_diagram_success",
                "old_fault_still_near_b16",
                "enable_temporal_fault",
            ]:
                if readiness.get(key) is not True:
                    failures.append(f"B26 human readiness must record {key}=true.")
            for key in [
                "source_model_saved",
                "temporary_model_committed",
                "source_slx_modified",
                "temporary_slx_committed",
                "simulink_smoke_run",
                "smoke_success",
                "labels_exported",
                "gcn_trained",
                "reranker_retrained",
                "l12_touched",
            ]:
                if readiness.get(key) is not False:
                    failures.append(f"B26 human readiness must record {key}=false.")
        except Exception as exc:
            failures.append(f"Failed to read B26 human readiness: {exc}")

    if b26_dry_run_readiness.exists():
        try:
            import json

            dry = json.loads(b26_dry_run_readiness.read_text(encoding="utf-8"))
            expected = {
                "target_bus": "B26",
                "readiness_status": "ready_for_next_round_temp_smoke",
                "selected_injection_block_path": "Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node",
                "selected_fault_block_path": "Grid/Fault_B26_TEMP",
                "formal_label_gate": "35 / 33 / 33",
                "v2_plus_b39_count": 41,
                "b39_status": "candidate_label_not_formal",
                "recommended_next_step": "run actual B26 temporary smoke in a separate round",
            }
            for key, value in expected.items():
                if dry.get(key) != value:
                    failures.append(f"B26 dry-run readiness must record {key}={value!r}.")
            for key in ["dry_run", "would_run_smoke_next_round"]:
                if dry.get(key) is not True:
                    failures.append(f"B26 dry-run readiness must record {key}=true.")
            for key in [
                "actual_simulink_run",
                "source_slx_modified",
                "temporary_slx_committed",
                "labels_exported",
                "gcn_trained",
                "reranker_retrained",
                "simulink_smoke_run",
                "smoke_success",
                "source_model_saved",
                "temporary_model_committed",
            ]:
                if dry.get(key) is not False:
                    failures.append(f"B26 dry-run readiness must record {key}=false.")
        except Exception as exc:
            failures.append(f"Failed to read B26 dry-run readiness: {exc}")

    b26_smoke_report = temp_lab_smoke_dir / "ieee39_b26_bus_fault_temp_lab_smoke_report.json"
    b26_smoke_summary = temp_lab_smoke_dir / "ieee39_b26_bus_fault_temp_lab_smoke_summary.csv"
    if b26_smoke_report.exists():
        try:
            import json
            import math

            report = json.loads(b26_smoke_report.read_text(encoding="utf-8"))
            expected = {
                "target_bus": "B26",
                "scenario_id": "BF_B26_TEMP_SMOKE",
                "selected_fault_block_path": "Grid/Fault_B26_TEMP",
                "selected_injection_block_path": "Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node",
                "old_formal_gate": "35 / 33 / 33",
                "v2_plus_b39_count": 41,
                "b39_status": "candidate_label_not_formal",
            }
            for key, value in expected.items():
                if report.get(key) != value:
                    failures.append(f"B26 smoke report must record {key}={value!r}.")
            for key in ["actual_simulink_run", "human_readiness_used", "human_readiness_ready"]:
                if report.get(key) is not True:
                    failures.append(f"B26 smoke report must record {key}=true.")
            for key in [
                "dry_run",
                "source_slx_modified",
                "temporary_slx_committed",
                "labels_exported",
                "gcn_trained",
                "reranker_retrained",
                "formal_label_gate_changed",
                "v2_plus_b39_count_changed",
                "l12_touched",
            ]:
                if report.get(key) is not False:
                    failures.append(f"B26 smoke report must record {key}=false.")
            if report.get("simulation_success") is True:
                if report.get("physical_fault_or_breaker_action_executed") is not True:
                    failures.append("B26 successful smoke must record physical_fault_or_breaker_action_executed=true.")
                if report.get("measurement_extraction_status") != "voltage_speed_angle":
                    failures.append("B26 successful smoke must record measurement_extraction_status=voltage_speed_angle.")
                if "frequency=generator_speed_proxy" not in str(report.get("signal_source_summary", "")):
                    failures.append("B26 successful smoke must record frequency=generator_speed_proxy.")
                for key in [
                    "min_voltage_pu",
                    "max_voltage_pu",
                    "min_frequency_hz",
                    "max_frequency_hz",
                    "max_speed_deviation",
                    "max_rotor_angle_separation_deg",
                ]:
                    try:
                        if not math.isfinite(float(report.get(key))):
                            failures.append(f"B26 successful smoke must have finite {key}.")
                    except (TypeError, ValueError):
                        failures.append(f"B26 successful smoke must have numeric {key}.")
                if "review B26 smoke output quality" not in str(report.get("recommended_next_step", "")):
                    failures.append("B26 successful smoke must recommend quality review before label export.")
            else:
                if not report.get("smoke_not_run_reason"):
                    failures.append("B26 failed smoke must record non-empty failure reason.")
                if "diagnose" not in str(report.get("recommended_next_step", "")).lower():
                    failures.append("B26 failed smoke must recommend diagnosis before label export.")
        except Exception as exc:
            failures.append(f"Failed to read B26 smoke report: {exc}")

    if b26_smoke_summary.exists():
        try:
            import csv

            with b26_smoke_summary.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            if len(rows) != 1:
                failures.append("B26 smoke summary must contain exactly one row.")
            else:
                row = rows[0]
                if row.get("scenario_id") != "BF_B26_TEMP_SMOKE":
                    failures.append("B26 smoke summary must record scenario_id=BF_B26_TEMP_SMOKE.")
                if row.get("target_bus") != "B26":
                    failures.append("B26 smoke summary must record target_bus=B26.")
                if row.get("source_slx_modified") != "False" or row.get("temporary_slx_committed") != "False":
                    failures.append("B26 smoke summary must preserve source_slx_modified=false and temporary_slx_committed=false.")
        except Exception as exc:
            failures.append(f"Failed to read B26 smoke summary: {exc}")

    b26_quality_review = temp_lab_smoke_dir / "ieee39_b26_temp_smoke_quality_review.json"
    if b26_quality_review.exists():
        try:
            import json

            quality = json.loads(b26_quality_review.read_text(encoding="utf-8"))
            expected = {
                "target_bus": "B26",
                "scenario_id": "BF_B26_TEMP_SMOKE",
                "measurement_extraction_status": "voltage_speed_angle",
                "old_formal_gate": "35 / 33 / 33",
                "v2_plus_b39_count": 41,
                "b39_status": "candidate_label_not_formal",
                "recommended_next_step": "export B26 bus-fault candidate label in a separate round, without training",
            }
            for key, value in expected.items():
                if quality.get(key) != value:
                    failures.append(f"B26 quality review must record {key}={value!r}.")
            for key in [
                "simulation_success",
                "physical_fault_or_breaker_action_executed",
                "training_ready_candidate_smoke",
                "signal_source_has_frequency_proxy",
                "dynamic_measurement_available",
                "metrics_all_finite",
                "old_formal_gate_preserved",
                "v2_plus_b39_count_preserved",
                "quality_review_passed_for_candidate_export",
            ]:
                if quality.get(key) is not True:
                    failures.append(f"B26 quality review must record {key}=true.")
            for key in [
                "labels_exported",
                "gcn_trained",
                "reranker_retrained",
                "source_slx_modified",
                "temporary_slx_committed",
                "l12_touched",
            ]:
                if quality.get(key) is not False:
                    failures.append(f"B26 quality review must record {key}=false.")
            for key in [
                "min_voltage_pu",
                "max_voltage_pu",
                "min_frequency_hz",
                "max_frequency_hz",
                "max_speed_deviation",
                "max_rotor_angle_separation_deg",
            ]:
                try:
                    if not math.isfinite(float(quality.get(key))):
                        failures.append(f"B26 quality review must have finite {key}.")
                except (TypeError, ValueError):
                    failures.append(f"B26 quality review must have numeric {key}.")
        except Exception as exc:
            failures.append(f"Failed to read B26 quality review: {exc}")

    b39_quality_review = temp_lab_smoke_dir / "ieee39_b39_temp_smoke_quality_review.json"
    if b39_quality_review.exists():
        try:
            import json

            quality = json.loads(b39_quality_review.read_text(encoding="utf-8"))
            expected = {
                "target_bus": "B39",
                "scenario_id": "BF_B39_TEMP_SMOKE",
                "measurement_extraction_status": "voltage_speed_angle",
                "old_formal_gate": "35 / 33 / 33",
                "v2_candidate_count": 40,
                "recommended_next_step": "export B39 bus-fault candidate label in a separate round, without training",
            }
            for key, value in expected.items():
                if quality.get(key) != value:
                    failures.append(f"B39 quality review must record {key}={value!r}.")
            for key in [
                "simulation_success",
                "physical_fault_or_breaker_action_executed",
                "training_ready_candidate_smoke",
                "signal_source_has_frequency_proxy",
                "min_voltage_near_zero",
                "unstable_flag",
                "dynamic_measurement_available",
                "old_formal_gate_preserved",
                "v2_candidate_count_preserved",
                "quality_review_passed_for_candidate_export",
            ]:
                if quality.get(key) is not True:
                    failures.append(f"B39 quality review must record {key}=true.")
            for key in [
                "labels_exported",
                "gcn_trained",
                "reranker_retrained",
                "source_slx_modified",
                "temporary_slx_committed",
                "l12_touched",
            ]:
                if quality.get(key) is not False:
                    failures.append(f"B39 quality review must record {key}=false.")
            for key in [
                "min_voltage_pu",
                "max_voltage_pu",
                "min_frequency_hz",
                "max_frequency_hz",
                "max_speed_deviation",
                "max_rotor_angle_separation_deg",
            ]:
                if quality.get(key) is None:
                    failures.append(f"B39 quality review missing numeric field {key}.")
        except Exception as exc:
            failures.append(f"Failed to read B39 quality review: {exc}")

    b39_export_dir = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export"
    b39_candidate_json = b39_export_dir / "ieee39_b39_bus_fault_dynamic_label_candidate.json"
    b39_combined_csv = b39_export_dir / "ieee39_dynamic_label_schema_v2_plus_b39_candidate.csv"
    b39_quality_summary = b39_export_dir / "ieee39_dynamic_label_quality_summary_v2_plus_b39_candidate.json"
    b39_readiness = b39_export_dir / "ieee39_dynamic_aware_training_readiness_v2_plus_b39_candidate.json"
    b39_provenance = b39_export_dir / "ieee39_b39_candidate_duplicate_provenance_report.md"
    if b39_candidate_json.exists() and b39_combined_csv.exists() and b39_quality_summary.exists() and b39_readiness.exists():
        try:
            import json
            import pandas as pd

            candidate = json.loads(b39_candidate_json.read_text(encoding="utf-8"))
            combined = pd.read_csv(b39_combined_csv)
            quality = json.loads(b39_quality_summary.read_text(encoding="utf-8"))
            readiness = json.loads(b39_readiness.read_text(encoding="utf-8"))

            expected_candidate = {
                "scenario_id": "BF_B39_TEMP_SMOKE",
                "target_bus": "B39",
                "target_bus_or_component": "B39",
                "fault_type": "three_phase_bus_fault_temp_smoke",
                "line_id": "NO_LINE",
                "measurement_extraction_status": "voltage_speed_angle",
                "schema_version": "ieee39_dynamic_label_schema_v2_plus_b39_candidate",
                "export_status": "candidate_only",
            }
            for key, value in expected_candidate.items():
                if candidate.get(key) != value:
                    failures.append(f"B39 candidate export must record {key}={value!r}.")
            if "frequency=generator_speed_proxy" not in str(candidate.get("signal_source_summary", "")):
                failures.append("B39 candidate export must preserve frequency=generator_speed_proxy.")
            expected_false = [
                "source_slx_modified",
                "temporary_slx_committed",
                "formal_line_trip_label",
                "handwired_line_trip_label",
            ]
            for key in expected_false:
                if _truthy(candidate.get(key)) is not False:
                    failures.append(f"B39 candidate export must record {key}=false.")
            expected_true = [
                "simulation_success",
                "physical_fault_or_breaker_action_executed",
                "human_verified_injection_point",
                "quality_review_passed_for_candidate_export",
                "training_ready_label_candidate",
                "non_line_trip_label",
                "bus_fault_label",
                "candidate_not_formal_label",
            ]
            for key in expected_true:
                if _truthy(candidate.get(key)) is not True:
                    failures.append(f"B39 candidate export must record {key}=true.")
            if len(combined) != 41:
                failures.append("v2-plus-B39 combined candidate schema must contain 41 rows.")
            b39_mask = combined.get("scenario_id", pd.Series(dtype=str)).astype(str) == "BF_B39_TEMP_SMOKE"
            if b39_mask.sum() != 1:
                failures.append("v2-plus-B39 combined candidate schema must contain exactly one B39 row.")
            else:
                b39_row = combined.loc[b39_mask].iloc[0]
                if b39_row.get("target_bus") != "B39":
                    failures.append("v2-plus-B39 B39 row must record target_bus=B39.")
                if b39_row.get("target_bus_or_component") != "B39":
                    failures.append("v2-plus-B39 B39 row must record target_bus_or_component=B39.")
                if b39_row.get("line_id") != "NO_LINE":
                    failures.append("v2-plus-B39 B39 row must record line_id=NO_LINE.")
                if b39_row.get("fault_type") != "three_phase_bus_fault_temp_smoke":
                    failures.append("v2-plus-B39 B39 row must preserve the bus-fault fault_type.")
                if not _truthy(b39_row.get("bus_fault_label")):
                    failures.append("v2-plus-B39 B39 row must record bus_fault_label=true.")
                if not _truthy(b39_row.get("candidate_not_formal_label")):
                    failures.append("v2-plus-B39 B39 row must record candidate_not_formal_label=true.")

            expected_quality = {
                "original_num_training_ready_labels": 35,
                "original_num_training_ready_handwired_line_trip_labels": 33,
                "original_num_unique_handwired_line_ids": 33,
                "previous_v2_candidate_count": 40,
                "num_new_b39_bus_fault_candidates": 1,
                "num_v2_plus_b39_candidate_labels": 41,
            }
            for key, value in expected_quality.items():
                if quality.get(key) != value:
                    failures.append(f"B39 quality summary must record {key}={value}.")
            for key in [
                "original_formal_gate_preserved",
                "b39_quality_review_passed",
                "b39_training_ready_candidate",
                "l12_excluded",
                "nf06_provenance_warning_preserved",
                "allowed_for_future_v2_plus_b39_preview",
            ]:
                if quality.get(key) is not True:
                    failures.append(f"B39 quality summary must record {key}=true.")
            for key in [
                "b39_formal_label",
                "gcn_trained",
                "reranker_retrained",
                "formal_label_gate_changed",
                "v2_preview_training_changed",
                "should_train_now",
            ]:
                if quality.get(key) is not False:
                    failures.append(f"B39 quality summary must record {key}=false.")
            if readiness.get("should_train_now") is not False:
                failures.append("B39 readiness must record should_train_now=false.")
            if readiness.get("num_v2_plus_b39_candidate_labels") != 41:
                failures.append("B39 readiness must record 41 v2-plus-B39 candidates.")
            if readiness.get("previous_v2_candidate_count") != 40:
                failures.append("B39 readiness must preserve previous_v2_candidate_count=40.")
            provenance_text = b39_provenance.read_text(encoding="utf-8", errors="ignore").lower()
            for required in ["no exact duplicate", "nf06 warning preserved", "l12 excluded"]:
                if required not in provenance_text:
                    failures.append(f"B39 provenance report missing: {required}")
        except Exception as exc:
            failures.append(f"Failed to read B39 candidate export artifacts: {exc}")

    b26_export_dir = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export"
    b26_candidate_json = b26_export_dir / "ieee39_b26_bus_fault_dynamic_label_candidate.json"
    b26_combined_csv = b26_export_dir / "ieee39_dynamic_label_schema_v2_plus_b39_b26_candidate.csv"
    b26_export_summary = b26_export_dir / "ieee39_b26_bus_fault_candidate_export_summary.json"
    b26_readiness = b26_export_dir / "ieee39_v2_plus_b39_b26_training_readiness.json"
    if b26_candidate_json.exists() and b26_combined_csv.exists() and b26_export_summary.exists() and b26_readiness.exists():
        try:
            import json
            import pandas as pd

            candidate = json.loads(b26_candidate_json.read_text(encoding="utf-8"))
            combined = pd.read_csv(b26_combined_csv)
            summary = json.loads(b26_export_summary.read_text(encoding="utf-8"))
            readiness = json.loads(b26_readiness.read_text(encoding="utf-8"))

            expected_candidate = {
                "scenario_id": "BF_B26_TEMP_SMOKE",
                "target_bus": "B26",
                "target_bus_or_component": "B26",
                "fault_type": "three_phase_bus_fault_temp_smoke",
                "line_id": "NO_LINE",
                "measurement_extraction_status": "voltage_speed_angle",
                "schema_version": "ieee39_dynamic_label_schema_v2_plus_b39_b26_candidate",
                "export_status": "candidate_only",
                "labels_exported_this_round": "candidate_only",
                "old_formal_gate": "35 / 33 / 33",
                "b39_status": "candidate_label_not_formal",
            }
            for key, value in expected_candidate.items():
                if candidate.get(key) != value:
                    failures.append(f"B26 candidate export must record {key}={value!r}.")
            if "frequency=generator_speed_proxy" not in str(candidate.get("signal_source_summary", "")):
                failures.append("B26 candidate export must preserve frequency=generator_speed_proxy.")
            try:
                score = float(candidate.get("dynamic_stress_score"))
                if not math.isfinite(score) or abs(score - 0.5314759474846006) > 1e-12:
                    failures.append("B26 candidate export must record the expected dynamic_stress_score.")
            except (TypeError, ValueError):
                failures.append("B26 candidate export must record numeric dynamic_stress_score.")
            expected_false = [
                "source_slx_modified",
                "temporary_slx_committed",
                "formal_line_trip_label",
                "handwired_line_trip_label",
                "gcn_trained",
                "reranker_retrained",
            ]
            for key in expected_false:
                if _truthy(candidate.get(key)) is not False:
                    failures.append(f"B26 candidate export must record {key}=false.")
            expected_true = [
                "simulation_success",
                "physical_fault_or_breaker_action_executed",
                "quality_review_passed_for_candidate_export",
                "training_ready_label_candidate",
                "training_ready_label_v2",
                "non_line_trip_label",
                "bus_fault_label",
                "temporary_smoke_candidate",
                "candidate_not_formal_label",
                "phasor_rms_not_emt",
                "generator_speed_proxy_not_direct_frequency",
                "temporary_bus_fault_not_engineering_grade_protection",
                "l12_excluded",
                "nf06_provenance_warning_preserved",
            ]
            for key in expected_true:
                if _truthy(candidate.get(key)) is not True:
                    failures.append(f"B26 candidate export must record {key}=true.")
            if len(combined) != 42:
                failures.append("v2-plus-B39+B26 combined candidate schema must contain 42 rows.")
            for scenario_id, bus in [("BF_B39_TEMP_SMOKE", "B39"), ("BF_B26_TEMP_SMOKE", "B26")]:
                mask = combined.get("scenario_id", pd.Series(dtype=str)).astype(str) == scenario_id
                if mask.sum() != 1:
                    failures.append(f"v2-plus-B39+B26 combined candidate schema must contain exactly one {scenario_id} row.")
                    continue
                row = combined.loc[mask].iloc[0]
                if row.get("target_bus") != bus:
                    failures.append(f"v2-plus-B39+B26 {scenario_id} row must record target_bus={bus}.")
                if row.get("target_bus_or_component") != bus:
                    failures.append(f"v2-plus-B39+B26 {scenario_id} row must record target_bus_or_component={bus}.")
                if row.get("line_id") != "NO_LINE":
                    failures.append(f"v2-plus-B39+B26 {scenario_id} row must record line_id=NO_LINE.")
                if row.get("fault_type") != "three_phase_bus_fault_temp_smoke":
                    failures.append(f"v2-plus-B39+B26 {scenario_id} row must preserve the bus-fault fault_type.")
                if not _truthy(row.get("bus_fault_label")):
                    failures.append(f"v2-plus-B39+B26 {scenario_id} row must record bus_fault_label=true.")
                if not _truthy(row.get("candidate_not_formal_label")):
                    failures.append(f"v2-plus-B39+B26 {scenario_id} row must record candidate_not_formal_label=true.")

            expected_summary = {
                "export_scope": "candidate_only",
                "target_bus": "B26",
                "scenario_id": "BF_B26_TEMP_SMOKE",
                "previous_v2_plus_b39_count": 41,
                "num_new_b26_bus_fault_candidates": 1,
                "num_v2_plus_b39_b26_candidate_labels": 42,
                "old_formal_gate": "35 / 33 / 33",
                "labels_exported_this_round": "candidate_only",
                "recommended_next_step": "run v2-plus-B39+B26 no-training composition review before any training",
            }
            for key, value in expected_summary.items():
                if summary.get(key) != value:
                    failures.append(f"B26 export summary must record {key}={value!r}.")
            for key in [
                "formal_label_gate_changed",
                "b26_formal_label",
                "gcn_trained",
                "reranker_retrained",
                "should_train_now",
            ]:
                if summary.get(key) is not False:
                    failures.append(f"B26 export summary must record {key}=false.")
            for key in [
                "b26_quality_review_passed",
                "b26_training_ready_candidate",
                "b26_candidate_not_formal_label",
                "l12_excluded",
                "nf06_provenance_warning_preserved",
            ]:
                if summary.get(key) is not True:
                    failures.append(f"B26 export summary must record {key}=true.")
            if readiness.get("candidate_count") != 42:
                failures.append("B26 readiness must record candidate_count=42.")
            if readiness.get("num_bus_fault_candidates") != 2:
                failures.append("B26 readiness must record two bus-fault candidates.")
            for key in ["ready_for_future_preview_training", "b39_candidate_present", "b26_candidate_present"]:
                if readiness.get(key) is not True:
                    failures.append(f"B26 readiness must record {key}=true.")
            if readiness.get("should_train_now") is not False:
                failures.append("B26 readiness must record should_train_now=false.")
        except Exception as exc:
            failures.append(f"Failed to read B26 candidate export artifacts: {exc}")

    b26_review_dir = b26_export_dir / "no_training_composition_review"
    b26_review_json = b26_review_dir / "ieee39_v2_plus_b39_b26_composition_review.json"
    b26_family_counts = b26_review_dir / "ieee39_v2_plus_b39_b26_label_family_counts.csv"
    b26_fault_counts = b26_review_dir / "ieee39_v2_plus_b39_b26_fault_type_counts.csv"
    b26_bus_fault_comparison = b26_review_dir / "ieee39_v2_plus_b39_b26_bus_fault_comparison.csv"
    if b26_review_json.exists() and b26_family_counts.exists() and b26_fault_counts.exists() and b26_bus_fault_comparison.exists():
        try:
            import json
            import pandas as pd

            review = json.loads(b26_review_json.read_text(encoding="utf-8"))
            family = pd.read_csv(b26_family_counts)
            fault = pd.read_csv(b26_fault_counts)
            comparison = pd.read_csv(b26_bus_fault_comparison)
            expected_review = {
                "review_scope": "no_training_composition_comparison",
                "previous_v2_plus_b39_count": 41,
                "v2_plus_b39_b26_candidate_count": 42,
                "num_new_b26_bus_fault_candidates": 1,
                "old_formal_gate": "35 / 33 / 33",
                "num_formal_v1_existing": 35,
                "num_handwired_line_trip": 33,
                "num_non_line_trip_candidates": 7,
                "num_bus_fault_candidates": 2,
                "b39_status": "candidate_label_not_formal",
                "b26_status": "candidate_label_not_formal",
                "recommended_next_step": "run v2-plus-B39+B26 preview/no-leakage comparison in a separate round, still not GCN usefulness audit",
            }
            for key, value in expected_review.items():
                if review.get(key) != value:
                    failures.append(f"B26 composition review must record {key}={value!r}.")
            for key in [
                "simulink_run",
                "labels_exported",
                "slx_submitted",
                "source_slx_modified",
                "gcn_trained",
                "reranker_retrained",
                "preview_training_run",
                "gcn_usefulness_audit_run",
                "should_train_now",
                "b39_exact_duplicate",
                "b26_exact_duplicate",
                "b39_b26_duplicate_measurement_group",
            ]:
                if review.get(key) is not False:
                    failures.append(f"B26 composition review must record {key}=false.")
            for key in [
                "b39_candidate_present",
                "b26_candidate_present",
                "l12_excluded",
                "nf06_provenance_warning_preserved",
                "bus_fault_target_bus_complete",
                "bus_fault_target_bus_or_component_complete",
                "bus_fault_line_id_no_line",
                "b39_b26_schema_consistency_passed",
                "count_consistency_passed",
                "export_boundary_passed",
                "leakage_risk_reviewed",
                "compact_dynamic_measurement_features_are_post_fault",
                "target_feature_leakage_risk_if_used_as_inputs",
                "all_no_training_composition_checks_passed",
            ]:
                if review.get(key) is not True:
                    failures.append(f"B26 composition review must record {key}=true.")
            if set(review.get("bus_fault_targets", [])) != {"B39", "B26"}:
                failures.append("B26 composition review must record bus_fault_targets B39 and B26.")
            if review.get("scenario_id_duplicates") != [] or review.get("label_id_v2_duplicates") != []:
                failures.append("B26 composition review must record no scenario_id / label_id duplicates.")

            family_counts = dict(zip(family["label_family"], family["count"]))
            fault_counts = dict(zip(fault["fault_type"], fault["count"]))
            if family_counts.get("existing_formal_dynamic") != 35 or family_counts.get("non_line_trip") != 7:
                failures.append("B26 composition review family counts must record 35 formal and 7 non_line_trip rows.")
            if fault_counts.get("three_phase_bus_fault_temp_smoke") != 2:
                failures.append("B26 composition review fault counts must record two bus-fault candidates.")
            if len(comparison) != 2 or set(comparison.get("scenario_id", pd.Series(dtype=str)).astype(str)) != {"BF_B39_TEMP_SMOKE", "BF_B26_TEMP_SMOKE"}:
                failures.append("B26 composition review bus-fault comparison must contain B39 and B26.")
            for _, row in comparison.iterrows():
                if row.get("target_bus") not in {"B39", "B26"}:
                    failures.append("B26 composition review comparison rows must target B39 or B26.")
                if row.get("target_bus_or_component") != row.get("target_bus"):
                    failures.append("B26 composition review comparison rows must keep target_bus_or_component complete.")
                if row.get("line_id") != "NO_LINE":
                    failures.append("B26 composition review comparison rows must use line_id=NO_LINE.")
        except Exception as exc:
            failures.append(f"Failed to read B26 composition review artifacts: {exc}")

    b26_preview_dir = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview"
    b26_preview_json = b26_preview_dir / "v2_plus_b39_b26_preview_comparison.json"
    b26_preview_md = b26_preview_dir / "v2_plus_b39_b26_preview_comparison.md"
    b26_preview_doc = ROOT / "docs/ieee39_v2_plus_b39_b26_preview_no_leakage_comparison.md"
    if b26_preview_json.exists() and b26_preview_md.exists() and b26_preview_doc.exists():
        try:
            import json

            comparison = json.loads(b26_preview_json.read_text(encoding="utf-8"))
            expected_values = {
                "preview_only": True,
                "final_performance_conclusion": False,
                "gcn_trained": False,
                "gcn_usefulness_audit_run": False,
                "formal_reranker_retrained": False,
                "simulink_run": False,
                "labels_exported": False,
                "old_formal_gate": "35 / 33 / 33",
                "v2_plus_b39_b26_candidate_count": 42,
                "previous_v2_plus_b39_count": 41,
                "num_bus_fault_candidates": 2,
                "b39_status": "candidate_label_not_formal",
                "b26_status": "candidate_label_not_formal",
                "l12_excluded": True,
                "nf06_provenance_warning_preserved": True,
                "leakage_risk_reviewed": True,
                "target_feature_leakage_risk_if_dynamic_measurements_used": True,
                "can_directly_validate_gcn": False,
            }
            for key, value in expected_values.items():
                if comparison.get(key) != value:
                    failures.append(f"v2-plus-B39+B26 preview comparison must record {key}={value!r}.")
            required_numeric = [
                "include_all_42_rmse",
                "exclude_provenance_required_rmse",
                "no_dynamic_measurement_rmse",
                "label_family_holdout_rmse",
                "bus_fault_holdout_rmse",
                "b39_holdout_absolute_error",
                "b26_holdout_absolute_error",
                "b39_true_dynamic_stress_score",
                "b39_predicted_dynamic_stress_score",
                "b26_true_dynamic_stress_score",
                "b26_predicted_dynamic_stress_score",
                "b39_unstable_probability",
                "b26_unstable_probability",
            ]
            for key in required_numeric:
                value = comparison.get(key)
                if not isinstance(value, (int, float)) or value < 0:
                    failures.append(f"v2-plus-B39+B26 preview comparison missing nonnegative numeric {key}.")
            if comparison.get("recommended_next_step") != "collect more bus-fault candidates before GCN usefulness audit":
                failures.append("v2-plus-B39+B26 preview comparison must recommend collecting more bus-fault candidates.")
            for mode in [
                "include_all_42_candidates",
                "exclude_provenance_required",
                "no_dynamic_measurement_features",
                "label_family_holdout",
                "bus_fault_holdout",
                "b39_holdout",
                "b26_holdout",
            ]:
                metrics_path = b26_preview_dir / mode / "preview_training_metrics.json"
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
                for key in [
                    "preview_only",
                    "dynamic_stress_score_is_proxy_target",
                ]:
                    if metrics.get(key) is not True:
                        failures.append(f"{mode} preview metrics must record {key}=true.")
                for key in [
                    "final_performance_conclusion",
                    "simulink_run",
                    "labels_exported",
                    "gcn_trained",
                    "gcn_usefulness_audit_run",
                    "formal_reranker_retrained",
                ]:
                    if metrics.get(key) is not False:
                        failures.append(f"{mode} preview metrics must record {key}=false.")
                if not metrics.get("regression_metrics"):
                    failures.append(f"{mode} preview metrics missing regression_metrics.")
                if mode == "no_dynamic_measurement_features":
                    forbidden = {
                        "min_voltage_pu",
                        "max_voltage_pu",
                        "min_frequency_hz",
                        "max_frequency_hz",
                        "max_speed_deviation",
                        "max_rotor_angle_separation_deg",
                        "dynamic_stress_score",
                        "unstable_flag",
                    }
                    if forbidden & set(metrics.get("feature_columns", [])):
                        failures.append("B39+B26 no_dynamic_measurement features contain leakage columns.")
            doc_text = "\n".join(
                [
                    b26_preview_md.read_text(encoding="utf-8", errors="ignore"),
                    b26_preview_doc.read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            for required in [
                "preview/no-leakage comparison",
                "does not train gcn",
                "does not run a gcn usefulness audit",
                "candidate labels, not formal labels",
                "phasor_rms`, not emt",
                "generator_speed_proxy` is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in doc_text:
                    failures.append(f"v2-plus-B39+B26 preview docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is not useful",
                "emt validation completed",
                "formal reranker has been retrained",
                "b39 and b26 are formal labels",
            ]:
                if bad in doc_text:
                    failures.append(f"v2-plus-B39+B26 preview docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read v2-plus-B39+B26 preview artifacts: {exc}")

    all_remaining_dir = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
    all_remaining_json = all_remaining_dir / "ieee39_bus_fault_all_remaining_targets.json"
    all_remaining_md = all_remaining_dir / "ieee39_bus_fault_all_remaining_targets.md"
    all_remaining_commands = all_remaining_dir / "all_remaining_manual_gui_wiring_commands.md"
    all_remaining_schema = all_remaining_dir / "batch_manual_connection_evidence_schema.json"
    all_remaining_gate = all_remaining_dir / "batch_gate_sequence.md"
    all_remaining_doc = ROOT / "docs/ieee39_all_remaining_bus_fault_manual_wiring_plan.md"
    if all_remaining_json.exists():
        try:
            normal_targets = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
            all_targets = normal_targets + ["B16"]
            payload = _read_json_path(all_remaining_json)
            expected = {
                "batch_id": "bus_fault_all_remaining_manual_wiring",
                "existing_bus_fault_candidates": ["B39", "B26"],
                "current_candidate_count": 42,
                "old_formal_gate": "35 / 33 / 33",
                "normal_target_buses": normal_targets,
                "special_target_buses": ["B16"],
                "all_new_target_buses": all_targets,
                "num_normal_targets": 36,
                "num_special_targets": 1,
                "num_all_new_targets": 37,
                "excluded_from_wiring": ["B39", "B26"],
                "should_run_smoke_now": False,
                "should_export_labels_now": False,
                "should_train_now": False,
                "gcn_usefulness_audit_now": False,
            }
            for key, value in expected.items():
                if payload.get(key) != value:
                    failures.append(f"All-remaining bus-fault plan must record {key}={value!r}.")
            template_dir = all_remaining_dir / "manual_review_templates"
            for bus in all_targets:
                template_path = template_dir / f"manual_bus_fault_injection_review_template_{bus}.json"
                if not os.path.exists(_fs_path(template_path)):
                    failures.append(f"Missing all-remaining bus-fault template for {bus}.")
                    continue
                template = _read_json_path(template_path)
                if template.get("target_bus") != bus:
                    failures.append(f"{bus} template target_bus mismatch.")
                if template.get("suggested_fault_block_name") != f"Grid/Fault_{bus}_TEMP":
                    failures.append(f"{bus} template has wrong suggested fault block name.")
                for key in [
                    "human_verified_injection_point",
                    "safe_to_run_smoke_recommendation",
                    "simulink_smoke_run",
                    "smoke_success",
                    "candidate_label_exported",
                    "labels_exported",
                    "gcn_trained",
                    "reranker_retrained",
                    "temporary_model_committed",
                    "source_slx_modified",
                    "temporary_slx_committed",
                ]:
                    if template.get(key) is not False:
                        failures.append(f"{bus} template must initialize {key}=false.")
                if bus == "B16":
                    if template.get("special_handling") is not True or not template.get("special_handling_reason"):
                        failures.append("B16 template must be special handling with a nonempty reason.")
                elif template.get("special_handling") is not False:
                    failures.append(f"{bus} template must not be special handling.")
            schema = _read_json_path(all_remaining_schema)
            for required in [
                "batch_id",
                "target_bus",
                "special_handling",
                "temp_model_path",
                "human_verified_injection_point",
                "safe_to_run_smoke_recommendation",
                "simulink_smoke_run",
                "smoke_success",
                "candidate_label_exported",
                "labels_exported",
                "gcn_trained",
                "reranker_retrained",
                "failed_checks",
                "next_action",
            ]:
                if required not in schema.get("required", []):
                    failures.append(f"All-remaining evidence schema missing required field: {required}")
            doc_text = "\n".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in [all_remaining_md, all_remaining_commands, all_remaining_gate, all_remaining_doc]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            for required in [
                "does not run simulink",
                "does not export labels",
                "does not train gcn",
                "does not run a gcn usefulness audit",
                "candidate labels, not formal labels",
                "phasor_rms, not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"All-remaining bus-fault docs missing: {required}")
            for bad in [
                "this round ran simulink",
                "labels were exported",
                "gcn was trained",
                "gcn usefulness audit was run",
                "human verified=true",
                "smoke success=true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in normalized:
                    failures.append(f"All-remaining bus-fault docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read all-remaining bus-fault wiring artifacts: {exc}")

    all_remaining_evidence_dir = all_remaining_dir / "manual_connection_evidence"
    all_remaining_evidence_summary = all_remaining_evidence_dir / "batch_manual_connection_evidence_summary.json"
    all_remaining_ready = all_remaining_evidence_dir / "buses_ready_for_readiness_dry_run.json"
    all_remaining_evidence_doc = ROOT / "docs/ieee39_all_remaining_bus_fault_manual_connection_evidence.md"
    if all_remaining_evidence_summary.exists():
        try:
            normal_targets = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
            all_targets = normal_targets + ["B16"]
            summary = _read_json_path(all_remaining_evidence_summary)
            expected_summary = {
                "batch_id": "bus_fault_all_remaining_manual_wiring",
                "user_declared_all_wiring_complete": True,
                "total_targets": 37,
                "normal_targets": 36,
                "special_targets": 1,
                "existing_completed_bus_faults": ["B39", "B26"],
                "current_candidate_count": 42,
                "old_formal_gate": "35 / 33 / 33",
                "num_temp_models_found": 37,
                "num_fault_blocks_found": 37,
                "num_update_diagram_success": 37,
                "num_automated_evidence_check_passed": 37,
                "num_human_verified_injection_point": 37,
                "num_safe_to_run_smoke_recommendation": 37,
                "buses_blocked": [],
                "b16_special_check_passed": True,
                "b16_old_fault_not_moved": True,
                "simulink_run": False,
                "actual_smoke_run": False,
                "labels_exported": False,
                "candidate_labels_exported": False,
                "gcn_trained": False,
                "reranker_retrained": False,
                "gcn_usefulness_audit_run": False,
                "should_run_smoke_now": False,
                "should_export_labels_now": False,
                "should_train_now": False,
            }
            for key, value in expected_summary.items():
                if summary.get(key) != value:
                    failures.append(f"All-remaining manual evidence summary must record {key}={value!r}.")
            if set(summary.get("buses_ready_for_next_round_readiness", [])) != set(all_targets):
                failures.append("All-remaining manual evidence summary must mark all 37 targets ready for readiness dry-run.")
            ready = _read_json_path(all_remaining_ready)
            if ready.get("ready_count") != 37 or ready.get("blocked_count") != 0:
                failures.append("All-remaining readiness candidate list must record 37 ready and 0 blocked.")
            for bus in all_targets:
                evidence_json = all_remaining_evidence_dir / f"manual_connection_evidence_{bus}.json"
                evidence_md = all_remaining_evidence_dir / f"manual_connection_evidence_{bus}.md"
                if not os.path.exists(_fs_path(evidence_json)) or not os.path.exists(_fs_path(evidence_md)):
                    failures.append(f"Missing all-remaining manual connection evidence for {bus}.")
                    continue
                evidence = _read_json_path(evidence_json)
                for key in [
                    "temp_model_exists",
                    "fault_block_found",
                    "fault_block_name_correct",
                    "update_diagram_attempted",
                    "update_diagram_success",
                    "automated_evidence_check_passed",
                    "human_verified_injection_point",
                    "safe_to_run_smoke_recommendation",
                ]:
                    if evidence.get(key) is not True:
                        failures.append(f"{bus} manual evidence must record {key}=true.")
                for key in [
                    "simulink_smoke_run",
                    "smoke_success",
                    "labels_exported",
                    "candidate_label_exported",
                    "gcn_trained",
                    "reranker_retrained",
                    "source_slx_modified",
                    "temporary_slx_committed",
                ]:
                    if evidence.get(key) is not False:
                        failures.append(f"{bus} manual evidence must record {key}=false.")
                if bus == "B16":
                    if evidence.get("special_handling") is not True or evidence.get("selected_fault_block_path") != "Grid/Fault_B16_TEMP":
                        failures.append("B16 manual evidence must be special handling with Grid/Fault_B16_TEMP.")
                elif evidence.get("special_handling") is not False:
                    failures.append(f"{bus} manual evidence must not be special handling.")
            doc_text = "\n".join(
                [
                    all_remaining_evidence_doc.read_text(encoding="utf-8", errors="ignore"),
                    (all_remaining_evidence_dir / "batch_manual_connection_evidence_summary.md").read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            for required in [
                "does not run simulink simulation",
                "does not run actual smoke",
                "does not export labels",
                "does not train gcn",
                "does not run a gcn usefulness audit",
                "not formal labels",
                "not candidate labels",
                "not smoke success",
                "phasor_rms, not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"All-remaining manual evidence docs missing: {required}")
            for bad in [
                "37 new targets are candidate labels",
                "37 new targets are smoke success",
                "gcn usefulness audit was run",
                "labels_exported=true",
                "candidate_label_exported=true",
                "smoke_success=true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in normalized:
                    failures.append(f"All-remaining manual evidence docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read all-remaining manual evidence artifacts: {exc}")

    all_remaining_readiness_dir = all_remaining_dir / "readiness_dry_run"
    all_remaining_readiness_summary = all_remaining_readiness_dir / "batch_readiness_dry_run_summary.json"
    all_remaining_readiness_manifest = all_remaining_readiness_dir / "batch_actual_smoke_plan_manifest.json"
    all_remaining_readiness_doc = ROOT / "docs/ieee39_all_remaining_bus_fault_batch_readiness_dry_run.md"
    if all_remaining_readiness_summary.exists():
        try:
            normal_targets = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
            all_targets = normal_targets + ["B16"]
            summary = _read_json_path(all_remaining_readiness_summary)
            expected_summary = {
                "batch_id": "bus_fault_all_remaining_manual_wiring",
                "readiness_scope": "dry_run_only",
                "total_targets": 37,
                "normal_targets": 36,
                "special_targets": 1,
                "existing_completed_bus_faults": ["B39", "B26"],
                "current_candidate_count": 42,
                "old_formal_gate": "35 / 33 / 33",
                "num_manual_evidence_passed": 37,
                "num_readiness_dry_run_checked": 37,
                "num_ready_for_next_round_actual_smoke": 37,
                "num_blocked_before_smoke": 0,
                "ready_buses": all_targets,
                "blocked_buses": [],
                "blocked_reasons_by_bus": {},
                "b16_special_handling_preserved": True,
                "b16_old_fault_not_moved": True,
                "simulation_run": False,
                "actual_smoke_run": False,
                "labels_exported": False,
                "candidate_labels_exported": False,
                "gcn_trained": False,
                "reranker_retrained": False,
                "gcn_usefulness_audit_run": False,
                "should_run_actual_smoke_now": False,
                "should_export_labels_now": False,
                "should_train_now": False,
            }
            for key, value in expected_summary.items():
                if summary.get(key) != value:
                    failures.append(f"All-remaining readiness summary must record {key}={value!r}.")
            for bus in all_targets:
                readiness_json = all_remaining_readiness_dir / f"readiness_dry_run_{bus}.json"
                readiness_md = all_remaining_readiness_dir / f"readiness_dry_run_{bus}.md"
                if not os.path.exists(_fs_path(readiness_json)) or not os.path.exists(_fs_path(readiness_md)):
                    failures.append(f"Missing all-remaining readiness dry-run artifact for {bus}.")
                    continue
                record = _read_json_path(readiness_json)
                for key in [
                    "temp_model_exists",
                    "fault_block_found",
                    "fault_block_name_correct",
                    "update_diagram_success",
                    "human_verified_injection_point",
                    "safe_to_run_smoke_recommendation_from_manual_evidence",
                    "ready_for_next_round_actual_smoke",
                ]:
                    if record.get(key) is not True:
                        failures.append(f"{bus} readiness dry-run must record {key}=true.")
                for key in [
                    "actual_smoke_run",
                    "simulation_run",
                    "labels_exported",
                    "candidate_label_exported",
                    "gcn_trained",
                    "reranker_retrained",
                    "gcn_usefulness_audit_run",
                    "source_slx_modified",
                    "temporary_slx_committed",
                ]:
                    if record.get(key) is not False:
                        failures.append(f"{bus} readiness dry-run must record {key}=false.")
                if record.get("readiness_scope") != "dry_run_only":
                    failures.append(f"{bus} readiness dry-run must keep readiness_scope=dry_run_only.")
                if record.get("readiness_status") != "ready_for_next_round_actual_smoke":
                    failures.append(f"{bus} readiness dry-run must be ready for next-round actual smoke.")
                if record.get("selected_fault_block_path") != f"Grid/Fault_{bus}_TEMP":
                    failures.append(f"{bus} readiness dry-run has wrong selected fault block path.")
                if bus == "B16":
                    if record.get("special_handling") is not True:
                        failures.append("B16 readiness dry-run must preserve special_handling=true.")
                elif record.get("special_handling") is not False:
                    failures.append(f"{bus} readiness dry-run must not be special handling.")
                if "smoke_success" in record:
                    failures.append(f"{bus} readiness dry-run must not write smoke_success.")
            manifest = _read_json_path(all_remaining_readiness_manifest)
            if manifest.get("plan_scope") != "next_round_actual_smoke_plan_only":
                failures.append("All-remaining readiness manifest must be next-round plan only.")
            if manifest.get("actual_smoke_run_this_round") is not False:
                failures.append("All-remaining readiness manifest must record actual_smoke_run_this_round=false.")
            if set(manifest.get("ready_buses", [])) != set(all_targets):
                failures.append("All-remaining readiness manifest must include all ready buses.")
            if manifest.get("should_run_smoke_now") is not False or manifest.get("should_export_labels_now") is not False or manifest.get("should_train_now") is not False:
                failures.append("All-remaining readiness manifest must not trigger smoke, labels, or training now.")
            doc_text = "\n".join(
                [
                    all_remaining_readiness_doc.read_text(encoding="utf-8", errors="ignore"),
                    (all_remaining_readiness_dir / "batch_readiness_dry_run_summary.md").read_text(encoding="utf-8", errors="ignore"),
                    (all_remaining_readiness_dir / "batch_actual_smoke_plan_manifest.md").read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            for required in [
                "readiness dry-run",
                "not actual smoke",
                "no simulation was run",
                "does not export labels",
                "does not train gcn",
                "does not run a gcn usefulness audit",
                "not candidate labels",
                "not smoke success",
                "phasor_rms, not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"All-remaining readiness docs missing: {required}")
            for bad in [
                "37 new targets are candidate labels",
                "37 new targets are smoke success",
                "actual smoke succeeded",
                "simulation succeeded",
                "gcn usefulness audit was run",
                "labels_exported=true",
                "candidate_label_exported=true",
                "smoke_success=true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in normalized:
                    failures.append(f"All-remaining readiness docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read all-remaining readiness dry-run artifacts: {exc}")

    all_remaining_smoke_dir = all_remaining_dir / "batch_smoke_outputs"
    all_remaining_smoke_summary = all_remaining_smoke_dir / "batch_actual_smoke_summary.json"
    all_remaining_smoke_quality = all_remaining_smoke_dir / "buses_ready_for_smoke_quality_review.json"
    all_remaining_smoke_doc = ROOT / "docs/ieee39_all_remaining_bus_fault_batch_actual_smoke.md"
    if all_remaining_smoke_summary.exists():
        try:
            normal_targets = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
            all_targets = normal_targets + ["B16"]
            summary = _read_json_path(all_remaining_smoke_summary)
            expected_summary = {
                "batch_id": "bus_fault_all_remaining_manual_wiring",
                "smoke_scope": "actual_temporary_smoke_only",
                "total_targets": 37,
                "num_smoke_attempted": 37,
                "current_candidate_count": 42,
                "old_formal_gate": "35 / 33 / 33",
                "actual_simulink_run": True,
                "dry_run": False,
                "labels_exported": False,
                "candidate_labels_exported": False,
                "gcn_trained": False,
                "reranker_retrained": False,
                "gcn_usefulness_audit_run": False,
                "should_export_labels_now": False,
                "should_train_now": False,
            }
            for key, value in expected_summary.items():
                if summary.get(key) != value:
                    failures.append(f"All-remaining batch smoke summary must record {key}={value!r}.")
            attempted_total = summary.get("num_simulation_success", 0) + summary.get("num_simulation_failed", 0) + summary.get("num_timeout", 0)
            if attempted_total != summary.get("num_smoke_attempted"):
                failures.append("All-remaining batch smoke counts must sum to num_smoke_attempted.")
            if set(summary.get("successful_buses", []) + summary.get("failed_buses", []) + summary.get("timeout_buses", [])) != set(all_targets):
                failures.append("All-remaining batch smoke summary must account for all 37 targets.")
            for bus in all_targets:
                report_json = all_remaining_smoke_dir / f"batch_smoke_{bus}_report.json"
                report_md = all_remaining_smoke_dir / f"batch_smoke_{bus}_report.md"
                report_csv = all_remaining_smoke_dir / f"batch_smoke_{bus}_summary.csv"
                if not os.path.exists(_fs_path(report_json)) or not os.path.exists(_fs_path(report_md)) or not os.path.exists(_fs_path(report_csv)):
                    failures.append(f"Missing all-remaining batch smoke report artifacts for {bus}.")
                    continue
                report = _read_json_path(report_json)
                for key in [
                    "actual_simulink_run",
                    "smoke_executed",
                ]:
                    if report.get(key) is not True:
                        failures.append(f"{bus} batch smoke report must record {key}=true.")
                for key in [
                    "dry_run",
                    "source_slx_modified",
                    "temporary_slx_committed",
                    "labels_exported",
                    "candidate_label_exported",
                    "gcn_trained",
                    "reranker_retrained",
                    "gcn_usefulness_audit_run",
                ]:
                    if report.get(key) is not False:
                        failures.append(f"{bus} batch smoke report must record {key}=false.")
                if report.get("target_bus") != bus or report.get("scenario_id") != f"BF_{bus}_TEMP_SMOKE":
                    failures.append(f"{bus} batch smoke report has wrong target_bus or scenario_id.")
                if report.get("selected_fault_block_path") != f"Grid/Fault_{bus}_TEMP":
                    failures.append(f"{bus} batch smoke report has wrong selected fault block path.")
                if report.get("simulation_success") is True:
                    if report.get("measurement_extraction_status") != "voltage_speed_angle":
                        failures.append(f"{bus} successful batch smoke must have voltage_speed_angle measurements.")
                    if report.get("physical_fault_or_breaker_action_executed") is not True:
                        failures.append(f"{bus} successful batch smoke must record physical_fault_or_breaker_action_executed=true.")
                    if "frequency=generator_speed_proxy" not in str(report.get("signal_source_summary", "")):
                        failures.append(f"{bus} successful batch smoke must use generator_speed_proxy frequency.")
                if bus == "B16" and report.get("special_handling") is not True:
                    failures.append("B16 batch smoke report must preserve special_handling=true.")
            quality = _read_json_path(all_remaining_smoke_quality)
            if quality.get("ready_for_quality_review_buses") != summary.get("successful_buses"):
                failures.append("All-remaining quality-review candidate list must match successful buses.")
            if quality.get("blocked_from_quality_review_buses") != summary.get("failed_buses", []) + summary.get("timeout_buses", []):
                failures.append("All-remaining quality-review blocked list must match failed/timeout buses.")
            for key in ["should_run_quality_review_now", "should_export_labels_now", "should_train_now"]:
                if quality.get(key) is not False:
                    failures.append(f"All-remaining quality-review candidate list must record {key}=false.")
            doc_text = "\n".join(
                [
                    all_remaining_smoke_doc.read_text(encoding="utf-8", errors="ignore"),
                    (all_remaining_smoke_dir / "batch_actual_smoke_summary.md").read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            for required in [
                "actual simulink smoke was run",
                "did not export labels",
                "did not train gcn",
                "did not run a gcn usefulness audit",
                "not candidate labels",
                "temporary smoke evidence",
                "smoke quality review",
                "phasor_rms, not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"All-remaining batch smoke docs missing: {required}")
            for bad in [
                "37 new targets are candidate labels",
                "labels were exported",
                "gcn was trained",
                "gcn usefulness audit was run",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in normalized:
                    failures.append(f"All-remaining batch smoke docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read all-remaining batch smoke artifacts: {exc}")

    all_remaining_quality_dir = all_remaining_dir / "batch_smoke_quality_review"
    all_remaining_quality_summary = all_remaining_quality_dir / "batch_smoke_quality_review_summary.json"
    all_remaining_quality_eligible = all_remaining_quality_dir / "buses_eligible_for_candidate_export.json"
    all_remaining_quality_doc = ROOT / "docs/ieee39_all_remaining_bus_fault_batch_smoke_quality_review.md"
    if all_remaining_quality_summary.exists():
        try:
            normal_targets = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
            all_targets = normal_targets + ["B16"]
            summary = _read_json_path(all_remaining_quality_summary)
            expected_summary = {
                "batch_id": "bus_fault_all_remaining_manual_wiring",
                "quality_review_scope": "smoke_output_quality_only",
                "total_smoke_reports_reviewed": 37,
                "current_candidate_count": 42,
                "old_formal_gate": "35 / 33 / 33",
                "actual_simulink_run_this_round": False,
                "smoke_was_run_in_previous_round": True,
                "labels_exported": False,
                "candidate_labels_exported": False,
                "gcn_trained": False,
                "reranker_retrained": False,
                "gcn_usefulness_audit_run": False,
                "should_export_labels_now": False,
                "should_train_now": False,
            }
            for key, value in expected_summary.items():
                if summary.get(key) != value:
                    failures.append(f"All-remaining smoke quality summary must record {key}={value!r}.")
            if summary.get("num_quality_review_passed", 0) + summary.get("num_quality_review_failed", 0) != 37:
                failures.append("All-remaining smoke quality pass/fail counts must sum to 37.")
            if set(summary.get("quality_review_passed_buses", []) + summary.get("quality_review_failed_buses", [])) != set(all_targets):
                failures.append("All-remaining smoke quality summary must account for all 37 targets.")
            if summary.get("measurement_extraction_status_counts") != {"voltage_speed_angle": 37}:
                failures.append("All-remaining smoke quality summary must preserve voltage_speed_angle count for all buses.")
            if "B1" not in summary.get("unstable_flag_false_buses", []):
                failures.append("All-remaining smoke quality summary must list B1 as unstable_flag=false.")
            if summary.get("special_b16_quality_review_passed") is not True:
                failures.append("B16 smoke quality review must pass when its smoke metrics are valid.")
            for bus in all_targets:
                review_json = all_remaining_quality_dir / f"smoke_quality_review_{bus}.json"
                review_md = all_remaining_quality_dir / f"smoke_quality_review_{bus}.md"
                if not os.path.exists(_fs_path(review_json)) or not os.path.exists(_fs_path(review_md)):
                    failures.append(f"Missing all-remaining smoke quality review artifacts for {bus}.")
                    continue
                review = _read_json_path(review_json)
                if review.get("target_bus") != bus or review.get("scenario_id") != f"BF_{bus}_TEMP_SMOKE":
                    failures.append(f"{bus} smoke quality review has wrong target_bus or scenario_id.")
                if review.get("actual_simulink_run_this_round") is not False or review.get("smoke_was_run_in_previous_round") is not True:
                    failures.append(f"{bus} smoke quality review must be review-only with previous-round smoke.")
                for key in ["labels_exported", "candidate_label_exported", "gcn_trained", "reranker_retrained", "gcn_usefulness_audit_run", "source_slx_modified", "temporary_slx_committed"]:
                    if review.get(key) is not False:
                        failures.append(f"{bus} smoke quality review must record {key}=false.")
                if review.get("selected_fault_block_path") != f"Grid/Fault_{bus}_TEMP":
                    failures.append(f"{bus} smoke quality review has wrong selected fault block path.")
                if review.get("quality_review_passed_for_candidate_export") is True:
                    if review.get("metrics_all_finite") is not True:
                        failures.append(f"{bus} passed smoke quality review without finite metrics.")
                    if review.get("signal_source_has_frequency_proxy") is not True:
                        failures.append(f"{bus} passed smoke quality review without generator_speed_proxy.")
                    if review.get("measurement_extraction_status") != "voltage_speed_angle":
                        failures.append(f"{bus} passed smoke quality review without voltage_speed_angle measurements.")
                if bus == "B16":
                    if review.get("special_handling") is not True or review.get("b16_old_fault_not_moved") is not True:
                        failures.append("B16 smoke quality review must preserve special handling and old-fault boundary.")
            eligible = _read_json_path(all_remaining_quality_eligible)
            if eligible.get("eligible_buses") != summary.get("candidate_export_eligible_buses"):
                failures.append("All-remaining eligible-export list must match quality-passed buses.")
            if eligible.get("blocked_buses") != summary.get("candidate_export_blocked_buses"):
                failures.append("All-remaining eligible-export blocked list must match quality-failed buses.")
            if eligible.get("should_export_labels_now") is not False or eligible.get("should_train_now") is not False:
                failures.append("All-remaining eligible-export list must not trigger immediate export or training.")
            doc_text = "\n".join(
                [
                    all_remaining_quality_doc.read_text(encoding="utf-8", errors="ignore"),
                    (all_remaining_quality_dir / "batch_smoke_quality_review_summary.md").read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            for required in [
                "did not run simulink",
                "did not run actual smoke",
                "did not export labels",
                "did not train gcn",
                "did not retrain the reranker",
                "did not run a gcn usefulness audit",
                "still not candidate labels",
                "candidate-only export",
                "unstable_flag is a compact smoke threshold marker",
                "phasor_rms, not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"All-remaining smoke quality docs missing: {required}")
            for bad in [
                "37 new targets are candidate labels",
                "this round ran simulink",
                "this round ran actual smoke",
                "labels were exported",
                "gcn was trained",
                "gcn usefulness audit was run",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in normalized:
                    failures.append(f"All-remaining smoke quality docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read all-remaining smoke quality review artifacts: {exc}")

    all_remaining_export_dir = all_remaining_dir / "candidate_label_export"
    all_remaining_export_summary = all_remaining_export_dir / "batch_candidate_label_export_summary.json"
    all_remaining_combined = all_remaining_export_dir / "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv"
    all_remaining_export_doc = ROOT / "docs/ieee39_all_remaining_bus_fault_candidate_label_export.md"
    if all_remaining_export_summary.exists():
        try:
            import pandas as pd

            normal_targets = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
            new_targets = normal_targets + ["B16"]
            all_buses = {f"B{i}" for i in range(1, 40)}
            summary = _read_json_path(all_remaining_export_summary)
            expected_summary = {
                "export_scope": "candidate_only",
                "previous_candidate_count": 42,
                "num_new_all_remaining_bus_fault_candidates": 37,
                "num_v2_plus_all_bus_fault_candidate_labels": 79,
                "num_total_bus_fault_candidates": 39,
                "all_ieee39_buses_have_bus_fault_candidate": True,
                "formal_label_gate_changed": False,
                "old_formal_gate": "35 / 33 / 33",
                "b39_b26_status": "existing_candidate_labels_not_formal",
                "l12_excluded": True,
                "nf06_provenance_warning_preserved": True,
                "labels_exported_this_round": "candidate_only",
                "gcn_trained": False,
                "reranker_retrained": False,
                "gcn_usefulness_audit_run": False,
                "should_train_now": False,
            }
            for key, value in expected_summary.items():
                if summary.get(key) != value:
                    failures.append(f"All-remaining candidate export summary must record {key}={value!r}.")
            if summary.get("unstable_flag_false_buses") != ["B1"]:
                failures.append("All-remaining candidate export summary must preserve B1 as unstable_flag=false.")
            if set(summary.get("new_candidate_buses", [])) != set(new_targets):
                failures.append("All-remaining candidate export summary must list the 37 new candidate buses.")
            combined = pd.read_csv(_fs_path(all_remaining_combined))
            if len(combined) != 79:
                failures.append("All-remaining combined candidate dataset must contain 79 rows.")
            if "bus_fault_label" in combined.columns:
                bus_fault = combined[combined["bus_fault_label"].map(lambda value: str(value).strip().lower() in {"1", "true", "yes"})]
                if len(bus_fault) != 39:
                    failures.append("All-remaining combined dataset must contain 39 bus-fault candidates.")
                if set(bus_fault.get("target_bus", pd.Series(dtype=str)).dropna().astype(str)) != all_buses:
                    failures.append("All-remaining combined dataset must cover B1-B39 bus-fault candidates.")
                if not bus_fault.get("line_id", pd.Series(dtype=str)).astype(str).eq("NO_LINE").all():
                    failures.append("All-remaining bus-fault candidates must use line_id=NO_LINE.")
                if not bus_fault.get("candidate_not_formal_label", pd.Series(dtype=str)).map(lambda value: str(value).strip().lower() in {"1", "true", "yes"}).all():
                    failures.append("All-remaining bus-fault candidates must remain candidate_not_formal_label=true.")
            else:
                failures.append("All-remaining combined dataset missing bus_fault_label column.")
            for bus in new_targets:
                candidate_json = all_remaining_export_dir / f"candidate_label_{bus}.json"
                candidate_csv = all_remaining_export_dir / f"candidate_label_{bus}.csv"
                if not os.path.exists(_fs_path(candidate_json)) or not os.path.exists(_fs_path(candidate_csv)):
                    failures.append(f"Missing all-remaining candidate label artifacts for {bus}.")
                    continue
                candidate = _read_json_path(candidate_json)
                if candidate.get("scenario_id") != f"BF_{bus}_TEMP_SMOKE" or candidate.get("target_bus") != bus:
                    failures.append(f"{bus} candidate label has wrong scenario_id or target_bus.")
                if candidate.get("line_id") != "NO_LINE" or candidate.get("target_bus_or_component") != bus:
                    failures.append(f"{bus} candidate label must use NO_LINE and filled target_bus_or_component.")
                if candidate.get("selected_fault_block_path") != f"Grid/Fault_{bus}_TEMP":
                    failures.append(f"{bus} candidate label has wrong selected fault block path.")
                for key in ["bus_fault_label", "temporary_smoke_candidate", "candidate_not_formal_label", "training_ready_label_candidate", "training_ready_label_v2"]:
                    if str(candidate.get(key)).strip().lower() not in {"1", "true", "yes"}:
                        failures.append(f"{bus} candidate label must record {key}=true.")
                for key in ["formal_line_trip_label", "handwired_line_trip_label", "gcn_trained", "reranker_retrained", "gcn_usefulness_audit_run"]:
                    if str(candidate.get(key)).strip().lower() in {"1", "true", "yes"}:
                        failures.append(f"{bus} candidate label must record {key}=false.")
                if "frequency=generator_speed_proxy" not in str(candidate.get("signal_source_summary", "")):
                    failures.append(f"{bus} candidate label must preserve generator_speed_proxy.")
            readiness = _read_json_path(all_remaining_export_dir / "v2_plus_all_bus_fault_training_readiness.json")
            if readiness.get("candidate_count") != 79 or readiness.get("num_bus_fault_candidates") != 39:
                failures.append("All-remaining training readiness must record 79 candidates and 39 bus-fault candidates.")
            if readiness.get("should_train_now") is not False:
                failures.append("All-remaining training readiness must keep should_train_now=false.")
            coverage = _read_json_path(all_remaining_export_dir / "all_bus_fault_candidate_coverage_report.json")
            if coverage.get("missing_buses") != [] or coverage.get("num_covered_buses") != 39:
                failures.append("All-remaining coverage report must cover all 39 buses.")
            doc_text = "\n".join(
                [
                    all_remaining_export_doc.read_text(encoding="utf-8", errors="ignore"),
                    (all_remaining_export_dir / "batch_candidate_label_export_summary.md").read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            for required in [
                "candidate-only export",
                "did not run simulink",
                "did not run actual smoke",
                "did not train gcn",
                "did not retrain the reranker",
                "did not run a gcn usefulness audit",
                "candidate_not_formal_label",
                "not formal labels",
                "phasor_rms, not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
                "target-feature leakage",
                "no-training composition review",
            ]:
                if required not in normalized:
                    failures.append(f"All-remaining candidate export docs missing: {required}")
            for bad in [
                "this round ran simulink",
                "this round ran actual smoke",
                "gcn was trained",
                "gcn usefulness audit was run",
                "bus-fault labels are formal labels",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in normalized:
                    failures.append(f"All-remaining candidate export docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read all-remaining candidate export artifacts: {exc}")

    all_bus_composition_dir = all_remaining_dir / "no_training_composition_review"
    all_bus_composition_json = all_bus_composition_dir / "v2_plus_all_bus_fault_composition_review.json"
    all_bus_composition_doc = ROOT / "docs/ieee39_v2_plus_all_bus_fault_no_training_composition_review.md"
    if all_bus_composition_json.exists():
        try:
            review = _read_json_path(all_bus_composition_json)
            expected = {
                "review_scope": "no_training_composition_review",
                "candidate_dataset": "v2_plus_all_bus_fault_candidates",
                "total_candidate_rows": 79,
                "expected_candidate_rows": 79,
                "row_count_check_passed": True,
                "num_total_bus_fault_candidates": 39,
                "expected_total_bus_fault_candidates": 39,
                "all_ieee39_buses_have_bus_fault_candidate": True,
                "old_formal_gate": "35 / 33 / 33",
                "formal_label_gate_changed": False,
                "l12_excluded": True,
                "nf06_provenance_warning_preserved": True,
                "composition_review_passed": True,
                "compact_dynamic_measurement_features_are_post_fault": True,
                "target_feature_leakage_risk_if_used_as_inputs": True,
                "simulink_run": False,
                "actual_smoke_run": False,
                "labels_exported": False,
                "gcn_trained": False,
                "reranker_retrained": False,
                "gcn_usefulness_audit_run": False,
                "preview_training_run": False,
                "should_train_now": False,
            }
            for key, value in expected.items():
                if review.get(key) != value:
                    failures.append(f"V2-plus-all-bus-fault composition review must record {key}={value!r}.")
            if review.get("missing_bus_fault_buses") != []:
                failures.append("V2-plus-all-bus-fault composition review must have no missing bus-fault buses.")
            if review.get("scenario_id_duplicates") != [] or review.get("label_id_v2_duplicates") != []:
                failures.append("V2-plus-all-bus-fault composition review must have no duplicate scenario or label IDs.")
            if review.get("dynamic_stress_score_nonfinite_rows") != []:
                failures.append("V2-plus-all-bus-fault composition review must have no nonfinite bus-fault dynamic stress scores.")
            if review.get("unstable_flag_false_buses") != ["B1"]:
                failures.append("V2-plus-all-bus-fault composition review must preserve B1 as unstable_flag=false.")
            for key in [
                "every_bus_fault_row_has_line_id_NO_LINE",
                "every_bus_fault_row_has_target_bus_filled",
                "every_bus_fault_row_has_target_bus_or_component_filled",
                "every_bus_fault_row_candidate_not_formal_label_true",
                "every_bus_fault_row_formal_line_trip_label_false",
                "every_bus_fault_row_bus_fault_label_true",
                "every_bus_fault_row_temporary_smoke_candidate_true",
                "every_bus_fault_row_quality_review_passed_true",
                "every_bus_fault_row_signal_source_contains_frequency_proxy",
                "every_bus_fault_row_phasor_rms_not_emt_true",
                "every_bus_fault_row_generator_speed_proxy_not_direct_frequency_true",
                "every_bus_fault_row_temporary_bus_fault_not_engineering_grade_protection_true",
            ]:
                if review.get(key) is not True:
                    failures.append(f"V2-plus-all-bus-fault composition review must pass {key}.")
            coverage = _read_json_path(all_bus_composition_dir / "all_bus_fault_coverage_check.json")
            schema = _read_json_path(all_bus_composition_dir / "schema_and_duplicate_check.json")
            leakage = _read_json_path(all_bus_composition_dir / "leakage_risk_and_training_boundary_check.json")
            if coverage.get("missing_bus_fault_buses") != [] or coverage.get("num_covered_buses") != 39:
                failures.append("V2-plus-all-bus-fault coverage check must cover all 39 buses.")
            if schema.get("scenario_id_duplicates") != [] or schema.get("label_id_v2_duplicates") != []:
                failures.append("V2-plus-all-bus-fault schema check must have no duplicate IDs.")
            if leakage.get("target_feature_leakage_risk_if_used_as_inputs") is not True or leakage.get("should_train_now") is not False:
                failures.append("V2-plus-all-bus-fault leakage boundary check must preserve leakage warning and no-training boundary.")
            doc_text = "\n".join(
                [
                    all_bus_composition_doc.read_text(encoding="utf-8", errors="ignore"),
                    (all_bus_composition_dir / "v2_plus_all_bus_fault_composition_review.md").read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            for required in [
                "no-training composition review",
                "did not run simulink",
                "did not run actual smoke",
                "did not export labels",
                "did not train gcn",
                "did not retrain the reranker",
                "did not run a gcn usefulness audit",
                "candidate_not_formal_label",
                "not formal labels",
                "phasor_rms, not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
                "target-feature leakage",
                "preview/no-leakage comparison",
            ]:
                if required not in normalized:
                    failures.append(f"V2-plus-all-bus-fault composition docs missing: {required}")
            for bad in [
                "this round ran simulink",
                "this round export labels",
                "gcn was trained",
                "gcn usefulness audit was run",
                "bus-fault labels are formal labels",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in normalized:
                    failures.append(f"V2-plus-all-bus-fault composition docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read v2-plus-all-bus-fault composition artifacts: {exc}")

    all_bus_preview_dir = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview"
    all_bus_preview_json = all_bus_preview_dir / "v2_plus_all_bus_fault_preview_comparison.json"
    all_bus_preview_md = all_bus_preview_dir / "v2_plus_all_bus_fault_preview_comparison.md"
    all_bus_preview_doc = ROOT / "docs/ieee39_v2_plus_all_bus_fault_preview_no_leakage_comparison.md"
    if all_bus_preview_json.exists() and all_bus_preview_md.exists() and all_bus_preview_doc.exists():
        try:
            preview = _read_json_path(all_bus_preview_json)
            expected = {
                "preview_only": True,
                "final_performance_conclusion": False,
                "candidate_dataset": "v2_plus_all_bus_fault_candidates",
                "total_candidate_rows": 79,
                "num_total_bus_fault_candidates": 39,
                "all_ieee39_buses_have_bus_fault_candidate": True,
                "old_formal_gate": "35 / 33 / 33",
                "l12_excluded": True,
                "nf06_provenance_warning_preserved": True,
                "simulink_run": False,
                "actual_smoke_run": False,
                "labels_exported": False,
                "gcn_trained": False,
                "formal_reranker_retrained": False,
                "gcn_usefulness_audit_run": False,
                "should_train_now": False,
                "compact_dynamic_measurement_features_are_post_fault": True,
                "target_feature_leakage_risk_if_used_as_inputs": True,
                "include_all_is_leaky_upper_bound": True,
                "no_dynamic_measurement_feature_set_required_for_future_audit": True,
            }
            for key, value in expected.items():
                if preview.get(key) != value:
                    failures.append(f"All-bus-fault preview comparison must record {key}={value!r}.")
            if preview.get("unstable_flag_false_buses") != ["B1"]:
                failures.append("All-bus-fault preview comparison must preserve unstable_flag_false_buses=['B1'].")
            for key in [
                "include_all_79_rmse",
                "no_dynamic_measurement_rmse",
                "label_family_holdout_rmse",
                "bus_fault_holdout_rmse",
                "leave_one_bus_fault_out_rmse",
                "no_dynamic_measurement_leave_one_bus_fault_out_rmse",
                "b1_true_dynamic_stress_score",
                "b1_predicted_dynamic_stress_score",
                "b1_absolute_error",
                "b1_true_unstable_flag",
                "b1_unstable_probability",
                "worst_10_lobo_buses_by_abs_error",
                "recommended_next_step",
            ]:
                if preview.get(key) in (None, ""):
                    failures.append(f"All-bus-fault preview comparison missing {key}.")
            if len(preview.get("worst_10_lobo_buses_by_abs_error", [])) != 10:
                failures.append("All-bus-fault preview comparison must store 10 worst LOO buses.")
            for mode in [
                "include_all_79_candidates",
                "no_dynamic_measurement_features",
                "label_family_holdout",
                "bus_fault_holdout",
                "leave_one_bus_fault_out",
                "no_dynamic_measurement_leave_one_bus_fault_out",
                "existing_vs_new_bus_fault_check",
            ]:
                metrics_path = all_bus_preview_dir / mode / "preview_training_metrics.json"
                metrics = _read_json_path(metrics_path)
                for key, value in {
                    "preview_only": True,
                    "final_performance_conclusion": False,
                    "simulink_run": False,
                    "actual_smoke_run": False,
                    "labels_exported": False,
                    "gcn_trained": False,
                    "formal_reranker_retrained": False,
                    "gcn_usefulness_audit_run": False,
                    "should_train_now": False,
                }.items():
                    if metrics.get(key) != value:
                        failures.append(f"All-bus-fault preview mode {mode} must record {key}={value!r}.")
            leave_one = _read_json_path(all_bus_preview_dir / "leave_one_bus_fault_out" / "preview_training_metrics.json")
            no_dyn_leave_one = _read_json_path(
                all_bus_preview_dir / "no_dynamic_measurement_leave_one_bus_fault_out" / "preview_training_metrics.json"
            )
            bus_holdout = _read_json_path(all_bus_preview_dir / "bus_fault_holdout" / "preview_training_metrics.json")
            existing_vs_new = _read_json_path(
                all_bus_preview_dir / "existing_vs_new_bus_fault_check" / "preview_training_metrics.json"
            )
            if len(leave_one.get("per_bus_predictions", [])) != 39:
                failures.append("All-bus-fault leave_one_bus_fault_out must contain 39 per-bus predictions.")
            if len(no_dyn_leave_one.get("per_bus_predictions", [])) != 39:
                failures.append("All-bus-fault no-dynamic leave-one-bus-fault-out must contain 39 per-bus predictions.")
            if len(bus_holdout.get("per_bus_predictions", [])) != 39:
                failures.append("All-bus-fault bus_fault_holdout must contain 39 per-bus predictions.")
            if existing_vs_new.get("num_existing_bus_fault_candidates") != 2 or existing_vs_new.get("num_new_bus_fault_candidates") != 37:
                failures.append("All-bus-fault existing_vs_new_bus_fault_check must keep 2 existing and 37 new bus-fault candidates.")
            doc_text = "\n".join(
                [
                    all_bus_preview_doc.read_text(encoding="utf-8", errors="ignore"),
                    all_bus_preview_md.read_text(encoding="utf-8", errors="ignore"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            current_text = "\n".join(
                [
                    all_bus_preview_doc.read_text(encoding="utf-8", errors="ignore"),
                    all_bus_preview_md.read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            current_normalized = " ".join(current_text.replace("`", "").split())
            for required in [
                "preview/no-leakage comparison",
                "did not run simulink",
                "did not run actual smoke",
                "did not export labels",
                "did not train gcn",
                "did not retrain the formal reranker",
                "did not run a gcn usefulness audit",
                "leaky upper-bound",
                "candidate labels, not formal labels",
                "temporary smoke candidates",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
                "cannot directly prove gcn useful or not useful",
            ]:
                if required not in normalized:
                    failures.append(f"All-bus-fault preview docs missing: {required}")
            for bad in [
                "this round ran simulink",
                "this round export labels",
                "gcn was trained",
                "gcn usefulness audit was run",
                "final performance conclusion is true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in current_normalized:
                    failures.append(f"All-bus-fault preview docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read v2-plus-all-bus-fault preview artifacts: {exc}")

    audit_plan_dir = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan"
    audit_plan_json = audit_plan_dir / "gcn_usefulness_audit_plan.json"
    audit_plan_md = audit_plan_dir / "gcn_usefulness_audit_plan.md"
    audit_doc = ROOT / "docs/ieee39_gcn_usefulness_audit_plan.md"
    if audit_plan_json.exists() and audit_plan_md.exists() and audit_doc.exists():
        try:
            plan = _read_json_path(audit_plan_json)
            expected = {
                "audit_scope": "plan_only",
                "audit_execution_this_round": False,
                "gcn_trained_this_round": False,
                "formal_gcn_training": False,
                "reranker_retrained": False,
                "simulink_run": False,
                "labels_exported": False,
                "candidate_dataset": "v2_plus_all_bus_fault_candidates",
                "total_candidate_rows": 79,
                "num_total_bus_fault_candidates": 39,
                "all_ieee39_buses_have_bus_fault_candidate": True,
                "old_formal_gate": "35 / 33 / 33",
                "l12_excluded": True,
                "nf06_provenance_warning_preserved": True,
                "unstable_flag_false_buses": ["B1"],
                "leakage_risk_confirmed_by_preview": True,
                "include_all_is_forbidden_for_gcn_audit": True,
                "no_dynamic_measurement_features_required": True,
                "recommended_audit_type": "strict_no_leakage_gcn_usefulness_audit",
                "should_run_audit_now": False,
                "should_train_now": False,
                "dry_run": True,
            }
            for key, value in expected.items():
                if plan.get(key) != value:
                    failures.append(f"GCN usefulness audit plan must record {key}={value!r}.")
            policy = _read_json_path(audit_plan_dir / "no_leakage_feature_policy.json")
            split = _read_json_path(audit_plan_dir / "strict_holdout_split_manifest.json")
            baseline = _read_json_path(audit_plan_dir / "baseline_comparison_plan.json")
            checklist = _read_json_path(audit_plan_dir / "gcn_audit_execution_checklist.json")
            if policy.get("feature_policy_passed") is not True:
                failures.append("GCN usefulness audit feature policy must pass.")
            for feature in [
                "min_voltage_pu",
                "max_frequency_hz",
                "max_speed_deviation",
                "max_rotor_angle_separation_deg",
                "dynamic_stress_score",
                "unstable_flag",
            ]:
                if feature not in policy.get("forbidden_post_fault_dynamic_measurement_features", []) and feature not in policy.get("forbidden_label_derived_features", []):
                    failures.append(f"GCN usefulness audit feature policy missing forbidden feature {feature}.")
            for split_name in [
                "bus_fault_holdout",
                "leave_one_bus_fault_out",
                "no_dynamic_measurement_leave_one_bus_fault_out",
                "nf06_provenance_sensitivity",
            ]:
                if split_name not in split.get("splits", {}):
                    failures.append(f"GCN usefulness audit split manifest missing {split_name}.")
            if checklist.get("should_train_now") is not False:
                failures.append("GCN usefulness audit execution checklist must keep should_train_now=false.")
            if checklist.get("failed_checks") != []:
                failures.append("GCN usefulness audit execution checklist must have empty failed_checks.")
            if len(baseline.get("baseline_models", [])) < 5:
                failures.append("GCN usefulness audit baseline plan must contain enough baselines.")
            doc_text = "\n".join(
                [
                    audit_doc.read_text(encoding="utf-8", errors="ignore"),
                    audit_plan_md.read_text(encoding="utf-8", errors="ignore"),
                    (audit_plan_dir / "no_leakage_feature_policy.md").read_text(encoding="utf-8", errors="ignore"),
                    (audit_plan_dir / "strict_holdout_split_manifest.md").read_text(encoding="utf-8", errors="ignore"),
                    (audit_plan_dir / "baseline_comparison_plan.md").read_text(encoding="utf-8", errors="ignore"),
                    (audit_plan_dir / "gcn_audit_execution_checklist.md").read_text(encoding="utf-8", errors="ignore"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            current_text = "\n".join(
                [
                    audit_doc.read_text(encoding="utf-8", errors="ignore"),
                    audit_plan_md.read_text(encoding="utf-8", errors="ignore"),
                    (audit_plan_dir / "no_leakage_feature_policy.md").read_text(encoding="utf-8", errors="ignore"),
                    (audit_plan_dir / "strict_holdout_split_manifest.md").read_text(encoding="utf-8", errors="ignore"),
                    (audit_plan_dir / "baseline_comparison_plan.md").read_text(encoding="utf-8", errors="ignore"),
                    (audit_plan_dir / "gcn_audit_execution_checklist.md").read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            current_normalized = " ".join(current_text.replace("`", "").split())
            for required in [
                "only prepares the gcn usefulness audit plan",
                "it did not train gcn",
                "it did not run the gcn usefulness audit",
                "it did not run simulink",
                "it did not export labels",
                "it did not retrain the reranker",
                "leaky upper-bound",
                "no-dynamic-measurement feature set",
                "bus_fault_holdout",
                "leave_one_bus_fault_out",
                "b1",
                "nf06",
                "l12 stays excluded",
                "candidate_not_formal_label",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"GCN usefulness audit plan docs missing: {required}")
            for bad in [
                "gcn usefulness audit was run",
                "gcn was trained",
                "final gcn conclusion",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in current_normalized:
                    failures.append(f"GCN usefulness audit plan docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read GCN usefulness audit plan artifacts: {exc}")

    dry_run_dir = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run"
    dry_run_json = dry_run_dir / "gcn_audit_dry_run_validator_summary.json"
    dry_run_md = dry_run_dir / "gcn_audit_dry_run_validator_summary.md"
    dry_run_csv = dry_run_dir / "gcn_audit_dry_run_validator_summary.csv"
    dry_run_manifest_json = dry_run_dir / "proposed_no_leakage_gcn_inputs_manifest.json"
    dry_run_manifest_md = dry_run_dir / "proposed_no_leakage_gcn_inputs_manifest.md"
    dry_run_draft_json = dry_run_dir / "formal_gcn_audit_execution_draft.json"
    dry_run_draft_md = dry_run_dir / "formal_gcn_audit_execution_draft.md"
    dry_run_doc = ROOT / "docs/ieee39_gcn_usefulness_audit_dry_run_validator.md"
    if all(
        path.exists()
        for path in [
            dry_run_json,
            dry_run_md,
            dry_run_csv,
            dry_run_manifest_json,
            dry_run_manifest_md,
            dry_run_draft_json,
            dry_run_draft_md,
            dry_run_doc,
        ]
    ):
        try:
            dry_run = _read_json_path(dry_run_json)
            manifest = _read_json_path(dry_run_manifest_json)
            draft = _read_json_path(dry_run_draft_json)
            expected = {
                "validator_scope": "dry_run_only",
                "audit_execution_this_round": False,
                "gcn_trained_this_round": False,
                "formal_gcn_training": False,
                "reranker_retrained": False,
                "simulink_run": False,
                "labels_exported": False,
                "model_saved": False,
                "total_candidate_rows": 79,
                "num_total_bus_fault_candidates": 39,
                "all_ieee39_buses_have_bus_fault_candidate": True,
                "forbidden_features_detected_in_inputs": [],
                "forbidden_features_absent_from_gcn_inputs": True,
                "target_bus_memorization_risk_flagged": True,
                "strict_holdouts_complete": True,
                "baseline_comparison_complete": True,
                "b1_special_tracking_enabled": True,
                "nf06_sensitivity_enabled": True,
                "l12_exclusion_check_enabled": True,
                "dry_run_validator_passed": True,
                "should_run_formal_gcn_audit_now": False,
                "should_train_gcn_now": False,
            }
            for key, value in expected.items():
                if dry_run.get(key) != value:
                    failures.append(f"GCN dry-run validator must record {key}={value!r}.")
            for forbidden in [
                "dynamic_stress_score",
                "unstable_flag",
                "min_voltage_pu",
                "max_frequency_hz",
                "max_speed_deviation",
                "max_rotor_angle_separation_deg",
            ]:
                if forbidden in manifest.get("proposed_no_leakage_gcn_input_columns", []):
                    failures.append(f"GCN dry-run proposed inputs must exclude {forbidden}.")
            if draft.get("draft_scope") != "execution_draft_only" or draft.get("execute_this_round") is not False:
                failures.append("GCN dry-run execution draft must stay execution_draft_only with execute_this_round=false.")
            doc_text = "\n".join(
                [
                    dry_run_md.read_text(encoding="utf-8", errors="ignore"),
                    dry_run_manifest_md.read_text(encoding="utf-8", errors="ignore"),
                    dry_run_draft_md.read_text(encoding="utf-8", errors="ignore"),
                    dry_run_doc.read_text(encoding="utf-8", errors="ignore"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            current_text = "\n".join(
                [
                    dry_run_md.read_text(encoding="utf-8", errors="ignore"),
                    dry_run_manifest_md.read_text(encoding="utf-8", errors="ignore"),
                    dry_run_draft_md.read_text(encoding="utf-8", errors="ignore"),
                    dry_run_doc.read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            current_normalized = " ".join(current_text.replace("`", "").split())
            for required in [
                "this round is the ieee39 gcn audit dry-run validator",
                "it did not train gcn",
                "it did not run the formal gcn usefulness audit",
                "it did not run simulink",
                "it did not export labels",
                "it did not retrain the reranker",
                "strict holdouts",
                "baseline comparison",
                "b1",
                "nf06",
                "l12",
                "target_bus",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"GCN dry-run validator docs missing: {required}")
            for bad in [
                "gcn was trained",
                "formal gcn audit was run",
                "final gcn conclusion",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in current_normalized:
                    failures.append(f"GCN dry-run validator docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read GCN dry-run validator artifacts: {exc}")

    audit_exec_dir = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_execution"
    audit_exec_json = audit_exec_dir / "gcn_usefulness_audit_execution_summary.json"
    audit_exec_md = audit_exec_dir / "gcn_usefulness_audit_execution_summary.md"
    audit_exec_csv = audit_exec_dir / "gcn_usefulness_audit_execution_summary.csv"
    audit_exec_doc = ROOT / "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md"
    audit_forbidden_json = audit_exec_dir / "forbidden_feature_audit_report.json"
    audit_compare_json = audit_exec_dir / "baseline_vs_gcn_comparison.json"
    audit_b1_json = audit_exec_dir / "b1_special_tracking_report.json"
    audit_nf06_json = audit_exec_dir / "nf06_sensitivity_report.json"
    audit_l12_json = audit_exec_dir / "l12_exclusion_confirmation.json"
    if all(
        path.exists()
        for path in [
            audit_exec_json,
            audit_exec_md,
            audit_exec_csv,
            audit_exec_doc,
            audit_forbidden_json,
            audit_compare_json,
            audit_b1_json,
            audit_nf06_json,
            audit_l12_json,
        ]
    ):
        try:
            summary = _read_json_path(audit_exec_json)
            forbidden = _read_json_path(audit_forbidden_json)
            comparison = _read_json_path(audit_compare_json)
            b1 = _read_json_path(audit_b1_json)
            nf06 = _read_json_path(audit_nf06_json)
            l12 = _read_json_path(audit_l12_json)
            expected = {
                "audit_scope": "formal_gcn_usefulness_audit_execution",
                "audit_only": True,
                "production_model_saved": False,
                "simulink_run": False,
                "actual_smoke_run": False,
                "labels_exported": False,
                "reranker_retrained": False,
                "rl_mitigation_touched": False,
                "total_candidate_rows": 79,
                "num_total_bus_fault_candidates": 39,
                "no_leakage_feature_policy_passed": True,
                "b1_special_tracking_enabled": True,
                "nf06_provenance_warning_preserved": True,
                "l12_excluded": True,
                "final_engineering_conclusion": False,
                "should_retrain_reranker_now": False,
                "should_deploy_model": False,
                "baseline_comparison_executed": True,
            }
            for key, value in expected.items():
                if summary.get(key) != value:
                    failures.append(f"GCN audit execution summary must record {key}={value!r}.")
            for split_name in [
                "bus_fault_holdout",
                "leave_one_bus_fault_out",
                "no_dynamic_measurement_leave_one_bus_fault_out",
            ]:
                if split_name not in summary.get("strict_holdouts_executed", []):
                    failures.append(f"GCN audit execution summary must include strict holdout {split_name}.")
            if forbidden.get("forbidden_features_detected_in_inputs") != []:
                failures.append("GCN audit execution forbidden_feature report must keep forbidden_features_detected_in_inputs=[].")
            if comparison.get("bus_fault_holdout", {}).get("best_baseline_name") is None:
                failures.append("GCN audit execution comparison must record bus_fault_holdout best baseline.")
            if b1.get("target_bus") != "B1":
                failures.append("GCN audit execution B1 report must keep target_bus=B1.")
            if l12.get("l12_excluded") is not True:
                failures.append("GCN audit execution must confirm L12 excluded.")
            if "include_NF06" not in nf06 or "exclude_NF06" not in nf06:
                failures.append("GCN audit execution NF06 report must include include/exclude variants.")
            doc_text = "\n".join(
                [
                    audit_exec_md.read_text(encoding="utf-8", errors="ignore"),
                    audit_exec_doc.read_text(encoding="utf-8", errors="ignore"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                ]
            ).lower()
            normalized = " ".join(doc_text.replace("`", "").split())
            current_text = "\n".join(
                [
                    audit_exec_md.read_text(encoding="utf-8", errors="ignore"),
                    audit_exec_doc.read_text(encoding="utf-8", errors="ignore"),
                ]
            ).lower()
            current_normalized = " ".join(current_text.replace("`", "").split())
            for required in [
                "formal gcn usefulness audit execution",
                "audit-only",
                "did not run simulink",
                "did not export labels",
                "did not retrain the reranker",
                "did not modify rl mitigation",
                "no-leakage features",
                "target_bus memorization risk",
                "b1",
                "nf06",
                "l12",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
            ]:
                if required not in normalized:
                    failures.append(f"GCN audit execution docs missing: {required}")
            for bad in [
                "final gcn conclusion",
                "production model saved",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in current_normalized:
                    failures.append(f"GCN audit execution docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read GCN audit execution artifacts: {exc}")

    diagnosis_dir = ROOT / "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis"
    diagnosis_json = diagnosis_dir / "gcn_audit_evidence_diagnosis_summary.json"
    diagnosis_md = diagnosis_dir / "gcn_audit_evidence_diagnosis_summary.md"
    diagnosis_csv = diagnosis_dir / "gcn_audit_evidence_diagnosis_summary.csv"
    diagnosis_doc = ROOT / "docs/ieee39_gcn_audit_evidence_diagnosis.md"
    diagnosis_gap = diagnosis_dir / "gcn_vs_baseline_gap_analysis.json"
    diagnosis_b1 = diagnosis_dir / "b1_and_classification_diagnosis.json"
    diagnosis_nf06 = diagnosis_dir / "nf06_sensitivity_diagnosis.json"
    diagnosis_graph = diagnosis_dir / "graph_construction_diagnosis.json"
    diagnosis_plan = diagnosis_dir / "next_gcn_improvement_plan.json"
    diagnosis_required = [
        diagnosis_json,
        diagnosis_md,
        diagnosis_csv,
        diagnosis_doc,
        diagnosis_gap,
        diagnosis_dir / "gcn_vs_baseline_gap_analysis.md",
        diagnosis_b1,
        diagnosis_dir / "b1_and_classification_diagnosis.md",
        diagnosis_nf06,
        diagnosis_dir / "nf06_sensitivity_diagnosis.md",
        diagnosis_graph,
        diagnosis_dir / "graph_construction_diagnosis.md",
        diagnosis_plan,
        diagnosis_dir / "next_gcn_improvement_plan.md",
    ]
    existing_diagnosis_required = [path for path in diagnosis_required if path.exists()]
    if existing_diagnosis_required:
        missing_diagnosis_required = [path for path in diagnosis_required if not path.exists()]
        if missing_diagnosis_required:
            failures.append(
                "GCN audit evidence diagnosis artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_diagnosis_required)
            )
        try:
            payload = _read_json_path(diagnosis_json)
            gap = _read_json_path(diagnosis_gap)
            b1_diag = _read_json_path(diagnosis_b1)
            nf06_diag = _read_json_path(diagnosis_nf06)
            graph_diag = _read_json_path(diagnosis_graph)
            plan_diag = _read_json_path(diagnosis_plan)
            for key, expected in [
                ("diagnosis_scope", "gcn_audit_evidence_diagnosis"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("final_engineering_conclusion", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if payload.get(key) != expected:
                    failures.append(f"GCN audit evidence diagnosis must set {key}={expected!r}.")
            if payload.get("forbidden_features_detected_in_inputs") != []:
                failures.append("GCN audit evidence diagnosis must keep forbidden_features_detected_in_inputs=[].")
            if gap.get("bus_fault_holdout_gcn_rmse", 0) <= gap.get("bus_fault_holdout_best_baseline_rmse", 0):
                failures.append("GCN audit evidence diagnosis must preserve bus_fault_holdout GCN > baseline RMSE.")
            if gap.get("lobo_gcn_rmse", 0) <= gap.get("lobo_best_baseline_rmse", 0):
                failures.append("GCN audit evidence diagnosis must preserve LOBO GCN > baseline RMSE.")
            if b1_diag.get("gcn_unstable_probability") != 1.0:
                failures.append("B1 diagnosis must preserve gcn_unstable_probability=1.0.")
            if nf06_diag.get("nf06_changes_audit_conclusion") is not False:
                failures.append("NF06 diagnosis must state that NF06 does not change the conclusion.")
            if "message passing" not in str(graph_diag.get("message_passing_usage", "")).lower():
                failures.append("Graph construction diagnosis must include message passing usage.")
            if plan_diag.get("training_triggered") is not False:
                failures.append("Next GCN improvement plan must not trigger training.")
            diagnosis_text = "\n".join(
                [
                    _read_text("docs/ieee39_gcn_audit_evidence_diagnosis.md"),
                    _read_text("results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/gcn_audit_evidence_diagnosis_summary.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                ]
            ).lower()
            normalized = " ".join(diagnosis_text.replace("`", "").split())
            for required in [
                "evidence diagnosis only",
                "does not train gcn",
                "does not rerun the formal audit",
                "does not run simulink",
                "does not export labels",
                "does not retrain the reranker",
                "current audit evidence does not support gcn usefulness over simpler baselines yet",
                "not a final proof against gcn",
                "b1",
                "overconfident",
                "nf06",
                "candidate rows as graph nodes",
                "not physical bus-branch electrical topology",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"GCN audit evidence diagnosis docs missing: {required}")
            for bad in [
                "gcn is useless",
                "final engineering conclusion: true",
                "production_model_saved = true",
                "production model saved: true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
            ]:
                if bad in normalized:
                    failures.append(f"GCN audit evidence diagnosis docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read GCN audit evidence diagnosis artifacts: {exc}")

    paper_dry_dir = ROOT / "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run"
    paper_dry_summary = paper_dry_dir / "paper_aligned_branch_gcn_dry_run_validator_summary.json"
    paper_dry_doc = ROOT / "docs/ieee39_paper_aligned_branch_gcn_redesign_dry_run.md"
    paper_dry_required = [
        paper_dry_doc,
        paper_dry_dir / "paper_method_mapping_summary.json",
        paper_dry_dir / "paper_method_mapping_summary.md",
        paper_dry_dir / "ieee39_branch_topology_source_inventory.json",
        paper_dry_dir / "ieee39_branch_topology_source_inventory.md",
        paper_dry_dir / "ieee39_branch_as_node_graph_manifest.json",
        paper_dry_dir / "ieee39_branch_as_node_graph_manifest.md",
        paper_dry_dir / "paper_aligned_feature_manifest.json",
        paper_dry_dir / "paper_aligned_feature_manifest.md",
        paper_dry_dir / "paper_aligned_label_plan.json",
        paper_dry_dir / "paper_aligned_label_plan.md",
        paper_dry_dir / "hybrid_search_policy_plan.json",
        paper_dry_dir / "hybrid_search_policy_plan.md",
        paper_dry_summary,
        paper_dry_dir / "paper_aligned_branch_gcn_dry_run_validator_summary.md",
        paper_dry_dir / "paper_aligned_branch_gcn_dry_run_validator_summary.csv",
    ]
    existing_paper_dry_required = [path for path in paper_dry_required if path.exists()]
    if existing_paper_dry_required:
        missing_paper_dry_required = [path for path in paper_dry_required if not path.exists()]
        if missing_paper_dry_required:
            failures.append(
                "IEEE39 paper-aligned branch GCN dry-run artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_paper_dry_required)
            )
        try:
            payload = _read_json_path(paper_dry_summary)
            topology = _read_json_path(paper_dry_dir / "ieee39_branch_topology_source_inventory.json")
            graph = _read_json_path(paper_dry_dir / "ieee39_branch_as_node_graph_manifest.json")
            features = _read_json_path(paper_dry_dir / "paper_aligned_feature_manifest.json")
            labels = _read_json_path(paper_dry_dir / "paper_aligned_label_plan.json")
            for key, expected in [
                ("dry_run_scope", "paper_aligned_branch_gcn_redesign_dry_run"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("paper_graph_node_type", "branch"),
                ("paper_graph_edge_rule", "shared_endpoint_bus"),
                ("previous_repo_graph_type", "candidate_similarity_graph"),
                ("previous_candidate_as_node_design_deprecated", True),
                ("proposed_graph_type", "branch_as_node_physical_line_graph"),
                ("bus_fault_labels_directly_paper_aligned", False),
                ("line_trip_labels_first_priority", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if payload.get(key) != expected:
                    failures.append(f"Paper-aligned branch GCN dry-run must set {key}={expected!r}.")
            if payload.get("forbidden_features_detected_in_inputs") != []:
                failures.append("Paper-aligned branch GCN dry-run must keep forbidden_features_detected_in_inputs=[].")
            if topology.get("detected_num_buses") != 39:
                failures.append("Paper-aligned branch GCN dry-run must detect B1-B39 bus list.")
            if topology.get("detected_num_branches") != 34:
                failures.append("Paper-aligned branch GCN dry-run must preserve current L01-L34 map.")
            if topology.get("l12_mapping_status", {}).get("mapping_found") is not True:
                failures.append("Paper-aligned branch GCN dry-run must preserve L12 mapping status.")
            if graph.get("graph_is_candidate_similarity_graph") is not False:
                failures.append("Paper-aligned branch graph must not be marked as candidate similarity graph.")
            if graph.get("graph_uses_physical_branch_connectivity") is not True:
                failures.append("Paper-aligned branch graph must use shared-endpoint physical branch connectivity.")
            if features.get("dynamic_measurements_forbidden") is not True:
                failures.append("Paper-aligned feature manifest must forbid dynamic measurements as inputs.")
            if features.get("feature_readiness_for_prototype") is not False:
                failures.append("Paper-aligned feature manifest must not claim full feature readiness yet.")
            if labels.get("can_build_paper_labels_from_existing_data") is not False:
                failures.append("Paper-aligned label plan must not claim current labels are fully paper-style labels.")
            paper_dry_text = "\n".join(
                [
                    _read_text("docs/ieee39_paper_aligned_branch_gcn_redesign_dry_run.md"),
                    _read_text("results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_method_mapping_summary.md"),
                    _read_text("results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_feature_manifest.md"),
                    _read_text("results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_label_plan.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                ]
            ).lower()
            normalized = " ".join(paper_dry_text.replace("`", "").split())
            for required in [
                "paper-aligned branch gcn redesign dry-run",
                "does not train gcn",
                "does not rerun the formal audit",
                "does not run simulink",
                "does not export labels",
                "does not retrain the reranker",
                "not a candidate-row graph",
                "branch vulnerability vector",
                "bus-fault labels are not directly equivalent",
                "line-trip labels should be the first priority",
                "post-fault dynamic measurements cannot be used as gcn inputs",
                "dynamic_stress_score and unstable_flag can only be labels",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"Paper-aligned branch GCN dry-run docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "final engineering conclusion: true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
                "production_model_saved = true",
            ]:
                if bad in normalized:
                    failures.append(f"Paper-aligned branch GCN dry-run docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read paper-aligned branch GCN dry-run artifacts: {exc}")

    consistency_dir = ROOT / "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_consistency_check"
    consistency_json = consistency_dir / "paper_aligned_redesign_consistency_check.json"
    consistency_md = consistency_dir / "paper_aligned_redesign_consistency_check.md"
    consistency_doc = ROOT / "docs/ieee39_paper_aligned_branch_gcn_redesign_consistency_check.md"
    consistency_required = [consistency_json, consistency_md, consistency_doc]
    existing_consistency_required = [path for path in consistency_required if path.exists()]
    if existing_consistency_required:
        missing_consistency_required = [path for path in consistency_required if not path.exists()]
        if missing_consistency_required:
            failures.append(
                "IEEE39 paper-aligned redesign consistency artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_consistency_required)
            )
        try:
            payload = _read_json_path(consistency_json)
            for key, expected in [
                ("check_scope", "paper_aligned_branch_gcn_redesign_consistency_check"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_dry_run_commit", "3230109b27c3b9af54801b61835b9a491490b2c1"),
                ("execution_summary_post_repair_audit", True),
                ("execution_doc_matches_execution_summary", True),
                ("stale_baseline_only_text_removed", True),
                ("paper_aligned_dry_run_preserved", True),
                ("can_build_branch_line_graph", True),
                ("can_build_required_paper_features", False),
                ("can_build_paper_labels_from_existing_data", False),
                ("bus_fault_labels_directly_paper_aligned", False),
                ("line_trip_labels_first_priority", True),
                ("final_engineering_conclusion", False),
                ("should_deploy_model", False),
                ("should_retrain_reranker_now", False),
            ]:
                if payload.get(key) != expected:
                    failures.append(f"Paper-aligned redesign consistency check must set {key}={expected!r}.")
            if payload.get("failed_checks") != []:
                failures.append("Paper-aligned redesign consistency check must have failed_checks=[].")
            execution_doc = _read_text("docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md").lower()
            normalized_execution = " ".join(execution_doc.replace("`", "").split())
            for required in [
                "post-repair strict no-leakage audit",
                "gcn_trained_for_audit: true",
                "gcn_dependency_available: true",
                "gcn_dependency_status: torch_and_torch_geometric_available",
                "0.7032927445152551",
                "0.12218041951744846",
                "audit evidence does not support gcn usefulness over simpler baselines yet",
            ]:
                if required not in normalized_execution:
                    failures.append(f"Strict no-leakage audit execution doc missing current post-repair wording: {required}")
            for stale in [
                "execution summary is still a baseline-only audit",
                "gcn_trained_for_audit: false",
                "gcn_dependency_status: blocked_by_missing_gcn_dependency",
                "gcn metrics: unavailable",
                "formal gcn audit blocked by missing dependency",
                "baseline-only audit completed",
            ]:
                if stale in normalized_execution:
                    failures.append(f"Strict no-leakage audit execution doc still contains stale wording: {stale}")
            consistency_text = "\n".join(
                [
                    _read_text("docs/ieee39_paper_aligned_branch_gcn_redesign_consistency_check.md"),
                    _read_text("results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_consistency_check/paper_aligned_redesign_consistency_check.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                ]
            ).lower()
            normalized = " ".join(consistency_text.replace("`", "").split())
            for required in [
                "documentation consistency",
                "does not train gcn",
                "does not rerun the formal audit",
                "does not run simulink",
                "does not export labels",
                "does not retrain the reranker",
                "current audit evidence does not support gcn usefulness over simpler baselines yet",
                "can_build_required_paper_features = false",
                "can_build_paper_labels_from_existing_data = false",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized:
                    failures.append(f"Paper-aligned redesign consistency docs missing: {required}")
            for bad in [
                "gcn is useless",
                "final engineering conclusion: true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
                "production_model_saved = true",
                "production ready",
            ]:
                if bad in normalized:
                    failures.append(f"Paper-aligned redesign consistency docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read paper-aligned redesign consistency artifacts: {exc}")

    feature_source_dir = ROOT / "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run"
    feature_source_summary = feature_source_dir / "feature_source_dry_run_validator_summary.json"
    feature_source_inventory = feature_source_dir / "feature_source_inventory.json"
    feature_source_matrix = feature_source_dir / "l01_l34_feature_readiness_matrix.json"
    feature_source_mapping = feature_source_dir / "paper_feature_mapping_plan.json"
    feature_source_no_leakage = feature_source_dir / "no_leakage_feature_source_audit.json"
    feature_source_doc = ROOT / "docs/ieee39_paper_aligned_feature_source_dry_run.md"
    feature_source_required = [
        feature_source_summary,
        feature_source_inventory,
        feature_source_matrix,
        feature_source_mapping,
        feature_source_no_leakage,
        feature_source_doc,
    ]
    existing_feature_source_required = [path for path in feature_source_required if path.exists()]
    if existing_feature_source_required:
        missing_feature_source_required = [path for path in feature_source_required if not path.exists()]
        if missing_feature_source_required:
            failures.append(
                "IEEE39 paper-aligned feature source dry-run artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_feature_source_required)
            )
        try:
            summary = _read_json_path(feature_source_summary)
            inventory = _read_json_path(feature_source_inventory)
            matrix = _read_json_path(feature_source_matrix)
            mapping = _read_json_path(feature_source_mapping)
            no_leakage = _read_json_path(feature_source_no_leakage)
            for key, expected in [
                ("dry_run_scope", "paper_aligned_feature_source_dry_run"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_consistency_commit", "e41e17f591958f8622baa9002f9b5e01376590d5"),
                ("paper_graph_node_type", "branch"),
                ("paper_graph_edge_rule", "shared_endpoint_bus"),
                ("branch_line_graph_ready", True),
                ("num_branch_nodes", 34),
                ("branch_flow_source_ready", False),
                ("line_limit_source_ready", False),
                ("relay_threshold_source_ready", False),
                ("bus_load_source_ready", False),
                ("can_build_required_paper_features", False),
                ("can_build_l01_l34_feature_matrix", False),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_feature_source_policy_passed", True),
                ("l12_special_case_preserved", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Paper-aligned feature source dry-run must set {key}={expected!r}.")
            if "verified current-state branch flow" not in str(summary.get("blocker_if_any", "")):
                failures.append("Paper-aligned feature source dry-run blocker must mention missing verified current-state branch flow.")
            if inventory.get("inventory_scope") != "paper_aligned_feature_source_inventory":
                failures.append("Feature source inventory scope is wrong.")
            if inventory.get("verified_sources_ready") is not False:
                failures.append("Feature source inventory must not mark verified_sources_ready=true yet.")
            if no_leakage.get("forbidden_features_detected_in_inputs") != []:
                failures.append("Feature source no-leakage audit must have forbidden_features_detected_in_inputs=[].")
            if no_leakage.get("post_fault_dynamic_measurements_used_as_inputs") is not False:
                failures.append("Feature source no-leakage audit must not use post-fault dynamic measurements as inputs.")
            if mapping.get("feature_vector_shape") != "L x 4" or mapping.get("current_L") != 34:
                failures.append("Paper feature mapping plan must keep feature_vector_shape='L x 4' and current_L=34.")
            if not isinstance(matrix, list) or len(matrix) != 34:
                failures.append("L01-L34 feature readiness matrix must contain 34 rows.")
            else:
                l12_rows = [row for row in matrix if row.get("line_id") == "L12"]
                if not l12_rows or l12_rows[0].get("l12_special_case_flag") is not True:
                    failures.append("L12 special case flag must be preserved in feature readiness matrix.")
                if any(row.get("ready_for_paper_feature_vector") for row in matrix):
                    failures.append("No L01-L34 row should be marked ready before verified flow/limit/load sources exist.")
            feature_source_text = "\n".join(
                [
                    _read_text("docs/ieee39_paper_aligned_feature_source_dry_run.md"),
                    _read_text("results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/feature_source_inventory.md"),
                    _read_text("results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/paper_feature_mapping_plan.md"),
                    _read_text("results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/no_leakage_feature_source_audit.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                ]
            ).lower()
            normalized_feature_source = " ".join(feature_source_text.replace("`", "").split())
            for required in [
                "paper-aligned feature source dry-run",
                "does not train gcn",
                "does not rerun the formal audit",
                "does not run simulink",
                "does not export labels",
                "does not retrain the reranker",
                "x_t",
                "x_p",
                "x_b",
                "x_l",
                "post-fault dynamic measurement cannot replace",
                "l12 remains a special case",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized_feature_source:
                    failures.append(f"Paper-aligned feature source docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "final engineering conclusion: true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
                "production_model_saved = true",
                "production ready",
            ]:
                if bad in normalized_feature_source:
                    failures.append(f"Paper-aligned feature source docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read paper-aligned feature source dry-run artifacts: {exc}")

    static_source_dir = ROOT / "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run"
    static_summary = static_source_dir / "static_feature_source_dry_run_validator_summary.json"
    static_inventory = static_source_dir / "static_case_source_inventory.json"
    static_plan = static_source_dir / "dc_power_flow_generation_plan.json"
    static_matrix = static_source_dir / "l01_l34_static_feature_source_matrix.json"
    static_proxy = static_source_dir / "relay_threshold_proxy_proposal.json"
    static_no_leakage = static_source_dir / "no_leakage_static_feature_audit.json"
    static_doc = ROOT / "docs/ieee39_static_operating_point_feature_source_dry_run.md"
    static_required = [static_summary, static_inventory, static_plan, static_matrix, static_proxy, static_no_leakage, static_doc]
    existing_static_required = [path for path in static_required if path.exists()]
    if existing_static_required:
        missing_static_required = [path for path in static_required if not path.exists()]
        if missing_static_required:
            failures.append(
                "IEEE39 static operating point feature source dry-run artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_static_required)
            )
        try:
            summary = _read_json_path(static_summary)
            inventory = _read_json_path(static_inventory)
            plan = _read_json_path(static_plan)
            matrix = _read_json_path(static_matrix)
            proxy = _read_json_path(static_proxy)
            no_leakage = _read_json_path(static_no_leakage)
            for key, expected in [
                ("dry_run_scope", "ieee39_static_operating_point_feature_source_dry_run"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_feature_dry_run_commit", "8deeab9b37c1033dc957736981119705977b4473"),
                ("paper_graph_node_type", "branch"),
                ("paper_graph_edge_rule", "shared_endpoint_bus"),
                ("branch_line_graph_ready", True),
                ("num_branch_nodes", 34),
                ("selected_case_source", "pypower.case39"),
                ("selected_case_source_trust_level", "standard_installed_case_loader_static_pre_fault"),
                ("dc_pf_run_this_round", True),
                ("branch_flow_source_ready", True),
                ("line_limit_source_ready", True),
                ("relay_threshold_source_ready", False),
                ("relay_threshold_proxy_proposed", True),
                ("relay_threshold_proxy_allowed_for_training_now", False),
                ("bus_load_source_ready", True),
                ("can_build_l01_l34_static_feature_matrix", False),
                ("can_build_required_paper_features_without_proxy", False),
                ("can_build_required_paper_features_with_documented_proxy", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_static_feature_policy_passed", True),
                ("l12_special_case_preserved", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Static operating point dry-run must set {key}={expected!r}.")
            if "unapproved beta * RATE_A proxy" not in str(summary.get("blocker_if_any", "")):
                failures.append("Static operating point dry-run blocker must mention unapproved beta * RATE_A proxy.")
            for key in ["baseMVA_available", "bus_table_available", "branch_table_available", "generator_table_available", "branch_flow_available", "branch_limit_available", "bus_load_available", "can_generate_dc_power_flow"]:
                if inventory.get(key) is not True:
                    failures.append(f"Static case source inventory must set {key}=True.")
            for key, expected in [
                ("run_dc_pf_this_round", True),
                ("dc_pf_solver_available", True),
                ("uses_simulink", False),
                ("uses_post_fault_dynamic_measurements", False),
                ("baseMVA", 100.0),
                ("bus_count", 39),
                ("branch_count", 46),
                ("mapping_to_L01_L34_possible", True),
            ]:
                if plan.get(key) != expected:
                    failures.append(f"DC PF generation plan must set {key}={expected!r}.")
            for key, expected in [
                ("relay_threshold_source_found", False),
                ("line_limit_source_found", True),
                ("proxy_needed", True),
                ("proposed_proxy", "beta * line_limit"),
                ("beta_value", 1.2),
                ("proxy_allowed_for_training_now", False),
                ("no_training_this_round", True),
            ]:
                if proxy.get(key) != expected:
                    failures.append(f"Relay threshold proxy proposal must set {key}={expected!r}.")
            if no_leakage.get("forbidden_features_detected_in_inputs") != []:
                failures.append("Static no-leakage audit must have forbidden_features_detected_in_inputs=[].")
            if no_leakage.get("post_fault_dynamic_measurements_used_as_inputs") is not False:
                failures.append("Static no-leakage audit must not use post-fault dynamic measurements as inputs.")
            if not isinstance(matrix, list) or len(matrix) != 34:
                failures.append("Static L01-L34 feature source matrix must contain 34 rows.")
            else:
                if not all(row.get("branch_flow_available") for row in matrix):
                    failures.append("Every static matrix row must have branch_flow_available=True.")
                if not all(row.get("line_limit_available") for row in matrix):
                    failures.append("Every static matrix row must have line_limit_available=True.")
                if not all(row.get("endpoint_load_available") for row in matrix):
                    failures.append("Every static matrix row must have endpoint_load_available=True.")
                if any(row.get("relay_threshold_available") for row in matrix):
                    failures.append("Static matrix must not mark relay_threshold_available=True when only proxy exists.")
                if any(row.get("ready_for_lx4_feature_vector") for row in matrix):
                    failures.append("Static matrix must not mark Lx4 vector ready before relay proxy approval.")
                l12_rows = [row for row in matrix if row.get("line_id") == "L12"]
                if not l12_rows or l12_rows[0].get("l12_special_case_flag") is not True:
                    failures.append("Static matrix must preserve L12 special case flag.")
            static_text = "\n".join(
                [
                    _read_text("docs/ieee39_static_operating_point_feature_source_dry_run.md"),
                    _read_text("results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/static_case_source_inventory.md"),
                    _read_text("results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/relay_threshold_proxy_proposal.md"),
                    _read_text("results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/no_leakage_static_feature_audit.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                ]
            ).lower()
            normalized_static = " ".join(static_text.replace("`", "").split())
            for required in [
                "static operating point feature source dry-run",
                "does not train gcn",
                "does not rerun the formal audit",
                "does not run simulink",
                "does not export labels",
                "does not retrain the reranker",
                "relay threshold proxy",
                "not allowed for training now",
                "post-fault dynamic measurements are not used as inputs",
                "l12 remains a special case",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "not engineering-grade protection",
            ]:
                if required not in normalized_static:
                    failures.append(f"Static operating point docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "final engineering conclusion: true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
                "production_model_saved = true",
                "production ready",
            ]:
                if bad in normalized_static:
                    failures.append(f"Static operating point docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read static operating point feature source dry-run artifacts: {exc}")

    proxy_approval_dir = ROOT / "results/gcn_search/ieee39_relay_threshold_proxy_approval"
    proxy_approval_summary = proxy_approval_dir / "relay_threshold_proxy_approval_summary.json"
    proxy_approval_matrix = proxy_approval_dir / "l01_l34_approved_paper_feature_source_matrix.json"
    proxy_approval_no_leakage = proxy_approval_dir / "no_leakage_proxy_feature_audit.json"
    proxy_approval_limitations = proxy_approval_dir / "relay_threshold_proxy_limitations.md"
    proxy_approval_doc = ROOT / "docs/ieee39_relay_threshold_proxy_approval.md"
    proxy_approval_required = [
        proxy_approval_summary,
        proxy_approval_dir / "relay_threshold_proxy_approval_summary.md",
        proxy_approval_dir / "relay_threshold_proxy_approval_summary.csv",
        proxy_approval_matrix,
        proxy_approval_dir / "l01_l34_approved_paper_feature_source_matrix.md",
        proxy_approval_dir / "l01_l34_approved_paper_feature_source_matrix.csv",
        proxy_approval_no_leakage,
        proxy_approval_dir / "no_leakage_proxy_feature_audit.md",
        proxy_approval_limitations,
        proxy_approval_doc,
    ]
    existing_proxy_approval_required = [path for path in proxy_approval_required if path.exists()]
    if existing_proxy_approval_required:
        missing_proxy_approval_required = [path for path in proxy_approval_required if not path.exists()]
        if missing_proxy_approval_required:
            failures.append(
                "IEEE39 relay threshold proxy approval artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_proxy_approval_required)
            )
        try:
            summary = _read_json_path(proxy_approval_summary)
            matrix = _read_json_path(proxy_approval_matrix)
            no_leakage = _read_json_path(proxy_approval_no_leakage)
            for key, expected in [
                ("approval_scope", "relay_threshold_proxy_approval"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_static_feature_commit", "a29bc6e209afe764aa8bf57613d66dd53114fba9"),
                ("relay_threshold_source_ready", False),
                ("relay_threshold_proxy_approved", True),
                ("relay_threshold_proxy_allowed_for_audit_only_prototype", True),
                ("relay_threshold_proxy_allowed_for_production", False),
                ("proxy_formula", "beta * RATE_A"),
                ("beta_value", 1.2),
                ("beta_value_source", "project default beta = 1.2"),
                ("line_limit_source", "pypower.case39 branch RATE_A"),
                ("branch_flow_source_ready", True),
                ("line_limit_source_ready", True),
                ("bus_load_source_ready", True),
                ("can_build_required_paper_features_without_proxy", False),
                ("can_build_required_paper_features_with_approved_proxy", True),
                ("can_build_l01_l34_paper_feature_matrix_with_proxy", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("l12_special_case_preserved", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Relay threshold proxy approval must set {key}={expected!r}.")
            if summary.get("recommended_next_step") != "prepare paper-style branch vulnerability label generator dry-run for line-trip labels":
                failures.append("Relay threshold proxy approval recommended next step must be label generator dry-run.")
            if len(matrix) != 34:
                failures.append("Approved L01-L34 paper feature source matrix must contain 34 rows.")
            if not all(row.get("ready_for_lx4_feature_vector_with_proxy") is True for row in matrix):
                failures.append("Approved L01-L34 matrix must mark all rows ready with proxy.")
            if not all(row.get("relay_threshold_is_proxy") is True for row in matrix):
                failures.append("Approved L01-L34 matrix must mark relay_threshold_is_proxy=true.")
            if any(row.get("proxy_allowed_for_production") is not False for row in matrix):
                failures.append("Approved L01-L34 matrix must keep proxy_allowed_for_production=false.")
            if not any(row.get("line_id") == "L12" and row.get("l12_special_case_flag") is True for row in matrix):
                failures.append("Approved L01-L34 matrix must preserve L12 special case flag.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("static_or_prefault_sources_only", True),
                ("dynamic_targets_only_used_as_labels", True),
                ("proxy_not_engineering_relay_setting", True),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"Proxy no-leakage audit must set {key}={expected!r}.")
            proxy_text = "\n".join(
                [
                    _read_text("docs/ieee39_relay_threshold_proxy_approval.md"),
                    _read_text("results/gcn_search/ieee39_relay_threshold_proxy_approval/relay_threshold_proxy_approval_summary.md"),
                    _read_text("results/gcn_search/ieee39_relay_threshold_proxy_approval/relay_threshold_proxy_limitations.md"),
                    _read_text("results/gcn_search/ieee39_relay_threshold_proxy_approval/no_leakage_proxy_feature_audit.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_static_operating_point_feature_source_dry_run.md"),
                    _read_text("docs/ieee39_paper_aligned_feature_source_dry_run.md"),
                ]
            ).lower()
            normalized_proxy = " ".join(proxy_text.replace("`", "").split())
            for required in [
                "relay threshold proxy approval",
                "did not train gcn",
                "did not rerun formal audit",
                "did not run simulink",
                "did not export labels",
                "did not retrain the reranker",
                "audit-only paper-aligned prototype proxy",
                "beta * rate_a",
                "beta = 1.2",
                "not a real relay protection setting",
                "not an engineering-grade relay threshold",
                "not allowed for production",
                "post-fault dynamic measurements are not used as inputs",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_proxy:
                    failures.append(f"Relay threshold proxy approval docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "final engineering conclusion: true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
                "engineering-grade relay threshold = true",
                "relay_threshold_proxy_allowed_for_production = true",
                "production ready",
            ]:
                if bad in normalized_proxy:
                    failures.append(f"Relay threshold proxy approval docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read relay threshold proxy approval artifacts: {exc}")

    label_generator_dir = ROOT / "results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run"
    label_generator_summary = label_generator_dir / "branch_vulnerability_label_generator_dry_run_summary.json"
    label_generator_semantics = label_generator_dir / "branch_vulnerability_label_semantics.json"
    label_generator_states = label_generator_dir / "state_space_manifest.json"
    label_generator_plan = label_generator_dir / "state_branch_label_generation_plan.json"
    label_generator_reuse = label_generator_dir / "existing_label_reuse_audit.json"
    label_generator_no_leakage = label_generator_dir / "no_leakage_label_generator_audit.json"
    label_generator_blocker = label_generator_dir / "label_generator_blocker_report.json"
    label_generator_doc = ROOT / "docs/ieee39_paper_style_branch_vulnerability_label_generator_dry_run.md"
    label_generator_required = [
        label_generator_semantics,
        label_generator_dir / "branch_vulnerability_label_semantics.md",
        label_generator_states,
        label_generator_dir / "state_space_manifest.md",
        label_generator_dir / "state_space_manifest.csv",
        label_generator_plan,
        label_generator_dir / "state_branch_label_generation_plan.md",
        label_generator_dir / "state_branch_label_generation_plan.csv",
        label_generator_reuse,
        label_generator_dir / "existing_label_reuse_audit.md",
        label_generator_no_leakage,
        label_generator_dir / "no_leakage_label_generator_audit.md",
        label_generator_blocker,
        label_generator_dir / "label_generator_blocker_report.md",
        label_generator_summary,
        label_generator_dir / "branch_vulnerability_label_generator_dry_run_summary.md",
        label_generator_dir / "branch_vulnerability_label_generator_dry_run_summary.csv",
        label_generator_doc,
    ]
    existing_label_generator_required = [path for path in label_generator_required if path.exists()]
    if existing_label_generator_required:
        missing_label_generator_required = [path for path in label_generator_required if not path.exists()]
        if missing_label_generator_required:
            failures.append(
                "IEEE39 paper-style branch vulnerability label generator dry-run artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_label_generator_required)
            )
        try:
            summary = _read_json_path(label_generator_summary)
            semantics = _read_json_path(label_generator_semantics)
            states = _read_json_path(label_generator_states)
            plan_rows = _read_json_path(label_generator_plan)
            reuse = _read_json_path(label_generator_reuse)
            no_leakage = _read_json_path(label_generator_no_leakage)
            blocker = _read_json_path(label_generator_blocker)
            for key, expected in [
                ("dry_run_scope", "paper_style_branch_vulnerability_label_generator_dry_run"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_proxy_approval_commit", "caa1decb21bddecc899fa55e5e9ce44241c8a029"),
                ("paper_graph_node_type", "branch"),
                ("paper_graph_edge_rule", "shared_endpoint_bus"),
                ("num_branch_nodes", 34),
                ("feature_matrix_with_proxy_ready", True),
                ("relay_threshold_is_proxy", True),
                ("proxy_allowed_for_audit_only_prototype", True),
                ("proxy_allowed_for_production", False),
                ("label_shape_target", "num_states x num_branches"),
                ("num_states_planned", 35),
                ("num_state_branch_pairs_planned", 1156),
                ("can_generate_full_state_branch_label_matrix_now", False),
                ("can_generate_base_state_single_line_labels_now", False),
                ("can_generate_single_outage_next_branch_labels_now", False),
                ("bus_fault_labels_directly_paper_aligned", False),
                ("line_trip_labels_first_priority", True),
                ("l12_special_case_preserved", True),
                ("nf06_warning_preserved", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_label_generator_policy_passed", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_export_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Branch vulnerability label generator dry-run must set {key}={expected!r}.")
            if "no complete state x branch" not in str(summary.get("blocker_if_any", "")):
                failures.append("Branch vulnerability label generator blocker must mention missing state x branch label source.")
            if summary.get("recommended_next_step") != "implement controlled line-trip label generation loop for paper-style branch vulnerability labels":
                failures.append("Branch vulnerability label generator recommended next step must be controlled line-trip loop.")
            for key, expected in [
                ("label_semantics_scope", "paper_style_branch_vulnerability_label_semantics"),
                ("paper_label_type", "branch_vulnerability_binary_vector"),
                ("label_shape", "num_states x num_branches"),
                ("bus_fault_labels_directly_paper_aligned", False),
                ("line_trip_labels_first_priority", True),
                ("no_training_this_round", True),
            ]:
                if semantics.get(key) != expected:
                    failures.append(f"Branch vulnerability label semantics must set {key}={expected!r}.")
            if len(states) != 35:
                failures.append("State space manifest must contain 35 states.")
            if not states or states[0].get("state_id") != "base_state":
                failures.append("State space manifest must start with base_state.")
            if len(plan_rows) != 1156:
                failures.append("State-branch label generation plan must contain 1156 rows.")
            if any(row.get("label_value") is not None for row in plan_rows):
                failures.append("Label generation dry-run must not fabricate 0/1 label values.")
            if any(row.get("label_source_available") is not False for row in plan_rows):
                failures.append("Label generation dry-run must keep label_source_available=false.")
            if not any(row.get("l12_special_case_flag") is True for row in plan_rows):
                failures.append("Label generation plan must preserve L12 special case rows.")
            for key, expected in [
                ("bus_fault_labels_directly_paper_aligned", False),
                ("l12_excluded_or_special", True),
                ("nf06_warning_preserved", True),
            ]:
                if reuse.get(key) != expected:
                    failures.append(f"Existing label reuse audit must set {key}={expected!r}.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("proxy_relay_threshold_used_only_in_feature_generation", True),
                ("no_leakage_label_generator_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"No-leakage label generator audit must set {key}={expected!r}.")
            for key, expected in [
                ("can_generate_full_state_branch_label_matrix_now", False),
                ("can_generate_base_state_single_line_labels_now", False),
                ("can_generate_single_outage_next_branch_labels_now", False),
                ("no_simulink_run_this_round", True),
                ("no_label_export_this_round", True),
            ]:
                if blocker.get(key) != expected:
                    failures.append(f"Label generator blocker report must set {key}={expected!r}.")
            label_text = "\n".join(
                [
                    _read_text("docs/ieee39_paper_style_branch_vulnerability_label_generator_dry_run.md"),
                    _read_text("results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/branch_vulnerability_label_semantics.md"),
                    _read_text("results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/state_branch_label_generation_plan.md"),
                    _read_text("results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/label_generator_blocker_report.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_relay_threshold_proxy_approval.md"),
                    _read_text("docs/ieee39_static_operating_point_feature_source_dry_run.md"),
                    _read_text("docs/ieee39_paper_aligned_branch_gcn_redesign_dry_run.md"),
                ]
            ).lower()
            normalized_label = " ".join(label_text.replace("`", "").split())
            for required in [
                "paper-style branch vulnerability label generator dry-run",
                "did not train gcn",
                "did not rerun formal audit",
                "did not run simulink",
                "did not export formal labels",
                "did not retrain the reranker",
                "state x branch",
                "vulnerability vector",
                "scenario-level dynamic labels",
                "bus-fault labels are not directly paper-aligned",
                "line-trip labels should be prepared first",
                "beta * rate_a",
                "not a real relay setting",
                "not an engineering-grade protection threshold",
                "controlled line-trip label generation loop",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_label:
                    failures.append(f"Branch vulnerability label generator docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "labels exported = true",
                "formal_labels_exported = true",
                "final engineering conclusion: true",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
                "real relay setting = true",
                "production ready",
            ]:
                if bad in normalized_label:
                    failures.append(f"Branch vulnerability label generator docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read branch vulnerability label generator dry-run artifacts: {exc}")

    base_pilot_dir = ROOT / "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot"
    base_pilot_summary = base_pilot_dir / "base_state_branch_vulnerability_label_pilot_summary.json"
    base_pilot_matrix = base_pilot_dir / "base_state_branch_vulnerability_label_matrix.json"
    base_pilot_reuse = base_pilot_dir / "existing_line_trip_label_reuse_report.json"
    base_pilot_no_leakage = base_pilot_dir / "no_leakage_base_state_label_pilot_audit.json"
    base_pilot_doc = ROOT / "docs/ieee39_base_state_branch_vulnerability_label_pilot.md"
    base_pilot_required = [
        base_pilot_summary,
        base_pilot_dir / "base_state_branch_vulnerability_label_pilot_summary.md",
        base_pilot_dir / "base_state_branch_vulnerability_label_pilot_summary.csv",
        base_pilot_matrix,
        base_pilot_dir / "base_state_branch_vulnerability_label_matrix.md",
        base_pilot_dir / "base_state_branch_vulnerability_label_matrix.csv",
        base_pilot_reuse,
        base_pilot_dir / "existing_line_trip_label_reuse_report.md",
        base_pilot_no_leakage,
        base_pilot_dir / "no_leakage_base_state_label_pilot_audit.md",
        base_pilot_doc,
    ]
    existing_base_pilot_required = [path for path in base_pilot_required if path.exists()]
    if existing_base_pilot_required:
        missing_base_pilot_required = [path for path in base_pilot_required if not path.exists()]
        if missing_base_pilot_required:
            failures.append(
                "IEEE39 base-state branch vulnerability label pilot artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_base_pilot_required)
            )
        try:
            summary = _read_json_path(base_pilot_summary)
            matrix = _read_json_path(base_pilot_matrix)
            reuse = _read_json_path(base_pilot_reuse)
            no_leakage = _read_json_path(base_pilot_no_leakage)
            for key, expected in [
                ("pilot_scope", "base_state_branch_vulnerability_label_pilot"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_label_generator_dry_run_commit", "221fa4baa1a1f1090fd953650b8577031380ffe8"),
                ("state_id", "base_state"),
                ("prior_outaged_branches", []),
                ("num_candidate_branches", 34),
                ("num_label_slots", 34),
                ("num_labels_available", 33),
                ("num_labels_unknown", 0),
                ("num_labels_excluded", 1),
                ("l12_special_case_preserved", True),
                ("feature_matrix_with_proxy_ready", True),
                ("relay_threshold_is_proxy", True),
                ("proxy_allowed_for_audit_only_prototype", True),
                ("proxy_allowed_for_production", False),
                ("bus_fault_labels_used", False),
                ("line_trip_labels_first_priority", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("pilot_labels_are_formal_training_labels", False),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_export_formal_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
                ("blocker_if_any", None),
                ("recommended_next_step", "prepare controlled single-outage state label generation loop dry-run"),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Base-state branch vulnerability label pilot must set {key}={expected!r}.")
            if len(matrix) != 34:
                failures.append("Base-state label pilot matrix must contain 34 rows.")
            else:
                l12_rows = [row for row in matrix if row.get("line_id") == "L12"]
                if len(l12_rows) != 1:
                    failures.append("Base-state label pilot matrix must contain exactly one L12 row.")
                elif not (
                    l12_rows[0].get("label_status") == "excluded"
                    and l12_rows[0].get("label_value") is None
                    and l12_rows[0].get("l12_special_case_flag") is True
                ):
                    failures.append("Base-state label pilot must preserve L12 as excluded/null/special.")
                non_l12 = [row for row in matrix if row.get("line_id") != "L12"]
                if len(non_l12) != 33:
                    failures.append("Base-state label pilot must contain 33 non-L12 rows.")
                if any(row.get("state_id") != "base_state" for row in matrix):
                    failures.append("Base-state label pilot matrix must only use state_id=base_state.")
                if any(row.get("prior_outaged_branches") != [] for row in matrix):
                    failures.append("Base-state label pilot matrix must keep prior_outaged_branches=[].")
                if any(row.get("label_status") != "available" for row in non_l12):
                    failures.append("All non-L12 base-state pilot rows should be available from existing line-trip artifacts.")
                if any(row.get("label_source") != "existing_training_ready_handwired_line_trip" for row in non_l12):
                    failures.append("All non-L12 base-state pilot rows must use existing line-trip label source.")
            for key, expected in [
                ("existing_line_trip_labels_found", True),
                ("existing_line_trip_labels_count", 33),
                ("reused_for_base_state_count", 33),
                ("unknown_count", 0),
                ("excluded_count", 1),
                ("l12_status", "excluded_special_islanding_timeout"),
                ("old_formal_gate_preserved", True),
            ]:
                if reuse.get(key) != expected:
                    failures.append(f"Existing line-trip label reuse report must set {key}={expected!r}.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("proxy_relay_threshold_used_only_in_feature_generation", True),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"No-leakage base-state label pilot audit must set {key}={expected!r}.")
            base_pilot_text = "\n".join(
                [
                    _read_text("docs/ieee39_base_state_branch_vulnerability_label_pilot.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_paper_style_branch_vulnerability_label_generator_dry_run.md"),
                    _read_text("docs/ieee39_relay_threshold_proxy_approval.md"),
                    _read_text("results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_pilot_summary.md"),
                    _read_text("results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/existing_line_trip_label_reuse_report.md"),
                    _read_text("results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/no_leakage_base_state_label_pilot_audit.md"),
                ]
            ).lower()
            normalized_base_pilot = " ".join(base_pilot_text.replace("`", "").split())
            for required in [
                "base-state label pilot only",
                "does not train gcn",
                "does not rerun formal audit",
                "does not run simulink",
                "does not export formal labels",
                "does not retrain the reranker",
                "only base_state x l01-l34",
                "does not generate single_outage_state x next_branch labels",
                "does not use bus-fault labels",
                "unknown or missing sources remain null",
                "l12 remains special/excluded",
                "beta * rate_a",
                "audit-only",
                "not a real relay setting",
                "pilot labels are not formal training labels",
                "controlled single-outage state label generation loop",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_base_pilot:
                    failures.append(f"Base-state label pilot docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "formal labels exported",
                "final engineering conclusion: true",
                "production_model_saved = true",
                "real relay setting = true",
            ]:
                if bad in normalized_base_pilot:
                    failures.append(f"Base-state label pilot docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read base-state branch vulnerability label pilot artifacts: {exc}")

    single_outage_dir = ROOT / "results/gcn_search/ieee39_single_outage_label_loop_dry_run"
    single_outage_summary = single_outage_dir / "single_outage_label_loop_dry_run_summary.json"
    single_outage_states = single_outage_dir / "single_outage_state_manifest.json"
    single_outage_plan = single_outage_dir / "single_outage_state_branch_label_loop_plan.json"
    single_outage_base_review = single_outage_dir / "base_state_label_distribution_review.json"
    single_outage_reuse = single_outage_dir / "existing_artifact_reuse_for_single_outage_audit.json"
    single_outage_no_leakage = single_outage_dir / "no_leakage_single_outage_label_loop_audit.json"
    single_outage_doc = ROOT / "docs/ieee39_single_outage_label_loop_dry_run.md"
    single_outage_required = [
        single_outage_states,
        single_outage_dir / "single_outage_state_manifest.md",
        single_outage_dir / "single_outage_state_manifest.csv",
        single_outage_plan,
        single_outage_dir / "single_outage_state_branch_label_loop_plan.md",
        single_outage_dir / "single_outage_state_branch_label_loop_plan.csv",
        single_outage_base_review,
        single_outage_dir / "base_state_label_distribution_review.md",
        single_outage_reuse,
        single_outage_dir / "existing_artifact_reuse_for_single_outage_audit.md",
        single_outage_no_leakage,
        single_outage_dir / "no_leakage_single_outage_label_loop_audit.md",
        single_outage_summary,
        single_outage_dir / "single_outage_label_loop_dry_run_summary.md",
        single_outage_dir / "single_outage_label_loop_dry_run_summary.csv",
        single_outage_doc,
    ]
    existing_single_outage_required = [path for path in single_outage_required if path.exists()]
    if existing_single_outage_required:
        missing_single_outage_required = [path for path in single_outage_required if not path.exists()]
        if missing_single_outage_required:
            failures.append(
                "IEEE39 single-outage label loop dry-run artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_single_outage_required)
            )
        try:
            summary = _read_json_path(single_outage_summary)
            states = _read_json_path(single_outage_states)
            plan = _read_json_path(single_outage_plan)
            base_review = _read_json_path(single_outage_base_review)
            reuse = _read_json_path(single_outage_reuse)
            no_leakage = _read_json_path(single_outage_no_leakage)
            for key, expected in [
                ("dry_run_scope", "single_outage_label_loop_dry_run"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("new_simulink_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_base_state_pilot_commit", "449f8d1e625672bb6e01fbffd59c6bb97d3d0fe0"),
                ("paper_graph_node_type", "branch"),
                ("paper_graph_edge_rule", "shared_endpoint_bus"),
                ("feature_matrix_with_proxy_ready", True),
                ("relay_threshold_is_proxy", True),
                ("proxy_allowed_for_audit_only_prototype", True),
                ("proxy_allowed_for_production", False),
                ("base_state_all_available_labels_negative", True),
                ("base_state_should_not_be_used_alone_for_training", True),
                ("num_single_outage_states_planned", 34),
                ("num_state_branch_pairs_planned", 1122),
                ("num_pairs_excluded_due_to_same_branch", 34),
                ("num_pairs_excluded_due_to_l12_special", 66),
                ("num_pairs_planned_for_future_generation", 1056),
                ("num_pairs_available_from_existing_artifacts", 0),
                ("can_generate_single_outage_labels_now", False),
                ("can_export_formal_single_outage_labels_now", False),
                ("bus_fault_labels_used", False),
                ("line_trip_labels_first_priority", True),
                ("l12_special_case_preserved", True),
                ("nf06_warning_preserved", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_export_formal_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
                (
                    "recommended_next_step",
                    "implement controlled generation runner for selected single-outage pilot pairs in a separate round",
                ),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Single-outage label loop dry-run must set {key}={expected!r}.")
            if "no approved reusable single_outage_state x next_branch" not in str(summary.get("blocker_if_any")):
                failures.append("Single-outage dry-run must record the missing reusable-artifact blocker.")
            if len(states) != 34:
                failures.append("Single-outage state manifest must contain 34 states.")
            else:
                l12_states = [row for row in states if row.get("prior_outaged_branch") == "L12"]
                if len(l12_states) != 1 or l12_states[0].get("eligible_for_label_generation") is not False:
                    failures.append("Single-outage state manifest must preserve prior L12 as ineligible/special.")
                if any(row.get("num_candidate_next_branches") != 33 for row in states):
                    failures.append("Each single-outage state must plan 33 next-branch candidates.")
                if any(row.get("prior_outaged_branch") in row.get("candidate_next_branches", []) for row in states):
                    failures.append("Single-outage states must not include the prior outage as a next candidate.")
            if len(plan) != 1122:
                failures.append("Single-outage pair plan must contain 1122 ordered prior->next rows.")
            else:
                l12_rows = [row for row in plan if row.get("l12_special_case_flag")]
                planned_rows = [row for row in plan if row.get("label_status") == "planned"]
                if len(l12_rows) != 66:
                    failures.append("Single-outage pair plan must exclude 66 rows involving L12.")
                if len(planned_rows) != 1056:
                    failures.append("Single-outage pair plan must leave 1056 rows for future generation.")
                if any(row.get("label_value") is not None for row in plan):
                    failures.append("Single-outage dry-run must not fabricate 0/1 labels.")
                if any(row.get("bus_fault_label_used") is not False for row in plan):
                    failures.append("Single-outage pair plan must not use bus-fault labels.")
                if any(row.get("prior_outaged_branch") == row.get("candidate_next_branch") for row in plan):
                    failures.append("Single-outage pair plan must exclude same-branch prior/candidate rows.")
            for key, expected in [
                ("base_state_num_label_slots", 34),
                ("base_state_num_labels_available", 33),
                ("base_state_num_positive_labels", 0),
                ("base_state_num_negative_labels", 33),
                ("base_state_num_excluded_labels", 1),
                ("base_state_all_available_labels_negative", True),
                ("training_risk_if_using_base_state_only", True),
            ]:
                if base_review.get(key) != expected:
                    failures.append(f"Single-outage base-state review must set {key}={expected!r}.")
            for key, expected in [
                ("existing_multi_line_or_path_labels_found", False),
                ("reusable_for_single_outage_count", 0),
                ("reusable_sequences", []),
                ("bus_fault_labels_used", False),
                ("l12_excluded_or_special", True),
            ]:
                if reuse.get(key) != expected:
                    failures.append(f"Single-outage reuse audit must set {key}={expected!r}.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("proxy_relay_threshold_used_only_in_feature_generation", True),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"Single-outage no-leakage audit must set {key}={expected!r}.")
            single_outage_text = "\n".join(
                [
                    _read_text("docs/ieee39_single_outage_label_loop_dry_run.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_label_loop_dry_run_summary.md"),
                    _read_text("results/gcn_search/ieee39_single_outage_label_loop_dry_run/base_state_label_distribution_review.md"),
                    _read_text("results/gcn_search/ieee39_single_outage_label_loop_dry_run/existing_artifact_reuse_for_single_outage_audit.md"),
                    _read_text("results/gcn_search/ieee39_single_outage_label_loop_dry_run/no_leakage_single_outage_label_loop_audit.md"),
                ]
            ).lower()
            normalized_single_outage = " ".join(single_outage_text.replace("`", "").split())
            for required in [
                "controlled single-outage state label loop dry-run",
                "does not train gcn",
                "does not rerun formal audit",
                "does not run new simulink",
                "does not export formal labels",
                "does not retrain the reranker",
                "all 33 available non-l12 labels were negative",
                "cannot train",
                "single_outage_state x next_branch",
                "does not fabricate 0/1 labels",
                "beta * rate_a",
                "audit-only proxy",
                "not a real relay setting",
                "bus-fault labels are unused",
                "l12 stays special/excluded",
                "nf06 warning is preserved",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_single_outage:
                    failures.append(f"Single-outage label loop docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "formal labels exported",
                "final engineering conclusion: true",
                "production_model_saved = true",
                "real relay setting = true",
                "deployment ready",
            ]:
                if bad in normalized_single_outage:
                    failures.append(f"Single-outage label loop docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read single-outage label loop dry-run artifacts: {exc}")

    pilot_pair_dir = ROOT / "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run"
    pilot_pair_summary = pilot_pair_dir / "single_outage_pilot_pair_runner_dry_run_summary.json"
    pilot_pair_selection = pilot_pair_dir / "pilot_pair_selection_summary.json"
    pilot_pair_selected = pilot_pair_dir / "selected_single_outage_pilot_pairs.json"
    pilot_pair_run_plan = pilot_pair_dir / "future_controlled_generation_run_plan.json"
    pilot_pair_no_leakage = pilot_pair_dir / "no_leakage_pilot_pair_runner_audit.json"
    pilot_pair_doc = ROOT / "docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md"
    pilot_pair_required = [
        pilot_pair_selection,
        pilot_pair_dir / "pilot_pair_selection_summary.md",
        pilot_pair_dir / "pilot_pair_selection_summary.csv",
        pilot_pair_selected,
        pilot_pair_dir / "selected_single_outage_pilot_pairs.md",
        pilot_pair_dir / "selected_single_outage_pilot_pairs.csv",
        pilot_pair_run_plan,
        pilot_pair_dir / "future_controlled_generation_run_plan.md",
        pilot_pair_no_leakage,
        pilot_pair_dir / "no_leakage_pilot_pair_runner_audit.md",
        pilot_pair_summary,
        pilot_pair_dir / "single_outage_pilot_pair_runner_dry_run_summary.md",
        pilot_pair_dir / "single_outage_pilot_pair_runner_dry_run_summary.csv",
        pilot_pair_doc,
    ]
    existing_pilot_pair_required = [path for path in pilot_pair_required if path.exists()]
    if existing_pilot_pair_required:
        missing_pilot_pair_required = [path for path in pilot_pair_required if not path.exists()]
        if missing_pilot_pair_required:
            failures.append(
                "IEEE39 single-outage pilot pair runner dry-run artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_pilot_pair_required)
            )
        try:
            summary = _read_json_path(pilot_pair_summary)
            selection = _read_json_path(pilot_pair_selection)
            selected = _read_json_path(pilot_pair_selected)
            run_plan = _read_json_path(pilot_pair_run_plan)
            no_leakage = _read_json_path(pilot_pair_no_leakage)
            for key, expected in [
                ("dry_run_scope", "single_outage_pilot_pair_runner_dry_run"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("new_simulink_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_single_outage_loop_commit", "b5e98d4fd27f438b2d46e6ec0ec60b46e21bcda9"),
                ("feature_matrix_with_proxy_ready", True),
                ("relay_threshold_is_proxy", True),
                ("proxy_allowed_for_audit_only_prototype", True),
                ("proxy_allowed_for_production", False),
                ("base_state_should_not_be_used_alone_for_training", True),
                ("num_candidate_pairs_available", 1056),
                ("label_values_fabricated", False),
                ("selected_pairs_label_status", "planned"),
                ("can_execute_future_generation_runner_after_approval", True),
                ("bus_fault_labels_used", False),
                ("line_trip_labels_first_priority", True),
                ("l12_special_case_preserved", True),
                ("nf06_warning_preserved", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_run_simulink_now", False),
                ("should_export_formal_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
                ("blocker_if_any", None),
                (
                    "recommended_next_step",
                    "approve and execute selected single-outage pilot pair generation in a separate round",
                ),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Single-outage pilot pair runner dry-run must set {key}={expected!r}.")
            for key in [
                "num_pilot_pairs_selected",
                "num_high_relay_ratio_pairs",
                "num_shared_bus_neighbor_pairs",
                "num_non_neighbor_control_pairs",
            ]:
                if int(summary.get(key, 0)) <= 0:
                    failures.append(f"Single-outage pilot pair runner dry-run must have {key} > 0.")
            for key, expected in [
                ("selection_scope", "single_outage_pilot_pair_selection"),
                ("source_single_outage_loop_commit", "b5e98d4fd27f438b2d46e6ec0ec60b46e21bcda9"),
                ("max_pairs_requested", 32),
                ("num_l12_pairs_excluded", 66),
                ("bus_fault_labels_used", False),
                ("label_values_fabricated", False),
                ("ready_for_future_controlled_generation", True),
            ]:
                if selection.get(key) != expected:
                    failures.append(f"Pilot pair selection summary must set {key}={expected!r}.")
            if selection.get("num_pairs_selected") != summary.get("num_pilot_pairs_selected"):
                failures.append("Pilot pair selection count must match dry-run summary count.")
            if len(selected) != summary.get("num_pilot_pairs_selected"):
                failures.append("Selected pilot pair JSON count must match dry-run summary count.")
            else:
                buckets = {row.get("selection_bucket") for row in selected}
                for bucket in [
                    "high_relay_ratio_pairs",
                    "shared_bus_neighbor_pairs",
                    "non_neighbor_control_pairs",
                ]:
                    if bucket not in buckets:
                        failures.append(f"Selected pilot pairs must include bucket {bucket}.")
                if any(row.get("label_value") is not None for row in selected):
                    failures.append("Selected pilot pairs must not fabricate label_value.")
                if any(row.get("label_status") != "planned" for row in selected):
                    failures.append("Selected pilot pairs must keep label_status=planned.")
                if any(row.get("bus_fault_label_used") is not False for row in selected):
                    failures.append("Selected pilot pairs must not use bus-fault labels.")
                if any(row.get("l12_special_case_flag") is not False for row in selected):
                    failures.append("Selected pilot pairs must exclude L12 special rows.")
                if any(
                    "L12" in {row.get("prior_outaged_branch"), row.get("candidate_next_branch")}
                    for row in selected
                ):
                    failures.append("Selected pilot pairs must not include L12 as prior or next branch.")
            for key, expected in [
                ("run_plan_scope", "future_controlled_single_outage_pilot_generation"),
                ("dry_run_only_this_round", True),
                ("new_simulink_run_this_round", False),
                ("selected_pair_count", summary.get("num_pilot_pairs_selected")),
                ("no_raw_trajectory_commit_policy", True),
                ("no_formal_label_export_this_round", True),
                ("required_manual_approval_before_execution", True),
            ]:
                if run_plan.get(key) != expected:
                    failures.append(f"Pilot pair future run plan must set {key}={expected!r}.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_future_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("proxy_relay_threshold_used_only_in_feature_generation", True),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"Pilot pair no-leakage audit must set {key}={expected!r}.")
            pilot_pair_text = "\n".join(
                [
                    _read_text("docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_single_outage_label_loop_dry_run.md"),
                    _read_text("docs/ieee39_base_state_branch_vulnerability_label_pilot.md"),
                    _read_text("results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/pilot_pair_selection_summary.md"),
                    _read_text("results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/future_controlled_generation_run_plan.md"),
                    _read_text("results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/no_leakage_pilot_pair_runner_audit.md"),
                    _read_text("results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/single_outage_pilot_pair_runner_dry_run_summary.md"),
                ]
            ).lower()
            normalized_pilot_pair = " ".join(pilot_pair_text.replace("`", "").split())
            for required in [
                "selected single-outage pilot pair generation runner dry-run",
                "does not train gcn",
                "does not rerun formal audit",
                "does not run new simulink",
                "does not export formal labels",
                "does not retrain the reranker",
                "base-state labels are all negative",
                "cannot be used alone",
                "does not run all 1056",
                "high_relay_ratio_pairs",
                "shared_bus_neighbor_pairs",
                "non_neighbor_control_pairs",
                "l12 remains special/excluded",
                "nf06 warning is preserved",
                "beta * rate_a",
                "audit-only proxy",
                "not a real relay setting",
                "bus-fault labels are not used",
                "manual approval is required",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_pilot_pair:
                    failures.append(f"Single-outage pilot pair runner docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "formal labels exported",
                "ran new simulink",
                "proxy is a real relay setting",
                "final engineering conclusion: true",
                "emt simulation",
                "generator_speed_proxy is direct frequency",
                "production_model_saved = true",
                "deployment ready",
            ]:
                if bad in normalized_pilot_pair:
                    failures.append(f"Single-outage pilot pair runner docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read single-outage pilot pair runner dry-run artifacts: {exc}")

    selected_pair_exec_dir = ROOT / "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution"
    selected_pair_exec_summary = selected_pair_exec_dir / "selected_pair_execution_summary.json"
    selected_pair_exec_approval = selected_pair_exec_dir / "selected_pair_execution_approval.json"
    selected_pair_exec_results = selected_pair_exec_dir / "selected_pair_execution_results.json"
    selected_pair_exec_distribution = selected_pair_exec_dir / "selected_pair_label_distribution.json"
    selected_pair_exec_no_leakage = selected_pair_exec_dir / "no_leakage_selected_pair_execution_audit.json"
    selected_pair_exec_safety = selected_pair_exec_dir / "large_file_and_artifact_safety_check.json"
    selected_pair_exec_doc = ROOT / "docs/ieee39_selected_single_outage_pilot_pair_execution.md"
    selected_pair_exec_required = [
        selected_pair_exec_approval,
        selected_pair_exec_dir / "selected_pair_execution_approval.md",
        selected_pair_exec_summary,
        selected_pair_exec_dir / "selected_pair_execution_summary.md",
        selected_pair_exec_dir / "selected_pair_execution_summary.csv",
        selected_pair_exec_results,
        selected_pair_exec_dir / "selected_pair_execution_results.md",
        selected_pair_exec_dir / "selected_pair_execution_results.csv",
        selected_pair_exec_distribution,
        selected_pair_exec_dir / "selected_pair_label_distribution.md",
        selected_pair_exec_no_leakage,
        selected_pair_exec_dir / "no_leakage_selected_pair_execution_audit.md",
        selected_pair_exec_safety,
        selected_pair_exec_dir / "large_file_and_artifact_safety_check.md",
        selected_pair_exec_doc,
    ]
    existing_selected_pair_exec_required = [path for path in selected_pair_exec_required if path.exists()]
    if existing_selected_pair_exec_required:
        missing_selected_pair_exec_required = [path for path in selected_pair_exec_required if not path.exists()]
        if missing_selected_pair_exec_required:
            failures.append(
                "IEEE39 selected single-outage pilot pair execution artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_selected_pair_exec_required)
            )
        try:
            approval = _read_json_path(selected_pair_exec_approval)
            summary = _read_json_path(selected_pair_exec_summary)
            results = _read_json_path(selected_pair_exec_results)
            distribution = _read_json_path(selected_pair_exec_distribution)
            no_leakage = _read_json_path(selected_pair_exec_no_leakage)
            safety = _read_json_path(selected_pair_exec_safety)
            for key, expected in [
                ("approval_scope", "selected_single_outage_pilot_pair_execution_approval"),
                ("source_dry_run_commit", "07d4f7b3a6d40f4695312ff8c9b8e9704b2facac"),
                ("approved_pair_count", 32),
                ("approved_selected_pairs_only", True),
                ("full_1056_generation_approved", False),
                ("formal_label_export_approved", False),
                ("gcn_training_approved", False),
                ("reranker_retrain_approved", False),
                ("raw_trajectory_commit_approved", False),
                ("beta_rate_a_proxy_acknowledged", True),
                ("proxy_allowed_for_audit_only_prototype", True),
                ("proxy_allowed_for_production", False),
            ]:
                if approval.get(key) != expected:
                    failures.append(f"Selected pair execution approval must set {key}={expected!r}.")
            for key, expected in [
                ("execution_scope", "selected_single_outage_pilot_pair_execution"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("new_simulink_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_dry_run_commit", "07d4f7b3a6d40f4695312ff8c9b8e9704b2facac"),
                ("selected_pair_count", 32),
                ("executed_pair_count", 0),
                ("succeeded_pair_count", 0),
                ("failed_pair_count", 0),
                ("timeout_pair_count", 0),
                ("unknown_pair_count", 32),
                ("pilot_label_available_count", 0),
                ("pilot_positive_count", 0),
                ("pilot_negative_count", 0),
                ("pilot_unknown_count", 32),
                ("pilot_excluded_count", 0),
                ("raw_trajectories_committed", False),
                ("full_timeseries_committed", False),
                ("mat_files_committed", False),
                ("bus_fault_labels_used", False),
                ("line_trip_labels_first_priority", True),
                ("l12_special_case_preserved", True),
                ("nf06_warning_preserved", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("pilot_labels_are_formal_training_labels", False),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_export_formal_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
                (
                    "recommended_next_step",
                    "fix controlled execution environment or run selected pair execution locally, then rerun evidence collection",
                ),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Selected pair execution summary must set {key}={expected!r}.")
            if "controlled Simulink execution backend is not available" not in str(summary.get("blocker_if_any")):
                failures.append("Selected pair execution summary must record the controlled execution backend blocker.")
            if len(results) != summary.get("selected_pair_count"):
                failures.append("Selected pair execution results count must match selected_pair_count.")
            else:
                if any(row.get("execution_status") != "blocked" for row in results):
                    failures.append("Selected pair execution results must keep blocked rows blocked in this audit runner.")
                if any(row.get("pilot_label_value") is not None for row in results):
                    failures.append("Selected pair execution must not fabricate pilot_label_value.")
                if any(row.get("pilot_label_status") != "blocked" for row in results):
                    failures.append("Selected pair execution pilot_label_status must be blocked.")
                if any(row.get("bus_fault_label_used") is not False for row in results):
                    failures.append("Selected pair execution must not use bus-fault labels.")
                if any(row.get("l12_special_case_flag") is not False for row in results):
                    failures.append("Selected pair execution must preserve L12 exclusion.")
                if any(
                    "L12" in {row.get("prior_outaged_branch"), row.get("candidate_next_branch")}
                    for row in results
                ):
                    failures.append("Selected pair execution must not include L12 rows.")
            for key, expected in [
                ("selected_pair_count", 32),
                ("pilot_label_available_count", 0),
                ("pilot_positive_count", 0),
                ("pilot_negative_count", 0),
                ("pilot_unknown_count", 32),
                ("pilot_timeout_count", 0),
                ("pilot_failed_count", 0),
                ("pilot_blocked_count", 32),
                ("all_available_labels_negative", False),
                ("has_positive_pilot_label", False),
            ]:
                if distribution.get(key) != expected:
                    failures.append(f"Selected pair label distribution must set {key}={expected!r}.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("proxy_relay_threshold_used_only_in_feature_generation", True),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"Selected pair no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"Selected pair safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("Selected pair safety check must pass.")
            selected_pair_exec_text = "\n".join(
                [
                    _read_text("docs/ieee39_selected_single_outage_pilot_pair_execution.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md"),
                    _read_text("docs/ieee39_single_outage_label_loop_dry_run.md"),
                    _read_text("results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_summary.md"),
                    _read_text("results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_label_distribution.md"),
                    _read_text("results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/no_leakage_selected_pair_execution_audit.md"),
                ]
            ).lower()
            normalized_selected_pair_exec = " ".join(selected_pair_exec_text.replace("`", "").split())
            for required in [
                "selected 32 single-outage pilot pair execution",
                "does not train gcn",
                "does not rerun formal audit",
                "does not export formal labels",
                "does not retrain the reranker",
                "not full 1056 generation",
                "timeout, unknown, blocked, or failed cases are not converted to 0/1",
                "beta * rate_a",
                "audit-only proxy",
                "not a real relay setting",
                "bus-fault labels are not used",
                "l12 remains special/excluded",
                "nf06 warning is preserved",
                "pilot labels are not formal training labels",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_selected_pair_exec:
                    failures.append(f"Selected pair execution docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "formal labels exported",
                "full 1056 generation completed",
                "proxy is a real relay setting",
                "final engineering conclusion: true",
                "emt simulation",
                "generator_speed_proxy is direct frequency",
                "deployment ready",
            ]:
                if bad in normalized_selected_pair_exec:
                    failures.append(f"Selected pair execution docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read selected single-outage pilot pair execution artifacts: {exc}")

    backend_diag_dir = ROOT / "results/gcn_search/ieee39_controlled_execution_backend_diagnosis"
    backend_diag_summary = backend_diag_dir / "backend_readiness_summary.json"
    backend_diag_inventory = backend_diag_dir / "backend_component_inventory.json"
    backend_diag_mapping = backend_diag_dir / "selected_pair_execution_mapping_diagnosis.json"
    backend_diag_repair = backend_diag_dir / "safe_execution_repair_plan.json"
    backend_diag_no_leakage = backend_diag_dir / "no_leakage_backend_diagnosis_audit.json"
    backend_diag_safety = backend_diag_dir / "large_file_safety_backend_diagnosis.json"
    backend_diag_doc = ROOT / "docs/ieee39_controlled_execution_backend_diagnosis.md"
    backend_diag_required = [
        backend_diag_summary,
        backend_diag_dir / "backend_readiness_summary.md",
        backend_diag_dir / "backend_readiness_summary.csv",
        backend_diag_inventory,
        backend_diag_dir / "backend_component_inventory.md",
        backend_diag_mapping,
        backend_diag_dir / "selected_pair_execution_mapping_diagnosis.md",
        backend_diag_dir / "selected_pair_execution_mapping_diagnosis.csv",
        backend_diag_repair,
        backend_diag_dir / "safe_execution_repair_plan.md",
        backend_diag_no_leakage,
        backend_diag_dir / "no_leakage_backend_diagnosis_audit.md",
        backend_diag_safety,
        backend_diag_dir / "large_file_safety_backend_diagnosis.md",
        backend_diag_doc,
    ]
    existing_backend_diag_required = [path for path in backend_diag_required if path.exists()]
    if existing_backend_diag_required:
        missing_backend_diag_required = [path for path in backend_diag_required if not path.exists()]
        if missing_backend_diag_required:
            failures.append(
                "IEEE39 controlled execution backend diagnosis artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_backend_diag_required)
            )
        try:
            summary = _read_json_path(backend_diag_summary)
            inventory = _read_json_path(backend_diag_inventory)
            mapping = _read_json_path(backend_diag_mapping)
            repair = _read_json_path(backend_diag_repair)
            no_leakage = _read_json_path(backend_diag_no_leakage)
            safety = _read_json_path(backend_diag_safety)
            for key, expected in [
                ("diagnosis_scope", "controlled_execution_backend_diagnosis"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("simulink_run", False),
                ("selected_pairs_executed", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_execution_commit", "606eba793b3895c333ab0c632369bfadde413dca"),
                ("selected_pair_count", 32),
                ("ieee39_wrapper_model_found", True),
                ("selected_pair_mapping_found", True),
                ("two_step_line_trip_injection_supported", False),
                ("batch_runner_found", False),
                ("timeout_policy_found", True),
                ("result_parser_found", False),
                ("evidence_writer_found", True),
                ("safe_no_raw_artifact_policy_found", True),
                ("can_execute_selected_32_pairs_now", False),
                ("can_execute_without_full_1056", True),
                ("graceful_blocked_mode_available", True),
                (
                    "recommended_next_step",
                    "add a selected-32-only controlled execution backend or write local manual execution instructions before rerunning evidence collection",
                ),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Controlled execution backend diagnosis summary must set {key}={expected!r}.")
            if "missing approved two-step line-trip sequence injection" not in str(summary.get("blocker_if_any")):
                failures.append("Controlled execution backend diagnosis must record the selected-pair backend blocker.")
            for required_component in [
                "approved selected-pair two-step line-trip sequence injection",
                "selected-32-only batch runner",
                "selected-pair dynamic result parser contract",
            ]:
                if required_component not in inventory.get("missing_components", []):
                    failures.append(f"Backend inventory missing component diagnosis: {required_component}")
            if "IEEE39 wrapper model path" not in inventory.get("reusable_components", []):
                failures.append("Backend inventory must record the reusable IEEE39 wrapper model path.")
            if len(mapping) != summary.get("selected_pair_count"):
                failures.append("Backend mapping diagnosis count must match selected_pair_count.")
            else:
                if any(row.get("prior_branch_mapping_available") is not True for row in mapping):
                    failures.append("Backend mapping diagnosis must have prior branch mappings for selected pairs.")
                if any(row.get("next_branch_mapping_available") is not True for row in mapping):
                    failures.append("Backend mapping diagnosis must have next branch mappings for selected pairs.")
                if any(row.get("sequence_injection_supported") is not False for row in mapping):
                    failures.append("Backend mapping diagnosis must not claim sequence injection support.")
                if any(row.get("execution_ready") is not False for row in mapping):
                    failures.append("Backend mapping diagnosis must not mark rows execution ready.")
                if any(row.get("l12_special_case_flag") is not False for row in mapping):
                    failures.append("Backend mapping diagnosis must preserve L12 exclusion.")
            if repair.get("repair_plan_scope") != "controlled_execution_backend_repair_plan":
                failures.append("Backend repair plan must use controlled_execution_backend_repair_plan scope.")
            if repair.get("manual_approval_required_before_execution") is not True:
                failures.append("Backend repair plan must require manual approval before execution.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_future_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("proxy_relay_threshold_used_only_in_feature_generation", True),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"Backend no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"Backend large-file safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("Backend large-file safety check must pass.")
            backend_diag_text = "\n".join(
                [
                    _read_text("docs/ieee39_controlled_execution_backend_diagnosis.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_selected_single_outage_pilot_pair_execution.md"),
                    _read_text("docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md"),
                    _read_text("results/gcn_search/ieee39_controlled_execution_backend_diagnosis/backend_readiness_summary.md"),
                    _read_text("results/gcn_search/ieee39_controlled_execution_backend_diagnosis/safe_execution_repair_plan.md"),
                    _read_text("results/gcn_search/ieee39_controlled_execution_backend_diagnosis/no_leakage_backend_diagnosis_audit.md"),
                ]
            ).lower()
            normalized_backend_diag = " ".join(backend_diag_text.replace("`", "").split())
            for required in [
                "controlled execution backend diagnosis",
                "does not train gcn",
                "does not rerun formal audit",
                "does not execute selected 32 pairs",
                "does not run full 1056 generation",
                "does not export formal labels",
                "does not retrain the reranker",
                "selected pair execution was blocked",
                "controlled simulink execution backend",
                "beta * rate_a",
                "audit-only proxy",
                "not a real relay setting",
                "bus-fault labels are not used",
                "l12 remains special/excluded",
                "nf06 warning is preserved",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_backend_diag:
                    failures.append(f"Controlled execution backend diagnosis docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "selected 32 pairs executed",
                "full 1056 generation completed",
                "formal labels exported",
                "proxy is a real relay setting",
                "final engineering conclusion: true",
                "emt simulation",
                "generator_speed_proxy is direct frequency",
                "deployment ready",
            ]:
                if bad in normalized_backend_diag:
                    failures.append(f"Controlled execution backend diagnosis docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read controlled execution backend diagnosis artifacts: {exc}")

    backend_repair_dir = ROOT / "results/gcn_search/ieee39_controlled_execution_backend_repair"
    backend_repair_summary = backend_repair_dir / "backend_repair_summary.json"
    backend_repair_contract = backend_repair_dir / "backend_execution_contract.json"
    backend_repair_matrix = backend_repair_dir / "selected_pair_backend_readiness_matrix.json"
    backend_repair_no_leakage = backend_repair_dir / "no_leakage_backend_repair_audit.json"
    backend_repair_safety = backend_repair_dir / "large_file_safety_backend_repair.json"
    backend_repair_doc = ROOT / "docs/ieee39_controlled_execution_backend_repair.md"
    backend_repair_required = [
        backend_repair_summary,
        backend_repair_dir / "backend_repair_summary.md",
        backend_repair_dir / "backend_repair_summary.csv",
        backend_repair_contract,
        backend_repair_dir / "backend_execution_contract.md",
        backend_repair_dir / "manual_execution_instruction_pack.md",
        backend_repair_matrix,
        backend_repair_dir / "selected_pair_backend_readiness_matrix.md",
        backend_repair_dir / "selected_pair_backend_readiness_matrix.csv",
        backend_repair_no_leakage,
        backend_repair_dir / "no_leakage_backend_repair_audit.md",
        backend_repair_safety,
        backend_repair_dir / "large_file_safety_backend_repair.md",
        backend_repair_doc,
        ROOT / "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
        ROOT / "scripts/gcn_search/parse_ieee39_selected_pair_execution_evidence.py",
        ROOT / "matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m",
    ]
    existing_backend_repair_required = [path for path in backend_repair_required if path.exists()]
    if existing_backend_repair_required:
        missing_backend_repair_required = [path for path in backend_repair_required if not path.exists()]
        if missing_backend_repair_required:
            failures.append(
                "IEEE39 controlled execution backend repair artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_backend_repair_required)
            )
        try:
            summary = _read_json_path(backend_repair_summary)
            contract = _read_json_path(backend_repair_contract)
            matrix = _read_json_path(backend_repair_matrix)
            no_leakage = _read_json_path(backend_repair_no_leakage)
            safety = _read_json_path(backend_repair_safety)
            for key, expected in [
                ("repair_scope", "controlled_execution_backend_repair"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("selected_pairs_executed", False),
                ("simulink_run", False),
                ("full_1056_generation_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_backend_diagnosis_commit", "0d96b0c258e23f4fe5c2ec01cac2a63b5d85c06f"),
                ("selected_pair_count", 32),
                ("python_runner_added", True),
                ("matlab_entrypoint_added", True),
                ("result_parser_contract_added", True),
                ("evidence_writer_added", True),
                ("manual_instruction_pack_added", True),
                ("selected_32_only_guard_added", True),
                ("full_1056_guard_added", True),
                ("no_formal_label_export_guard_added", True),
                ("no_training_guard_added", True),
                ("no_raw_artifact_policy_added", True),
                ("graceful_blocked_mode_available", True),
                ("can_execute_selected_32_pairs_after_manual_approval", True),
                ("can_execute_selected_32_pairs_now", False),
                ("recommended_next_step", "approve execution of selected 32 pairs using the repaired backend in a separate round"),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Controlled execution backend repair summary must set {key}={expected!r}.")
            if "manual approval" not in str(summary.get("blocker_if_any")):
                failures.append("Controlled execution backend repair summary must require manual approval.")
            for key, expected in [
                ("contract_scope", "selected_pair_execution_contract"),
                ("allowed_pair_count", 32),
                ("full_1056_generation_allowed", False),
                ("requires_approved_selected_pairs_only", True),
                ("requires_explicit_execute_flag", True),
                ("default_mode", "dry_run_or_blocked"),
                ("formal_label_export_policy", False),
            ]:
                if contract.get(key) != expected:
                    failures.append(f"Backend execution contract must set {key}={expected!r}.")
            if len(matrix) != summary.get("selected_pair_count"):
                failures.append("Backend repair readiness matrix count must match selected_pair_count.")
            else:
                for key in [
                    "mapping_ready",
                    "selected_32_guard_passed",
                    "execution_contract_ready",
                    "matlab_entrypoint_ready",
                    "parser_contract_ready",
                    "future_execution_ready",
                ]:
                    if any(row.get(key) is not True for row in matrix):
                        failures.append(f"Backend repair readiness matrix must set {key}=true for selected rows.")
                if any(row.get("l12_special_case_flag") is not False for row in matrix):
                    failures.append("Backend repair readiness matrix must preserve L12 exclusion.")
                if any(row.get("current_status") != "ready_for_manual_approval" for row in matrix):
                    failures.append("Backend repair readiness matrix rows must be ready_for_manual_approval.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_future_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("proxy_relay_threshold_used_only_in_feature_generation", True),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"Backend repair no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"Backend repair large-file safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("Backend repair large-file safety check must pass.")
            backend_repair_text = "\n".join(
                [
                    _read_text("docs/ieee39_controlled_execution_backend_repair.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_controlled_execution_backend_diagnosis.md"),
                    _read_text("docs/ieee39_selected_single_outage_pilot_pair_execution.md"),
                    _read_text("results/gcn_search/ieee39_controlled_execution_backend_repair/backend_repair_summary.md"),
                    _read_text("results/gcn_search/ieee39_controlled_execution_backend_repair/backend_execution_contract.md"),
                    _read_text("results/gcn_search/ieee39_controlled_execution_backend_repair/manual_execution_instruction_pack.md"),
                ]
            ).lower()
            normalized_backend_repair = " ".join(backend_repair_text.replace("`", "").split())
            for required in [
                "controlled execution backend repair",
                "does not train gcn",
                "does not rerun formal audit",
                "does not execute selected 32 pairs",
                "does not run full 1056 generation",
                "does not export formal labels",
                "does not retrain the reranker",
                "selected-32-only python runner",
                "matlab two-step line-trip entrypoint skeleton",
                "result parser contract",
                "manual instruction pack",
                "raw trajectory, full timeseries, or .mat",
                "beta * rate_a",
                "audit-only proxy",
                "not a real relay setting",
                "bus-fault labels are not used",
                "l12 remains special/excluded",
                "nf06 warning is preserved",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_backend_repair:
                    failures.append(f"Controlled execution backend repair docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "selected 32 pairs executed",
                "full 1056 generation completed",
                "formal labels exported",
                "proxy is a real relay setting",
                "emt simulation",
                "generator_speed_proxy is direct frequency",
                "deployment ready",
            ]:
                if bad in normalized_backend_repair:
                    failures.append(f"Controlled execution backend repair docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read controlled execution backend repair artifacts: {exc}")

    selected_32_dir = ROOT / "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence"
    selected_32_doc = ROOT / "docs/ieee39_selected_32_pair_controlled_execution_evidence.md"
    selected_32_summary = selected_32_dir / "selected_32_execution_summary.json"
    selected_32_approval = selected_32_dir / "selected_32_execution_approval.json"
    selected_32_results = selected_32_dir / "selected_32_execution_results.json"
    selected_32_distribution = selected_32_dir / "selected_32_label_distribution.json"
    selected_32_no_leakage = selected_32_dir / "no_leakage_selected_32_execution_audit.json"
    selected_32_safety = selected_32_dir / "large_file_safety_selected_32_execution.json"
    selected_32_required = [
        selected_32_doc,
        selected_32_approval,
        selected_32_dir / "selected_32_execution_approval.md",
        selected_32_summary,
        selected_32_dir / "selected_32_execution_summary.md",
        selected_32_dir / "selected_32_execution_summary.csv",
        selected_32_results,
        selected_32_dir / "selected_32_execution_results.md",
        selected_32_dir / "selected_32_execution_results.csv",
        selected_32_distribution,
        selected_32_dir / "selected_32_label_distribution.md",
        selected_32_no_leakage,
        selected_32_dir / "no_leakage_selected_32_execution_audit.md",
        selected_32_safety,
        selected_32_dir / "large_file_safety_selected_32_execution.md",
    ]
    existing_selected_32_required = [path for path in selected_32_required if path.exists()]
    if existing_selected_32_required:
        missing_selected_32_required = [path for path in selected_32_required if not path.exists()]
        if missing_selected_32_required:
            failures.append(
                "IEEE39 selected 32 controlled execution evidence artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_selected_32_required)
            )
        try:
            approval = _read_json_path(selected_32_approval)
            summary = _read_json_path(selected_32_summary)
            results = _read_json_path(selected_32_results)
            distribution = _read_json_path(selected_32_distribution)
            no_leakage = _read_json_path(selected_32_no_leakage)
            safety = _read_json_path(selected_32_safety)
            for key, expected in [
                ("approval_scope", "selected_32_controlled_execution_approval"),
                ("source_backend_repair_commit", "5c15cf88c3d980e3491d7327602a4d318216f2e4"),
                ("approved_selected_pairs_only", True),
                ("approved_pair_count", 32),
                ("full_1056_generation_approved", False),
                ("formal_label_export_approved", False),
                ("gcn_training_approved", False),
                ("reranker_retrain_approved", False),
                ("raw_trajectory_commit_approved", False),
                ("explicit_execute_required", True),
                ("beta_rate_a_proxy_acknowledged", True),
                ("proxy_allowed_for_audit_only_prototype", True),
                ("proxy_allowed_for_production", False),
            ]:
                if approval.get(key) != expected:
                    failures.append(f"Selected 32 approval must set {key}={expected!r}.")
            for key, expected in [
                ("execution_scope", "selected_32_controlled_execution_evidence"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("full_1056_generation_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_backend_repair_commit", "5c15cf88c3d980e3491d7327602a4d318216f2e4"),
                ("selected_pair_count", 32),
                ("pilot_label_available_count", 0),
                ("pilot_positive_count", 0),
                ("pilot_negative_count", 0),
                ("pilot_unknown_count", 32),
                ("pilot_blocked_count", 32),
                ("has_positive_pilot_label", False),
                ("raw_trajectories_committed", False),
                ("full_timeseries_committed", False),
                ("mat_files_committed", False),
                ("slx_files_committed", False),
                ("slxc_files_committed", False),
                ("slprj_committed", False),
                ("bus_fault_labels_used", False),
                ("line_trip_labels_first_priority", True),
                ("l12_special_case_preserved", True),
                ("nf06_warning_preserved", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("pilot_labels_are_formal_training_labels", False),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_export_formal_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"Selected 32 execution summary must set {key}={expected!r}.")
            if summary.get("blocked_pair_count") != 32:
                failures.append("Selected 32 execution summary must record blocked_pair_count=32 for skeleton execution.")
            if summary.get("executed_pair_count") != 0:
                failures.append("Selected 32 execution summary must record executed_pair_count=0 when the backend is skeleton-blocked.")
            if "guarded skeleton" not in str(summary.get("blocker_if_any", "")).lower():
                failures.append("Selected 32 execution summary must explain the guarded skeleton blocker.")
            if len(results) != 32:
                failures.append("Selected 32 execution results must contain 32 rows.")
            for row in results:
                if row.get("execution_status") != "blocked":
                    failures.append("Selected 32 execution rows must remain blocked unless real compact evidence exists.")
                    break
                if row.get("pilot_label_value") is not None:
                    failures.append("Selected 32 blocked rows must keep pilot_label_value=null.")
                    break
                if row.get("pilot_label_status") != "blocked":
                    failures.append("Selected 32 blocked rows must keep pilot_label_status=blocked.")
                    break
                for artifact_key in ["raw_trajectory_committed", "full_timeseries_committed", "mat_file_committed", "bus_fault_label_used"]:
                    if row.get(artifact_key) is not False:
                        failures.append(f"Selected 32 row must keep {artifact_key}=false.")
                        break
            for key, expected in [
                ("selected_pair_count", 32),
                ("pilot_label_available_count", 0),
                ("pilot_positive_count", 0),
                ("pilot_negative_count", 0),
                ("pilot_unknown_count", 32),
                ("pilot_blocked_count", 32),
                ("has_positive_pilot_label", False),
            ]:
                if distribution.get(key) != expected:
                    failures.append(f"Selected 32 label distribution must set {key}={expected!r}.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("proxy_relay_threshold_used_only_in_feature_generation", True),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"Selected 32 no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"Selected 32 large-file safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("Selected 32 large-file safety check must pass.")
            selected_32_text = "\n".join(
                [
                    _read_text("docs/ieee39_selected_32_pair_controlled_execution_evidence.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_controlled_execution_backend_repair.md"),
                    _read_text("docs/ieee39_selected_single_outage_pilot_pair_execution.md"),
                    _read_text("results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_summary.md"),
                    _read_text("results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_results.md"),
                ]
            ).lower()
            normalized_selected_32 = " ".join(selected_32_text.replace("`", "").split())
            for required in [
                "selected 32 pair controlled execution evidence",
                "does not train gcn",
                "does not rerun formal audit",
                "does not run full 1056 generation",
                "does not export formal labels",
                "does not retrain the reranker",
                "only selected 32 pairs",
                "compact blocked evidence",
                "raw trajectories",
                "full timeseries",
                "blocked, and unknown results are not converted to 0/1",
                "beta * rate_a",
                "audit-only proxy",
                "not a real relay setting",
                "bus-fault labels are not used",
                "l12 remains special/excluded",
                "nf06 warning is preserved",
                "pilot labels are not formal training labels",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_selected_32:
                    failures.append(f"Selected 32 execution docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "full 1056 generation completed",
                "formal labels exported",
                "proxy is a real relay setting",
                "emt simulation",
                "generator_speed_proxy is direct frequency",
                "final engineering conclusion",
                "deployment ready",
            ]:
                if bad in normalized_selected_32:
                    failures.append(f"Selected 32 execution docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read selected 32 controlled execution evidence artifacts: {exc}")

    entrypoint_repair_dir = ROOT / "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair"
    entrypoint_repair_doc = ROOT / "docs/ieee39_matlab_selected_pair_entrypoint_repair.md"
    entrypoint_repair_summary = entrypoint_repair_dir / "matlab_entrypoint_repair_summary.json"
    entrypoint_repair_contract = entrypoint_repair_dir / "single_pair_smoke_execution_contract.json"
    entrypoint_repair_reuse = entrypoint_repair_dir / "entrypoint_component_reuse_report.json"
    entrypoint_repair_candidate = entrypoint_repair_dir / "single_pair_smoke_candidate.json"
    entrypoint_repair_no_leakage = entrypoint_repair_dir / "no_leakage_entrypoint_repair_audit.json"
    entrypoint_repair_safety = entrypoint_repair_dir / "large_file_safety_entrypoint_repair.json"
    entrypoint_repair_required = [
        entrypoint_repair_doc,
        entrypoint_repair_summary,
        entrypoint_repair_dir / "matlab_entrypoint_repair_summary.md",
        entrypoint_repair_dir / "matlab_entrypoint_repair_summary.csv",
        entrypoint_repair_contract,
        entrypoint_repair_dir / "single_pair_smoke_execution_contract.md",
        entrypoint_repair_reuse,
        entrypoint_repair_dir / "entrypoint_component_reuse_report.md",
        entrypoint_repair_candidate,
        entrypoint_repair_dir / "single_pair_smoke_candidate.md",
        entrypoint_repair_no_leakage,
        entrypoint_repair_dir / "no_leakage_entrypoint_repair_audit.md",
        entrypoint_repair_safety,
        entrypoint_repair_dir / "large_file_safety_entrypoint_repair.md",
    ]
    existing_entrypoint_repair_required = [path for path in entrypoint_repair_required if path.exists()]
    if existing_entrypoint_repair_required:
        missing_entrypoint_repair_required = [path for path in entrypoint_repair_required if not path.exists()]
        if missing_entrypoint_repair_required:
            failures.append(
                "IEEE39 MATLAB selected-pair entrypoint repair artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_entrypoint_repair_required)
            )
        try:
            summary = _read_json_path(entrypoint_repair_summary)
            contract = _read_json_path(entrypoint_repair_contract)
            reuse = _read_json_path(entrypoint_repair_reuse)
            candidate = _read_json_path(entrypoint_repair_candidate)
            no_leakage = _read_json_path(entrypoint_repair_no_leakage)
            safety = _read_json_path(entrypoint_repair_safety)
            for key, expected in [
                ("repair_scope", "matlab_selected_pair_entrypoint_repair"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("selected_32_pairs_executed", False),
                ("full_1056_generation_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_selected_32_evidence_commit", "12f07cbc4d3b35883b1dd11078c87029d5df8aac"),
                ("matlab_entrypoint_updated", True),
                ("python_runner_updated", True),
                ("parser_contract_updated", True),
                ("selected_32_guard_preserved", True),
                ("single_pair_smoke_mode_added", True),
                ("batch_32_execution_allowed_now", False),
                ("full_1056_execution_allowed_now", False),
                ("can_attempt_single_pair_smoke_after_manual_approval", True),
                ("can_attempt_selected_32_after_single_pair_smoke", False),
                ("raw_trajectory_policy_preserved", True),
                ("formal_label_export_guard_preserved", True),
                ("no_training_guard_preserved", True),
                ("recommended_next_step", "approve one selected pair smoke execution in a separate round"),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"MATLAB selected-pair entrypoint repair summary must set {key}={expected!r}.")
            if "separate manual approval" not in str(summary.get("blocker_if_any", "")).lower():
                failures.append("MATLAB selected-pair entrypoint repair summary must require separate manual approval.")
            for key, expected in [
                ("contract_scope", "single_pair_smoke_execution_contract"),
                ("allowed_pair_count", 1),
                ("selected_32_batch_execution_allowed", False),
                ("full_1056_generation_allowed", False),
                ("requires_manual_approval", True),
                ("requires_explicit_execute", True),
                ("compact_evidence_only", True),
            ]:
                if contract.get(key) != expected:
                    failures.append(f"Single-pair smoke contract must set {key}={expected!r}.")
            if candidate.get("approved_for_execution_now") is not False:
                failures.append("Single-pair smoke candidate must not be approved for execution now.")
            if candidate.get("requires_next_round_approval") is not True:
                failures.append("Single-pair smoke candidate must require next-round approval.")
            if candidate.get("l12_special_case_flag") is not False:
                failures.append("Single-pair smoke candidate must preserve L12 exclusion.")
            if reuse.get("source_slx_modified") is not False:
                failures.append("Entrypoint reuse report must set source_slx_modified=false.")
            if not reuse.get("reused_matlab_components"):
                failures.append("Entrypoint reuse report must list reused MATLAB components.")
            if not reuse.get("reused_python_components"):
                failures.append("Entrypoint reuse report must list reused Python components.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_future_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("proxy_relay_threshold_used_only_in_feature_generation", True),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"Entrypoint repair no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "source_slx_modified",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"Entrypoint repair large-file safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("Entrypoint repair large-file safety check must pass.")
            matlab_entrypoint_text = _read_text("matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m").lower()
            for required in ["execute_single_pair", "dry_run_only", "pair_id", "batch execution is refused"]:
                if required not in matlab_entrypoint_text:
                    failures.append(f"MATLAB selected-pair entrypoint missing guard text: {required}")
            entrypoint_repair_text = "\n".join(
                [
                    _read_text("docs/ieee39_matlab_selected_pair_entrypoint_repair.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_selected_32_pair_controlled_execution_evidence.md"),
                    _read_text("docs/ieee39_controlled_execution_backend_repair.md"),
                    _read_text("results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/matlab_entrypoint_repair_summary.md"),
                    _read_text("results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/single_pair_smoke_execution_contract.md"),
                ]
            ).lower()
            normalized_entrypoint_repair = " ".join(entrypoint_repair_text.replace("`", "").split())
            for required in [
                "matlab selected-pair entrypoint repair",
                "does not train gcn",
                "does not rerun formal audit",
                "does not execute selected 32 pairs",
                "does not run full 1056 generation",
                "does not export formal labels",
                "does not retrain the reranker",
                "single-pair smoke",
                "at most one selected pair",
                "raw trajectory",
                "full timeseries",
                "source .slx",
                "beta * rate_a",
                "audit-only proxy",
                "not a real relay setting",
                "bus-fault labels are not used",
                "l12 remains special/excluded",
                "nf06 warning is preserved",
                "pilot labels are not formal training labels",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_entrypoint_repair:
                    failures.append(f"MATLAB selected-pair entrypoint repair docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal audit rerun completed",
                "selected 32 pairs executed",
                "full 1056 generation completed",
                "formal labels exported",
                "proxy is a real relay setting",
                "emt simulation",
                "generator_speed_proxy is direct frequency",
                "final engineering conclusion",
                "deployment ready",
            ]:
                if bad in normalized_entrypoint_repair:
                    failures.append(f"MATLAB selected-pair entrypoint repair docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read MATLAB selected-pair entrypoint repair artifacts: {exc}")

    spp001_dir = ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_execution"
    spp001_doc = ROOT / "docs/ieee39_spp001_single_pair_smoke_execution.md"
    spp001_approval = spp001_dir / "spp001_smoke_execution_approval.json"
    spp001_summary = spp001_dir / "spp001_smoke_execution_summary.json"
    spp001_result = spp001_dir / "spp001_smoke_execution_result.json"
    spp001_no_leakage = spp001_dir / "spp001_no_leakage_smoke_audit.json"
    spp001_safety = spp001_dir / "spp001_large_file_safety_check.json"
    spp001_required = [
        spp001_doc,
        spp001_approval,
        spp001_dir / "spp001_smoke_execution_approval.md",
        spp001_summary,
        spp001_dir / "spp001_smoke_execution_summary.md",
        spp001_dir / "spp001_smoke_execution_summary.csv",
        spp001_result,
        spp001_dir / "spp001_smoke_execution_result.md",
        spp001_dir / "spp001_smoke_execution_result.csv",
        spp001_no_leakage,
        spp001_dir / "spp001_no_leakage_smoke_audit.md",
        spp001_safety,
        spp001_dir / "spp001_large_file_safety_check.md",
    ]
    existing_spp001_required = [path for path in spp001_required if path.exists()]
    if existing_spp001_required:
        missing_spp001_required = [path for path in spp001_required if not path.exists()]
        if missing_spp001_required:
            failures.append(
                "IEEE39 SPP001 single-pair smoke artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_spp001_required)
            )
        try:
            approval = _read_json_path(spp001_approval)
            summary = _read_json_path(spp001_summary)
            result = _read_json_path(spp001_result)
            no_leakage = _read_json_path(spp001_no_leakage)
            safety = _read_json_path(spp001_safety)
            for key, expected in [
                ("approval_scope", "spp001_single_pair_smoke_execution_approval"),
                ("approved_selected_pairs_only", True),
                ("approved_pair_count", 1),
                ("pair_id", "SPP001"),
                ("prior_outaged_branch", "L15"),
                ("candidate_next_branch", "L04"),
                ("source_entrypoint_repair_commit", "4a8284da5ec80d91c30fe814c9823af157e37fe9"),
                ("selected_32_batch_execution_approved", False),
                ("full_1056_generation_approved", False),
                ("formal_label_export_approved", False),
                ("gcn_training_approved", False),
                ("reranker_retrain_approved", False),
                ("production_model_approved", False),
            ]:
                if approval.get(key) != expected:
                    failures.append(f"SPP001 approval must set {key}={expected!r}.")
            for key, expected in [
                ("execution_scope", "spp001_single_pair_smoke_execution"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("selected_32_batch_executed", False),
                ("full_1056_generation_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_entrypoint_repair_commit", "4a8284da5ec80d91c30fe814c9823af157e37fe9"),
                ("pair_id", "SPP001"),
                ("state_id", "single_outage_state_L15"),
                ("prior_outaged_branch", "L15"),
                ("candidate_next_branch", "L04"),
                ("selection_bucket", "high_relay_ratio_pairs"),
                ("execution_attempted", True),
                ("pilot_labels_are_formal_training_labels", False),
                ("source_slx_modified", False),
                ("bus_fault_labels_used", False),
                ("line_trip_labels_first_priority", True),
                ("l12_special_case_preserved", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_export_formal_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"SPP001 summary must set {key}={expected!r}.")
            if summary.get("execution_status") not in {"succeeded", "failed", "timeout", "blocked"}:
                failures.append("SPP001 summary execution_status must be succeeded/failed/timeout/blocked.")
            if summary.get("pilot_label_value") not in {0, 1, None}:
                failures.append("SPP001 pilot_label_value must be 0, 1, or null.")
            if summary.get("execution_status") != "succeeded" and summary.get("pilot_label_value") is not None:
                failures.append("SPP001 non-succeeded result must not fabricate a pilot label.")
            if result.get("pair_id") != "SPP001":
                failures.append("SPP001 result must be for SPP001.")
            if result.get("prior_outaged_branch") != "L15" or result.get("candidate_next_branch") != "L04":
                failures.append("SPP001 result must preserve L15 -> L04.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_future_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("bus_fault_labels_used", False),
                ("line_trip_labels_first_priority", True),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"SPP001 no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "source_slx_modified",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"SPP001 safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("SPP001 large-file safety check must pass.")
            spp001_text = "\n".join(
                [
                    _read_text("docs/ieee39_spp001_single_pair_smoke_execution.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_summary.md"),
                    _read_text("results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_result.md"),
                ]
            ).lower()
            normalized_spp001 = " ".join(spp001_text.replace("`", "").split())
            for required in [
                "spp001 single-pair smoke execution",
                "does not train gcn",
                "does not rerun formal audit",
                "does not execute the selected 32 batch",
                "does not run full 1056 generation",
                "does not export formal labels",
                "does not retrain the reranker",
                "l15 -> l04",
                "pilot labels are not formal training labels",
                "not a final project conclusion",
                "bus-fault labels are not used",
                "line-trip labels remain first priority",
                "l12 remains special/excluded",
                "raw trajectories",
                "full timeseries",
            ]:
                if required not in normalized_spp001:
                    failures.append(f"SPP001 docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal labels exported",
                "selected 32 batch executed",
                "full 1056 generation completed",
                "deployment ready",
            ]:
                if bad in normalized_spp001:
                    failures.append(f"SPP001 docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read SPP001 single-pair smoke artifacts: {exc}")

    spp001_rerun_dir = ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_rerun"
    spp001_rerun_doc = ROOT / "docs/ieee39_spp001_single_pair_smoke_rerun.md"
    spp001_rerun_approval = spp001_rerun_dir / "spp001_rerun_approval.json"
    spp001_rerun_summary = spp001_rerun_dir / "spp001_rerun_summary.json"
    spp001_rerun_result = spp001_rerun_dir / "spp001_rerun_result.json"
    spp001_rerun_distribution = spp001_rerun_dir / "spp001_rerun_label_distribution.json"
    spp001_rerun_no_leakage = spp001_rerun_dir / "spp001_no_leakage_rerun_audit.json"
    spp001_rerun_safety = spp001_rerun_dir / "spp001_large_file_safety_rerun.json"
    spp001_rerun_required = [
        spp001_rerun_doc,
        spp001_rerun_approval,
        spp001_rerun_dir / "spp001_rerun_approval.md",
        spp001_rerun_summary,
        spp001_rerun_dir / "spp001_rerun_summary.md",
        spp001_rerun_dir / "spp001_rerun_summary.csv",
        spp001_rerun_result,
        spp001_rerun_dir / "spp001_rerun_result.md",
        spp001_rerun_dir / "spp001_rerun_result.csv",
        spp001_rerun_distribution,
        spp001_rerun_dir / "spp001_rerun_label_distribution.md",
        spp001_rerun_no_leakage,
        spp001_rerun_dir / "spp001_no_leakage_rerun_audit.md",
        spp001_rerun_safety,
        spp001_rerun_dir / "spp001_large_file_safety_rerun.md",
    ]
    existing_spp001_rerun_required = [path for path in spp001_rerun_required if path.exists()]
    if existing_spp001_rerun_required:
        missing_spp001_rerun_required = [path for path in spp001_rerun_required if not path.exists()]
        if missing_spp001_rerun_required:
            failures.append(
                "IEEE39 SPP001 rerun artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_spp001_rerun_required)
            )
        try:
            approval = _read_json_path(spp001_rerun_approval)
            summary = _read_json_path(spp001_rerun_summary)
            result = _read_json_path(spp001_rerun_result)
            distribution = _read_json_path(spp001_rerun_distribution)
            no_leakage = _read_json_path(spp001_rerun_no_leakage)
            safety = _read_json_path(spp001_rerun_safety)
            for key, expected in [
                ("approval_scope", "spp001_single_pair_smoke_rerun_approval"),
                ("approved_selected_pairs_only", True),
                ("approved_pair_count", 1),
                ("pair_id", "SPP001"),
                ("prior_outaged_branch", "L15"),
                ("candidate_next_branch", "L04"),
                ("source_l15_readiness_repair_commit", "a648b8cb2d4fb3a4c27a5e7f3e8e588280ddc0d1"),
                ("selected_32_batch_execution_approved", False),
                ("full_1056_generation_approved", False),
                ("formal_label_export_approved", False),
                ("gcn_training_approved", False),
                ("reranker_retrain_approved", False),
                ("production_model_approved", False),
            ]:
                if approval.get(key) != expected:
                    failures.append(f"SPP001 rerun approval must set {key}={expected!r}.")
            for key, expected in [
                ("execution_scope", "spp001_single_pair_smoke_rerun"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("selected_32_batch_executed", False),
                ("full_1056_generation_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_l15_readiness_repair_commit", "a648b8cb2d4fb3a4c27a5e7f3e8e588280ddc0d1"),
                ("pair_id", "SPP001"),
                ("state_id", "single_outage_state_L15"),
                ("prior_outaged_branch", "L15"),
                ("candidate_next_branch", "L04"),
                ("selection_bucket", "high_relay_ratio_pairs"),
                ("l15_ready", True),
                ("l04_ready", True),
                ("execution_attempted", True),
                ("single_pair_executed", summary.get("execution_status") == "succeeded"),
                ("simulink_run", summary.get("execution_status") == "succeeded"),
                ("pilot_labels_are_formal_training_labels", False),
                ("source_slx_modified", False),
                ("bus_fault_labels_used", False),
                ("line_trip_labels_first_priority", True),
                ("l12_special_case_preserved", True),
                ("nf06_warning_preserved", True),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_export_formal_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"SPP001 rerun summary must set {key}={expected!r}.")
            if summary.get("execution_status") not in {"succeeded", "failed", "timeout", "blocked"}:
                failures.append("SPP001 rerun execution_status must be succeeded/failed/timeout/blocked.")
            if summary.get("pilot_label_value") not in {0, 1, None}:
                failures.append("SPP001 rerun pilot_label_value must be 0, 1, or null.")
            if summary.get("execution_status") != "succeeded" and summary.get("pilot_label_value") is not None:
                failures.append("SPP001 rerun non-succeeded result must not fabricate a pilot label.")
            if result.get("pair_id") != "SPP001":
                failures.append("SPP001 rerun result must be for SPP001.")
            if result.get("prior_outaged_branch") != "L15" or result.get("candidate_next_branch") != "L04":
                failures.append("SPP001 rerun result must preserve L15 -> L04.")
            if distribution.get("pair_count") != 1 or distribution.get("formal_training_labels") is not False:
                failures.append("SPP001 rerun label distribution must be one pilot-only row.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_future_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("bus_fault_labels_used", False),
                ("line_trip_labels_first_priority", True),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"SPP001 rerun no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "source_slx_modified",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"SPP001 rerun safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("SPP001 rerun large-file safety check must pass.")
            rerun_text = "\n".join(
                [
                    _read_text("docs/ieee39_spp001_single_pair_smoke_rerun.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_rerun_summary.md"),
                    _read_text("results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_rerun_result.md"),
                ]
            ).lower()
            normalized_rerun = " ".join(rerun_text.replace("`", "").split())
            for required in [
                "spp001 single-pair smoke rerun",
                "does not train gcn",
                "does not rerun formal audit",
                "does not execute the selected 32 batch",
                "does not run full 1056 generation",
                "does not export formal labels",
                "does not retrain the reranker",
                "l15 -> l04",
                "pilot labels are not formal training labels",
                "not a final project conclusion",
                "bus-fault labels are not used",
                "line-trip labels remain first priority",
                "l12 remains special/excluded",
                "raw trajectories",
                "full timeseries",
            ]:
                if required not in normalized_rerun:
                    failures.append(f"SPP001 rerun docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "formal labels exported",
                "selected 32 batch executed",
                "full 1056 generation completed",
                "deployment ready",
            ]:
                if bad in normalized_rerun:
                    failures.append(f"SPP001 rerun docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read SPP001 rerun artifacts: {exc}")

    spp001_bridge_dir = ROOT / "results/gcn_search/ieee39_spp001_model_provenance_bridge_repair"
    spp001_bridge_doc = ROOT / "docs/ieee39_spp001_model_provenance_bridge_repair.md"
    spp001_bridge_summary = spp001_bridge_dir / "spp001_provenance_bridge_repair_summary.json"
    spp001_bridge_inventory = spp001_bridge_dir / "spp001_trip_command_provenance_inventory.json"
    spp001_bridge_manifest = spp001_bridge_dir / "spp001_repaired_provenance_manifest.json"
    spp001_bridge_gate = spp001_bridge_dir / "spp001_rerun_provenance_gate.json"
    spp001_bridge_no_leakage = spp001_bridge_dir / "no_leakage_spp001_provenance_bridge_audit.json"
    spp001_bridge_safety = spp001_bridge_dir / "large_file_safety_spp001_provenance_bridge.json"
    spp001_bridge_required = [
        spp001_bridge_doc,
        spp001_bridge_summary,
        spp001_bridge_dir / "spp001_provenance_bridge_repair_summary.md",
        spp001_bridge_dir / "spp001_provenance_bridge_repair_summary.csv",
        spp001_bridge_inventory,
        spp001_bridge_dir / "spp001_trip_command_provenance_inventory.md",
        spp001_bridge_manifest,
        spp001_bridge_dir / "spp001_repaired_provenance_manifest.md",
        spp001_bridge_gate,
        spp001_bridge_dir / "spp001_rerun_provenance_gate.md",
        spp001_bridge_no_leakage,
        spp001_bridge_dir / "no_leakage_spp001_provenance_bridge_audit.md",
        spp001_bridge_safety,
        spp001_bridge_dir / "large_file_safety_spp001_provenance_bridge.md",
    ]
    existing_spp001_bridge_required = [path for path in spp001_bridge_required if path.exists()]
    if existing_spp001_bridge_required:
        missing_spp001_bridge_required = [path for path in spp001_bridge_required if not path.exists()]
        if missing_spp001_bridge_required:
            failures.append(
                "IEEE39 SPP001 model provenance bridge repair artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_spp001_bridge_required)
            )
        try:
            summary = _read_json_path(spp001_bridge_summary)
            inventory = _read_json_path(spp001_bridge_inventory)
            manifest = _read_json_path(spp001_bridge_manifest)
            gate = _read_json_path(spp001_bridge_gate)
            no_leakage = _read_json_path(spp001_bridge_no_leakage)
            safety = _read_json_path(spp001_bridge_safety)
            for key, expected in [
                ("repair_scope", "spp001_model_provenance_bridge_repair"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("spp001_smoke_executed", False),
                ("selected_32_batch_executed", False),
                ("full_1056_generation_run", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_spp001_rerun_commit", "f33eb97790a2bcc232a17ecd79be6c5153407f3b"),
                ("pair_id", "SPP001"),
                ("prior_outaged_branch", "L15"),
                ("candidate_next_branch", "L04"),
                ("previous_execution_status", "failed"),
                ("l15_trip_command_model_source", "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15"),
                ("l04_trip_command_model_source", "IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker"),
                ("same_wrapper_trip_commands_available", False),
                ("repaired_provenance_manifest_written", True),
                ("can_rerun_spp001_after_manual_approval", False),
                ("no_label_value_generated", True),
                ("raw_trajectories_committed", False),
                ("full_timeseries_committed", False),
                ("mat_files_committed", False),
                ("slx_files_committed", False),
                ("source_slx_modified", False),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_export_formal_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"SPP001 provenance bridge summary must set {key}={expected!r}.")
            if not summary.get("blocker_if_any"):
                failures.append("SPP001 provenance bridge summary must preserve a blocker.")
            if manifest.get("manifest_scope") != "spp001_same_wrapper_provenance_manifest":
                failures.append("SPP001 provenance manifest has wrong scope.")
            if manifest.get("same_wrapper_confirmed") is not False:
                failures.append("SPP001 provenance manifest must not confirm same-wrapper without evidence.")
            if manifest.get("approved_for_execution_now") is not False or manifest.get("requires_next_round_approval") is not True:
                failures.append("SPP001 provenance manifest must require a separate approval round.")
            if gate.get("gate_scope") != "spp001_rerun_provenance_gate":
                failures.append("SPP001 provenance gate has wrong scope.")
            if gate.get("l15_ready") is not True or gate.get("l04_ready") is not True:
                failures.append("SPP001 provenance gate must preserve L15/L04 readiness.")
            if gate.get("same_wrapper_confirmed") is not False or gate.get("provenance_bridge_ready") is not False:
                failures.append("SPP001 provenance gate must block rerun when same-wrapper is not confirmed.")
            if gate.get("can_request_spp001_rerun_approval") is not False:
                failures.append("SPP001 provenance gate must not allow rerun approval yet.")
            if not inventory.get("l15_trip_command_candidates") or not inventory.get("l04_trip_command_candidates"):
                failures.append("SPP001 provenance inventory must contain L15 and L04 candidates.")
            if inventory.get("selected_candidate_if_any") is not None:
                failures.append("SPP001 provenance inventory must not select a candidate without same-wrapper proof.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_future_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"SPP001 provenance no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "source_slx_modified",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"SPP001 provenance safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("SPP001 provenance large-file safety check must pass.")
            bridge_text = "\n".join(
                [
                    _read_text("docs/ieee39_spp001_model_provenance_bridge_repair.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_spp001_single_pair_smoke_rerun.md"),
                    _read_text("docs/ieee39_l15_handwired_validation_readiness_repair.md"),
                    _read_text("docs/ieee39_matlab_selected_pair_entrypoint_repair.md"),
                    _read_text("results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/spp001_provenance_bridge_repair_summary.md"),
                ]
            ).lower()
            normalized_bridge = " ".join(bridge_text.replace("`", "").split())
            for required in [
                "spp001 model provenance bridge repair",
                "does not train gcn",
                "does not rerun formal audit",
                "does not execute spp001 smoke",
                "does not execute selected 32 batch",
                "does not run full 1056 generation",
                "does not export formal labels",
                "does not retrain the reranker",
                "clean-lab l15",
                "same wrapper",
                "no spp001 0/1 label",
                "raw trajectory",
                "full timeseries",
                "source .slx is not modified",
                "bus-fault labels are not used",
                "l12 remains special/excluded",
                "pilot labels are not formal training labels",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_bridge:
                    failures.append(f"SPP001 provenance bridge docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "rerun formal audit completed",
                "spp001 smoke completed",
                "selected 32 batch execution completed",
                "full 1056 generation completed",
                "formal labels exported",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
                "deployment ready",
            ]:
                if bad in normalized_bridge:
                    failures.append(f"SPP001 provenance bridge docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read SPP001 provenance bridge repair artifacts: {exc}")

    spp001_dry_dir = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run"
    spp001_dry_doc = ROOT / "docs/ieee39_spp001_same_wrapper_bridge_dry_run.md"
    spp001_dry_summary = spp001_dry_dir / "spp001_same_wrapper_bridge_dry_run_summary.json"
    spp001_dry_plan = spp001_dry_dir / "spp001_bridge_component_plan.json"
    spp001_dry_manifest = spp001_dry_dir / "spp001_same_wrapper_candidate_manifest.json"
    spp001_dry_gate = spp001_dry_dir / "spp001_bridge_readiness_gate.json"
    spp001_dry_no_leakage = spp001_dry_dir / "no_leakage_spp001_bridge_dry_run_audit.json"
    spp001_dry_safety = spp001_dry_dir / "large_file_safety_spp001_bridge_dry_run.json"
    spp001_dry_required = [
        spp001_dry_doc,
        spp001_dry_summary,
        spp001_dry_dir / "spp001_same_wrapper_bridge_dry_run_summary.md",
        spp001_dry_dir / "spp001_same_wrapper_bridge_dry_run_summary.csv",
        spp001_dry_plan,
        spp001_dry_dir / "spp001_bridge_component_plan.md",
        spp001_dry_manifest,
        spp001_dry_dir / "spp001_same_wrapper_candidate_manifest.md",
        spp001_dry_dir / "spp001_bridge_local_execution_checklist.md",
        spp001_dry_gate,
        spp001_dry_dir / "spp001_bridge_readiness_gate.md",
        spp001_dry_no_leakage,
        spp001_dry_dir / "no_leakage_spp001_bridge_dry_run_audit.md",
        spp001_dry_safety,
        spp001_dry_dir / "large_file_safety_spp001_bridge_dry_run.md",
    ]
    existing_spp001_dry_required = [path for path in spp001_dry_required if path.exists()]
    if existing_spp001_dry_required:
        missing_spp001_dry_required = [path for path in spp001_dry_required if not path.exists()]
        if missing_spp001_dry_required:
            failures.append(
                "IEEE39 SPP001 same-wrapper bridge dry-run artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_spp001_dry_required)
            )
        try:
            summary = _read_json_path(spp001_dry_summary)
            plan = _read_json_path(spp001_dry_plan)
            manifest = _read_json_path(spp001_dry_manifest)
            gate = _read_json_path(spp001_dry_gate)
            no_leakage = _read_json_path(spp001_dry_no_leakage)
            safety = _read_json_path(spp001_dry_safety)
            for key, expected in [
                ("dry_run_scope", "spp001_same_wrapper_bridge_dry_run"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("spp001_smoke_executed", False),
                ("selected_32_batch_executed", False),
                ("full_1056_generation_run", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_provenance_bridge_commit", "5ad76acea5fb0e8c1f887ce868d2e1ce5dc08c27"),
                ("pair_id", "SPP001"),
                ("prior_outaged_branch", "L15"),
                ("candidate_next_branch", "L04"),
                ("same_wrapper_bridge_planned", True),
                ("same_wrapper_bridge_built_this_round", False),
                ("local_lab_copy_required", True),
                ("local_lab_copy_committed", False),
                ("source_slx_modified", False),
                ("can_build_same_wrapper_bridge_locally", True),
                ("can_confirm_same_wrapper_now", False),
                ("can_rerun_spp001_after_manual_approval", False),
                ("no_label_value_generated", True),
                ("raw_trajectories_committed", False),
                ("full_timeseries_committed", False),
                ("mat_files_committed", False),
                ("slx_files_committed", False),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"SPP001 bridge dry-run summary must set {key}={expected!r}.")
            if "approve local SPP001 same-wrapper bridge build/validation" not in str(summary.get("recommended_next_step")):
                failures.append("SPP001 bridge dry-run must recommend local bridge build/validation approval.")
            if plan.get("plan_scope") != "spp001_same_wrapper_bridge_component_plan":
                failures.append("SPP001 bridge component plan has wrong scope.")
            if plan.get("local_lab_copy_only") is not True or plan.get("source_slx_modified") is not False:
                failures.append("SPP001 bridge component plan must be local-copy only and not modify source SLX.")
            if manifest.get("manifest_scope") != "spp001_same_wrapper_candidate_manifest":
                failures.append("SPP001 same-wrapper candidate manifest has wrong scope.")
            if manifest.get("same_wrapper_confirmed_now") is not False:
                failures.append("SPP001 dry-run manifest must not confirm same-wrapper before local build.")
            if manifest.get("same_wrapper_bridge_built_this_round") is not False:
                failures.append("SPP001 dry-run manifest must not claim bridge was built.")
            if manifest.get("approved_for_execution_now") is not False or manifest.get("requires_next_round_approval") is not True:
                failures.append("SPP001 dry-run manifest must require a separate approval round.")
            if gate.get("gate_scope") != "spp001_same_wrapper_bridge_readiness_gate":
                failures.append("SPP001 bridge readiness gate has wrong scope.")
            for key, expected in [
                ("l15_ready", True),
                ("l04_ready", True),
                ("same_wrapper_confirmed_now", False),
                ("local_bridge_build_required", True),
                ("selected_32_batch_allowed", False),
                ("full_1056_allowed", False),
                ("formal_label_export_allowed", False),
                ("gcn_training_allowed", False),
                ("can_request_local_bridge_build_approval", True),
                ("can_request_spp001_smoke_rerun_approval", False),
            ]:
                if gate.get(key) != expected:
                    failures.append(f"SPP001 bridge readiness gate must set {key}={expected!r}.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_future_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"SPP001 bridge dry-run no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "local_lab_copy_committed",
                "source_slx_modified",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"SPP001 bridge dry-run safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("SPP001 bridge dry-run large-file safety check must pass.")
            dry_text = "\n".join(
                [
                    _read_text("docs/ieee39_spp001_same_wrapper_bridge_dry_run.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/spp001_same_wrapper_bridge_dry_run_summary.md"),
                    _read_text("results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/spp001_bridge_local_execution_checklist.md"),
                ]
            ).lower()
            normalized_dry = " ".join(dry_text.replace("`", "").split())
            for required in [
                "spp001 same-wrapper bridge dry-run",
                "does not train gcn",
                "does not rerun formal audit",
                "does not execute spp001 smoke",
                "does not execute selected 32 batch",
                "does not run full 1056 generation",
                "does not export formal labels",
                "l15 and l04 tripcommand paths are not in the same wrapper",
                "one-pair same-wrapper bridge",
                "local lab copy",
                "does not generate a 0/1 label",
                "raw trajectory",
                "full timeseries",
                "source .slx is not modified",
                "bus-fault labels are not used",
                "l12 remains special/excluded",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_dry:
                    failures.append(f"SPP001 bridge dry-run docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "spp001 smoke completed",
                "selected 32 batch execution completed",
                "full 1056 generation completed",
                "formal labels exported",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
                "deployment ready",
            ]:
                if bad in normalized_dry:
                    failures.append(f"SPP001 bridge dry-run docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read SPP001 same-wrapper bridge dry-run artifacts: {exc}")

    l15_repair_dir = ROOT / "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair"
    l15_repair_doc = ROOT / "docs/ieee39_l15_handwired_validation_readiness_repair.md"
    l15_summary = l15_repair_dir / "l15_readiness_repair_summary.json"
    l15_inventory = l15_repair_dir / "l15_evidence_inventory.json"
    l15_preview = l15_repair_dir / "repaired_combined_validation_preview.json"
    l15_gate = l15_repair_dir / "spp001_rerun_readiness_gate.json"
    l15_no_leakage = l15_repair_dir / "no_leakage_l15_readiness_repair_audit.json"
    l15_safety = l15_repair_dir / "large_file_safety_l15_readiness_repair.json"
    l15_required = [
        l15_repair_doc,
        l15_summary,
        l15_repair_dir / "l15_readiness_repair_summary.md",
        l15_repair_dir / "l15_readiness_repair_summary.csv",
        l15_inventory,
        l15_repair_dir / "l15_evidence_inventory.md",
        l15_preview,
        l15_repair_dir / "repaired_combined_validation_preview.md",
        l15_repair_dir / "repaired_combined_validation_preview.csv",
        l15_gate,
        l15_repair_dir / "spp001_rerun_readiness_gate.md",
        l15_no_leakage,
        l15_repair_dir / "no_leakage_l15_readiness_repair_audit.md",
        l15_safety,
        l15_repair_dir / "large_file_safety_l15_readiness_repair.md",
    ]
    existing_l15_required = [path for path in l15_required if path.exists()]
    if existing_l15_required:
        missing_l15_required = [path for path in l15_required if not path.exists()]
        if missing_l15_required:
            failures.append(
                "IEEE39 L15 readiness repair artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_l15_required)
            )
        try:
            summary = _read_json_path(l15_summary)
            inventory = _read_json_path(l15_inventory)
            preview = _read_json_path(l15_preview)
            gate = _read_json_path(l15_gate)
            no_leakage = _read_json_path(l15_no_leakage)
            safety = _read_json_path(l15_safety)
            for key, expected in [
                ("repair_scope", "l15_handwired_validation_readiness_repair"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_rerun", False),
                ("spp001_smoke_executed", False),
                ("selected_32_batch_executed", False),
                ("full_1056_generation_run", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("formal_labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("source_spp001_smoke_commit", "4c9e18b9aab9dce3d968ed3b47271372d60f78b2"),
                ("target_line_id", "L15"),
                ("paired_next_line_id", "L04"),
                ("previous_blocker", "single-pair smoke not ready: validation missing for L15; L04 validation passed"),
                ("l15_existing_evidence_found", True),
                ("l15_trip_command_path_found", True),
                ("l15_validation_passed", True),
                ("l15_readiness_status", "ready"),
                ("l04_validation_still_passed", True),
                ("repaired_combined_validation_written", True),
                ("can_rerun_spp001_smoke_after_manual_approval", True),
                ("no_label_value_generated", True),
                ("raw_trajectories_committed", False),
                ("full_timeseries_committed", False),
                ("mat_files_committed", False),
                ("slx_files_committed", False),
                ("source_slx_modified", False),
                ("forbidden_features_detected_in_inputs", []),
                ("no_leakage_policy_passed", True),
                ("final_engineering_conclusion", False),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_audit_now", False),
                ("should_export_formal_labels_now", False),
                ("should_retrain_reranker_now", False),
                ("should_deploy_model", False),
                ("blocker_if_any", None),
            ]:
                if summary.get(key) != expected:
                    failures.append(f"L15 readiness repair summary must set {key}={expected!r}.")
            if not inventory.get("l15_rows_found"):
                failures.append("L15 readiness inventory must contain l15_rows_found.")
            if not inventory.get("l15_trip_command_candidates"):
                failures.append("L15 readiness inventory must contain trip command candidates.")
            if not inventory.get("selected_source_if_any"):
                failures.append("L15 readiness inventory must select a source artifact.")
            by_line = {row.get("line_id"): row for row in preview}
            for line_id in ["L04", "L15"]:
                if line_id not in by_line:
                    failures.append(f"L15 repaired validation preview missing {line_id}.")
            if by_line.get("L15", {}).get("readiness_status") != "ready":
                failures.append("L15 repaired validation preview must mark L15 ready.")
            if "L15_TripCommand" not in str(by_line.get("L15", {}).get("trip_command_path", "")):
                failures.append("L15 repaired validation preview must preserve L15 trip_command_path.")
            for key, expected in [
                ("gate_scope", "spp001_rerun_readiness_gate"),
                ("pair_id", "SPP001"),
                ("prior_outaged_branch", "L15"),
                ("candidate_next_branch", "L04"),
                ("l15_ready", True),
                ("l04_ready", True),
                ("both_lines_ready", True),
                ("selected_32_batch_allowed", False),
                ("full_1056_allowed", False),
                ("formal_label_export_allowed", False),
                ("gcn_training_allowed", False),
                ("can_request_spp001_rerun_approval", True),
                ("blocker_if_any", None),
            ]:
                if gate.get(key) != expected:
                    failures.append(f"L15 SPP001 rerun readiness gate must set {key}={expected!r}.")
            for key, expected in [
                ("forbidden_features_detected_in_inputs", []),
                ("post_fault_dynamic_measurements_used_as_inputs", False),
                ("dynamic_outputs_used_only_as_future_labels_or_targets", True),
                ("label_derived_flags_used_as_inputs", False),
                ("bus_fault_labels_used", False),
                ("no_leakage_policy_passed", True),
            ]:
                if no_leakage.get(key) != expected:
                    failures.append(f"L15 no-leakage audit must set {key}={expected!r}.")
            for key in [
                "raw_trajectories_committed",
                "full_timeseries_committed",
                "mat_files_committed",
                "slx_files_committed",
                "slxc_files_committed",
                "slprj_committed",
                "source_slx_modified",
                "venv_committed",
                "wheel_or_dll_committed",
                "model_files_committed",
            ]:
                if safety.get(key) is not False:
                    failures.append(f"L15 large-file safety check must keep {key}=false.")
            if safety.get("safety_check_passed") is not True:
                failures.append("L15 large-file safety check must pass.")
            l15_text = "\n".join(
                [
                    _read_text("docs/ieee39_l15_handwired_validation_readiness_repair.md"),
                    _read_text("docs/gcn_pio_validation_log.md"),
                    _read_text("docs/ieee39_spp001_single_pair_smoke_execution.md"),
                    _read_text("docs/ieee39_matlab_selected_pair_entrypoint_repair.md"),
                    _read_text("results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/l15_readiness_repair_summary.md"),
                    _read_text("results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/spp001_rerun_readiness_gate.md"),
                ]
            ).lower()
            normalized_l15 = " ".join(l15_text.replace("`", "").split())
            for required in [
                "l15 handwired validation readiness repair",
                "does not train gcn",
                "does not rerun formal audit",
                "does not run spp001 smoke",
                "does not execute selected 32 batch",
                "does not run full 1056 generation",
                "does not export formal labels",
                "does not retrain the reranker",
                "does not create an spp001 0/1 label",
                "raw trajectory",
                "full timeseries",
                "source .slx is not modified",
                "bus-fault labels are not used",
                "l12 remains special/excluded",
                "pilot labels are not formal training labels",
                "phasor_rms is not emt",
                "generator_speed_proxy is not direct frequency",
                "temporary bus-fault injection is not engineering-grade protection",
            ]:
                if required not in normalized_l15:
                    failures.append(f"L15 readiness repair docs missing: {required}")
            for bad in [
                "gcn is useful",
                "gcn is useless",
                "rerun formal audit completed",
                "spp001 smoke completed",
                "selected 32 batch execution completed",
                "full 1056 generation completed",
                "formal labels exported",
                "emt validation completed",
                "generator_speed_proxy is direct frequency",
                "deployment ready",
            ]:
                if bad in normalized_l15:
                    failures.append(f"L15 readiness repair docs contain overstatement: {bad}")
        except Exception as exc:
            failures.append(f"Failed to read L15 readiness repair artifacts: {exc}")

    b39_review_dir = b39_export_dir / "no_training_composition_review"
    b39_review_json = b39_review_dir / "ieee39_v2_plus_b39_composition_review.json"
    b39_review_md = b39_review_dir / "ieee39_v2_plus_b39_composition_review.md"
    b39_family_counts = b39_review_dir / "ieee39_v2_plus_b39_label_family_counts.csv"
    b39_fault_counts = b39_review_dir / "ieee39_v2_plus_b39_fault_type_counts.csv"
    b39_comparison = b39_review_dir / "ieee39_v2_plus_b39_bus_fault_comparison.csv"
    if b39_review_json.exists() and b39_family_counts.exists() and b39_fault_counts.exists() and b39_comparison.exists():
        try:
            import json
            import pandas as pd

            review = json.loads(b39_review_json.read_text(encoding="utf-8"))
            family = pd.read_csv(b39_family_counts)
            fault = pd.read_csv(b39_fault_counts)
            comparison = pd.read_csv(b39_comparison)
            expected_review = {
                "previous_v2_candidate_count": 40,
                "v2_plus_b39_candidate_count": 41,
                "num_new_b39_bus_fault_candidates": 1,
                "old_formal_gate": "35 / 33 / 33",
                "num_formal_v1_existing": 35,
                "num_handwired_line_trip": 33,
                "num_non_line_trip_candidates": 6,
                "num_bus_fault_candidates": 1,
                "num_temporary_smoke_candidates": 1,
                "num_candidate_not_formal_label": 1,
                "num_training_ready_label_candidate": 41,
            }
            for key, value in expected_review.items():
                if review.get(key) != value:
                    failures.append(f"B39 composition review must record {key}={value!r}.")
            for key in [
                "l12_excluded",
                "nf06_provenance_warning_preserved",
                "b39_target_bus_complete",
                "b39_target_bus_or_component_complete",
                "b39_schema_consistency_passed",
                "count_consistency_passed",
                "export_boundary_passed",
            ]:
                if review.get(key) is not True:
                    failures.append(f"B39 composition review must record {key}=true.")
            for key in ["b39_exact_duplicate", "b39_provenance_risk", "should_train_now"]:
                if review.get(key) is not False:
                    failures.append(f"B39 composition review must record {key}=false.")
            family_counts = dict(zip(family["label_family"], family["count"]))
            fault_counts = dict(zip(fault["fault_type"], fault["count"]))
            if family_counts.get("existing_formal_dynamic") != 35:
                failures.append("B39 composition review family counts must record 35 formal dynamic rows.")
            if family_counts.get("non_line_trip") != 6:
                failures.append("B39 composition review family counts must record 6 non-line-trip rows.")
            if fault_counts.get("three_phase_bus_fault_temp_smoke") != 1:
                failures.append("B39 composition review fault counts must record one B39 bus fault.")
            if len(comparison) != 1:
                failures.append("B39 bus-fault comparison must contain one row.")
            else:
                row = comparison.iloc[0]
                if row.get("target_bus") != "B39" or row.get("target_bus_or_component") != "B39":
                    failures.append("B39 bus-fault comparison must preserve both target bus fields.")
            review_text = b39_review_md.read_text(encoding="utf-8", errors="ignore").lower()
            for required in ["b39_schema_consistency_passed", "count_consistency_passed", "export_boundary_passed", "should_train_now"]:
                if required not in review_text:
                    failures.append(f"B39 composition review markdown missing {required}.")
        except Exception as exc:
            failures.append(f"Failed to read B39 composition review artifacts: {exc}")

    v2_b39_preview_dir = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview"
    v2_b39_comparison = v2_b39_preview_dir / "v2_plus_b39_preview_comparison.json"
    if v2_b39_comparison.exists():
        try:
            import json

            comparison = json.loads(v2_b39_comparison.read_text(encoding="utf-8"))
            expected = {
                "preview_only": True,
                "final_performance_conclusion": False,
                "previous_v2_candidate_count": 40,
                "v2_plus_b39_candidate_count": 41,
                "b39_candidate_count": 1,
                "old_formal_gate": "35 / 33 / 33",
                "l12_excluded": True,
                "nf06_provenance_warning_preserved": True,
                "b39_schema_consistency_passed": True,
            }
            for key, value in expected.items():
                if comparison.get(key) != value:
                    failures.append(f"v2-plus-B39 preview comparison must record {key}={value!r}.")
            for key in [
                "include_all_41_metrics",
                "exclude_provenance_metrics",
                "no_dynamic_measurement_features_metrics",
                "label_family_holdout_metrics",
                "bus_fault_holdout_metrics",
            ]:
                if key not in comparison:
                    failures.append(f"v2-plus-B39 preview comparison missing {key}.")
            mode_expectations = {
                "include_all_41_candidates": {"num_samples": 41, "contains_b39": True, "contains_nf06": True},
                "exclude_provenance_required": {"num_samples": 40, "contains_b39": True, "contains_nf06": False},
                "no_dynamic_measurement_features": {"num_samples": 41, "leakage_reduced": True},
                "label_family_holdout": {"num_test_non_line_trip": 6, "num_test_bus_fault": 1},
                "bus_fault_holdout": {"num_test": 1, "test_scenario_id": "BF_B39_TEMP_SMOKE", "target_bus": "B39"},
            }
            for mode, expected_fields in mode_expectations.items():
                metrics_path = v2_b39_preview_dir / mode / "preview_training_metrics.json"
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
                if metrics.get("preview_only") is not True:
                    failures.append(f"{mode} metrics must set preview_only=true.")
                if metrics.get("final_performance_conclusion") is not False:
                    failures.append(f"{mode} metrics must set final_performance_conclusion=false.")
                for key, value in expected_fields.items():
                    if metrics.get(key) != value:
                        failures.append(f"{mode} metrics must record {key}={value!r}.")
                if not metrics.get("regression_metrics"):
                    failures.append(f"{mode} metrics missing regression_metrics.")
                if mode == "no_dynamic_measurement_features":
                    forbidden_features = {
                        "min_voltage_pu",
                        "max_voltage_pu",
                        "min_frequency_hz",
                        "max_frequency_hz",
                        "max_speed_deviation",
                        "max_rotor_angle_separation_deg",
                        "dynamic_stress_score",
                        "unstable_flag",
                    }
                    if forbidden_features & set(metrics.get("feature_columns", [])):
                        failures.append("no_dynamic_measurement_features contains forbidden leakage features.")
                if mode == "bus_fault_holdout":
                    for key in [
                        "true_dynamic_stress_score",
                        "predicted_dynamic_stress_score",
                        "regression_absolute_error",
                        "classification_probability_if_available",
                        "skipped_metrics_reason",
                    ]:
                        if metrics.get(key) is None:
                            failures.append(f"bus_fault_holdout metrics missing {key}.")
        except Exception as exc:
            failures.append(f"Failed to read v2-plus-B39 preview training artifacts: {exc}")

    v2_b39_preview_doc = ROOT / "docs/ieee39_v2_plus_b39_preview_training.md"
    if v2_b39_preview_doc.exists():
        text = _read_text("docs/ieee39_v2_plus_b39_preview_training.md").lower()
        for required in [
            "not gcn training",
            "does not run simulink",
            "does not submit `.slx`",
            "candidate label, not formal label",
            "v2-plus-b39 candidate count: `41`",
            "phasor_rms`, not emt",
            "generator_speed_proxy` is not direct frequency",
            "not engineering-grade protection",
            "preview-only",
        ]:
            if required not in text:
                failures.append(f"v2-plus-B39 preview training doc missing: {required}")
        for bad in [
            "gcn trained",
            "is a final performance conclusion",
            "final performance conclusion = true",
            "emt validation completed",
            "generator_speed_proxy is direct frequency",
        ]:
            if bad in text:
                failures.append(f"v2-plus-B39 preview training doc contains overstatement: {bad}")

    b39_interpretation_doc = ROOT / "docs/ieee39_v2_plus_b39_preview_interpretation.md"
    if b39_interpretation_doc.exists():
        text = _read_text("docs/ieee39_v2_plus_b39_preview_interpretation.md").lower()
        for required in [
            "does not train gcn",
            "does not retrain the reranker",
            "no_dynamic_measurement_features rmse",
            "worse",
            "b39 holdout absolute error",
            "underestimates the dynamic_stress_score",
            "collect more independent bus-fault samples",
            "b26",
            "b26 is not smoke success",
            "phasor_rms`, not emt",
            "generator_speed_proxy` is not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in text:
                failures.append(f"B39 preview interpretation doc missing: {required}")
        for bad in [
            "gcn trained",
            "reranker retrained",
            "b26 smoke success",
            "b26 candidate label has been exported",
            "emt validation completed",
            "generator_speed_proxy is direct frequency",
        ]:
            if bad in text:
                failures.append(f"B39 preview interpretation doc contains overstatement: {bad}")

    b26_plan_doc = ROOT / "docs/ieee39_b26_manual_bus_fault_verification_plan.md"
    b26_template = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B26.json"
    b26_commands = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_gui_check_commands.md"
    if b26_plan_doc.exists() and b26_template.exists() and b26_commands.exists():
        try:
            import json

            plan_text = _read_text("docs/ieee39_b26_manual_bus_fault_verification_plan.md").lower()
            command_text = b26_commands.read_text(encoding="utf-8", errors="ignore").lower()
            payload = json.loads(b26_template.read_text(encoding="utf-8"))
            for required in [
                "b26 is the next priority bus-fault sample",
                "b26 has a human-verified injection point",
                "b26 is not smoke success",
                "b26 is not a candidate label",
                "grid/bus26_1",
                "grid/bus26_2",
                "update diagram only",
                "does not run simulink",
                "does not submit `.slx`",
                "does not train gcn",
                "does not retrain the reranker",
            ]:
                if required not in plan_text:
                    failures.append(f"B26 manual plan doc missing: {required}")
            if payload.get("human_verified_injection_point") is not True:
                failures.append("B26 template must record human_verified_injection_point=true after rename recheck.")
            if payload.get("safe_to_run_smoke_recommendation") is not True:
                failures.append("B26 template must record safe_to_run_smoke_recommendation=true after rename recheck.")
            if payload.get("update_diagram_attempted") is not True:
                failures.append("B26 template must record update_diagram_attempted=true after manual evidence collection.")
            if payload.get("update_diagram_success") is not True:
                failures.append("B26 template must record update_diagram_success=true for the compile-only check.")
            if payload.get("expected_fault_block_found") is not True:
                failures.append("B26 template must record expected_fault_block_found=true after Grid/Fault_B26_TEMP exists.")
            if payload.get("human_verified") is not True:
                failures.append("B26 template must record human_verified=true after rename recheck.")
            if payload.get("selected_fault_block_path") != "Grid/Fault_B26_TEMP":
                failures.append("B26 template must select Grid/Fault_B26_TEMP.")
            if payload.get("suggested_fault_block_name") != "Grid/Fault_B26_TEMP":
                failures.append("B26 template must include suggested_fault_block_name=Grid/Fault_B26_TEMP.")
            if payload.get("suggested_fault_start_s") != 0.5 or payload.get("suggested_duration_s") != 0.08:
                failures.append("B26 template must include suggested timing 0.5s / 0.08s.")
            busbars = set(payload.get("candidate_busbar_paths", []))
            if not {"Grid/Bus26_1", "Grid/Bus26_2"}.issubset(busbars):
                failures.append("B26 template must include Grid/Bus26_1 and Grid/Bus26_2.")
            for required in ["grid/bus26_1", "grid/bus26_2", "get_param", "portconnectivity", "fault_b26_temp", "simulationcommand', 'update", "do not run simulation"]:
                if required not in command_text:
                    failures.append(f"B26 manual command snippets missing: {required}")
            if "simulationcommand', 'start" in command_text:
                failures.append("B26 manual command snippets must not start simulation.")
        except Exception as exc:
            failures.append(f"Failed to read B26 manual verification artifacts: {exc}")

    b39_export_doc = ROOT / "docs/ieee39_b39_bus_fault_candidate_label_export.md"
    if b39_export_doc.exists():
        text = _read_text("docs/ieee39_b39_bus_fault_candidate_label_export.md").lower()
        for required in [
            "does not run simulink",
            "does not submit `.slx`",
            "does not modify source `.slx`",
            "does not train gcn",
            "does not retrain",
            "candidate_not_formal_label",
            "previous v2 candidate count: `40`",
            "new v2-plus-b39 candidate count: `41`",
            "old formal gate remains: `35 / 33 / 33`",
            "nf06 duplicate/provenance warning preserved",
            "phasor_rms`, not emt",
            "generator_speed_proxy` is not direct frequency",
            "not engineering-grade protection",
            "should_train_now: `false`",
        ]:
            if required not in text:
                failures.append(f"B39 candidate export doc missing: {required}")
        for bad in [
            "gcn trained: `true`",
            "reranker retrained: `true`",
            "final dynamic performance conclusion",
            "emt validation completed",
            "engineering-grade protection completed",
        ]:
            if bad in text:
                failures.append(f"B39 candidate export doc contains overstatement: {bad}")

    temp_lab_doc = ROOT / "docs/ieee39_bus_fault_temp_lab_injection.md"
    if temp_lab_doc.exists():
        text = _read_text("docs/ieee39_bus_fault_temp_lab_injection.md").lower()
        for required in [
            "temporary lab",
            "b39",
            "b26",
            "injection point found",
            "safe to run smoke",
            "no gcn was trained",
            "reranker was not retrained",
            "no labels were exported",
            "old formal label gate remains `35 / 33 / 33`",
            "v2-plus-b39 count remains `41`",
            "phasor_rms, not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in text:
                failures.append(f"Bus-fault temp-lab doc missing: {required}")
        for bad in [
            "returned to the full gcn pipeline",
            "trained gcn",
            "reranker was retrained",
            "updated the formal label gate",
            "exported bus-fault labels",
            "emt validation completed",
            "engineering-grade protection completed",
        ]:
            if bad in text:
                failures.append(f"Bus-fault temp-lab doc contains overstatement: {bad}")

    manual_doc = ROOT / "docs/ieee39_bus_fault_gui_manual_checklist.md"
    if manual_doc.exists():
        text = _read_text("docs/ieee39_bus_fault_gui_manual_checklist.md").lower()
        for required in [
            "gui manual",
            "b39",
            "b26",
            "grid/bus39",
            "grid/bus26_1",
            "fault (three-phase)",
            "only if every item",
            "do not train gcn",
            "do not retrain",
            "do not export labels",
            "old formal gate remains `35 / 33 / 33`",
            "v2-plus-b39 count remains `41`",
            "phasor_rms, not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in text:
                failures.append(f"Bus-fault GUI manual checklist missing: {required}")
        for bad in [
            "b39 smoke success",
            "b26 smoke success",
            "smoke success completed",
            "trained gcn model",
            "reranker was retrained",
            "exported bus-fault labels",
            "final dynamic performance conclusion",
            "emt validation completed",
            "generator_speed_proxy is direct frequency",
            "engineering-grade protection completed",
        ]:
            if bad in text:
                failures.append(f"Bus-fault GUI manual checklist contains overstatement: {bad}")

    manual_summary = temp_lab_dir / "manual_review_consolidation_summary.json"
    if manual_summary.exists():
        try:
            import json

            summary = json.loads(manual_summary.read_text(encoding="utf-8"))
            if summary.get("preview_only") is not True:
                failures.append("Manual bus-fault review summary must set preview_only=true.")
            if summary.get("target_bus") != "B39":
                failures.append("Manual bus-fault review summary must be based on the default B39 template.")
            if summary.get("recommendation") == "do_not_run_smoke":
                failures.append("Manual bus-fault review summary must no longer default to do_not_run_smoke after B39 verification.")
            if summary.get("recommendation") != "manual_review_supports_next_round_inventory_update":
                failures.append("Manual bus-fault review summary must support next-round B39 inventory update.")
            for key in [
                "human_verified_injection_point",
                "safe_to_run_smoke_recommendation",
            ]:
                if summary.get(key) is not True:
                    failures.append(f"Manual bus-fault review summary must record {key}=true for B39.")
            for key in [
                "source_model_saved",
                "temporary_model_committed",
                "inventory_modified",
                "simulink_run",
                "labels_exported",
                "gcn_trained",
                "reranker_retrained",
            ]:
                if summary.get(key) is not False:
                    failures.append(f"Manual bus-fault review summary must record {key}=false.")
            if summary.get("formal_label_gate") != "35 / 33 / 33":
                failures.append("Manual bus-fault review summary must preserve formal gate 35 / 33 / 33.")
            if summary.get("v2_candidate_count") != 40:
                failures.append("Manual bus-fault review summary must preserve v2 candidate count 40.")
        except Exception as exc:
            failures.append(f"Failed to read manual bus-fault review summary: {exc}")

    for target_bus in ["B39", "B26"]:
        template_path = temp_lab_dir / f"manual_bus_fault_injection_review_template_{target_bus}.json"
        if template_path.exists():
            try:
                import json

                template = json.loads(template_path.read_text(encoding="utf-8"))
                if template.get("target_bus") != target_bus:
                    failures.append(f"Manual bus-fault template {target_bus} has wrong target_bus.")
                if target_bus == "B39":
                    for key in [
                        "human_verified_injection_point",
                        "safe_to_run_smoke_recommendation",
                        "fault_block_connected_in_parallel",
                        "original_network_connection_preserved",
                        "no_unintended_bypass",
                        "no_floating_ports",
                        "no_unintended_islanding",
                        "update_diagram_attempted",
                        "update_diagram_success",
                        "measurement_signals_expected_available",
                    ]:
                        if template.get(key) is not True:
                            failures.append(f"Manual bus-fault template B39 must record {key}=true.")
                    if template.get("selected_fault_block_path") != "Grid/Fault_B39_TEMP":
                        failures.append("Manual bus-fault template B39 must select Grid/Fault_B39_TEMP.")
                    if template.get("next_action") != "prepare temporary B39 smoke in next round":
                        failures.append("Manual bus-fault template B39 must point to next-round temporary smoke preparation.")
                else:
                    for key in [
                        "human_verified_injection_point",
                        "safe_to_run_smoke_recommendation",
                        "fault_block_connected_in_parallel",
                        "original_network_connection_preserved",
                        "no_unintended_bypass",
                        "no_floating_ports",
                        "no_unintended_islanding",
                        "update_diagram_attempted",
                        "update_diagram_success",
                        "measurement_signals_expected_available",
                    ]:
                        if template.get(key) is not True:
                            failures.append(f"Manual bus-fault template {target_bus} must record {key}=true after rename recheck.")
                    if template.get("selected_fault_block_path") != "Grid/Fault_B26_TEMP":
                        failures.append("Manual bus-fault template B26 must select Grid/Fault_B26_TEMP.")
                    next_action = str(template.get("next_action", "")).lower()
                    if "before any temporary smoke" not in next_action:
                        failures.append(f"Manual bus-fault template {target_bus} must keep conservative next_action.")
                for key in ["source_model_saved", "temporary_model_committed"]:
                    if template.get(key) is not False:
                        failures.append(f"Manual bus-fault template {target_bus} must record {key}=false.")
                if not template.get("candidate_blocks_reviewed"):
                    failures.append(f"Manual bus-fault template {target_bus} must list candidate blocks.")
            except Exception as exc:
                failures.append(f"Failed to read manual bus-fault template {target_bus}: {exc}")

    b39_evidence_doc = ROOT / "docs/ieee39_bus_fault_b39_manual_review_result.md"
    if b39_evidence_doc.exists():
        text = _read_text("docs/ieee39_bus_fault_b39_manual_review_result.md").lower()
        for required in [
            "human simulink gui review",
            "simscapeblock",
            "busbar",
            "grid/fault_b39_temp",
            "bus39 port 1",
            "b9 to b39",
            "old fault",
            "bus16_1",
            "b16 to b17",
            "update diagram passed",
            "fault_start_time = 0.5 s",
            "fault_duration = 0.08 s",
            "not smoke success",
            "35 / 33 / 33",
            "v2 candidate count remains `40`",
            "phasor_rms, not emt",
            "not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in text:
                failures.append(f"B39 manual evidence doc missing: {required}")
        for bad in [
            "b39 smoke success",
            "smoke success completed",
            "exported bus-fault labels",
            "trained gcn model",
            "reranker was retrained",
            "emt validation completed",
            "generator_speed_proxy is direct frequency",
            "engineering-grade protection completed",
        ]:
            if bad in text:
                failures.append(f"B39 manual evidence doc contains overstatement: {bad}")

    non_line_export_dir = non_line_dir / "non_line_trip_label_export"
    non_line_candidates = non_line_export_dir / "ieee39_non_line_trip_dynamic_label_candidates.csv"
    combined_v2 = non_line_export_dir / "ieee39_dynamic_label_schema_v2_combined_candidates.csv"
    quality_v2 = non_line_export_dir / "ieee39_dynamic_label_quality_summary_v2_with_non_line_trip_candidates.json"
    readiness_v2 = non_line_export_dir / "ieee39_dynamic_aware_training_readiness_v2_with_non_line_trip_candidates.json"
    provenance_report = non_line_export_dir / "ieee39_non_line_trip_duplicate_provenance_report.json"
    if non_line_candidates.exists() and combined_v2.exists() and quality_v2.exists() and readiness_v2.exists() and provenance_report.exists():
        try:
            import json
            import pandas as pd

            candidates = pd.read_csv(non_line_candidates)
            combined = pd.read_csv(combined_v2)
            quality = json.loads(quality_v2.read_text(encoding="utf-8"))
            readiness = json.loads(readiness_v2.read_text(encoding="utf-8"))
            provenance = json.loads(provenance_report.read_text(encoding="utf-8"))
            expected_ids = {"NF01", "NF02", "NF03", "NF04", "NF06"}
            if len(candidates) != 5 or set(candidates.get("scenario_id", pd.Series(dtype=str)).astype(str)) != expected_ids:
                failures.append("Non-line-trip candidate export must contain exactly NF01/NF02/NF03/NF04/NF06.")
            if len(combined) != 40:
                failures.append("Combined v2 candidate schema must contain 40 rows.")
            if int(combined.get("non_line_trip_label", pd.Series(dtype=bool)).astype(bool).sum()) != 5:
                failures.append("Combined v2 candidate schema must contain five non-line-trip rows.")
            if int(combined.get("handwired_line_trip_label", pd.Series(dtype=bool)).astype(bool).sum()) != 33:
                failures.append("Combined v2 candidate schema must preserve 33 handwired line-trip rows.")
            if not candidates.get("label_family", pd.Series(dtype=str)).astype(str).eq("non_line_trip").all():
                failures.append("All non-line-trip candidates must have label_family=non_line_trip.")
            if candidates.get("handwired_line_trip_label", pd.Series(dtype=bool)).astype(bool).any():
                failures.append("Non-line-trip candidates must not be handwired line-trip labels.")
            if candidates.get("formal_line_trip_label", pd.Series(dtype=bool)).astype(bool).any():
                failures.append("Non-line-trip candidates must not be formal line-trip labels.")
            nf06 = candidates[candidates.get("scenario_id", pd.Series(dtype=str)).astype(str).eq("NF06")]
            if nf06.empty or not bool(nf06.iloc[0].get("provenance_check_required", False)):
                failures.append("NF06 must be marked provenance_check_required.")
            joined = candidates.to_json().lower()
            for forbidden in ["l12", "handwired_timed_breaker", "single_line_trip"]:
                if forbidden in joined:
                    failures.append(f"Non-line-trip candidate export must not contain {forbidden}.")
            if "l12" in combined.to_json().lower():
                failures.append("Combined v2 candidate schema must keep L12 excluded.")
            if quality.get("original_formal_gate_preserved") is not True:
                failures.append("V2 quality summary must preserve the original formal gate.")
            if quality.get("original_num_training_ready_labels") != 35:
                failures.append("V2 quality summary must report original 35 training-ready labels.")
            if quality.get("original_num_training_ready_handwired_line_trip_labels") != 33:
                failures.append("V2 quality summary must report original 33 handwired line-trip labels.")
            if quality.get("num_non_line_trip_candidate_labels") != 5:
                failures.append("V2 quality summary must report five non-line-trip candidates.")
            if quality.get("num_training_ready_labels_v2_combined_candidate") != 40:
                failures.append("V2 quality summary must report 40 combined candidate rows.")
            if quality.get("should_retrain_reranker_now") is not False:
                failures.append("V2 quality summary must not request immediate reranker retraining.")
            if readiness.get("ready_for_v2_preview_training") is not True or readiness.get("should_train_now") is not False:
                failures.append("V2 readiness must be ready for future preview but should_train_now=false.")
            provenance_text = json.dumps(provenance).lower()
            for required_id in ["nf01", "nf04", "nf06"]:
                if required_id not in provenance_text:
                    failures.append(f"Duplicate/provenance report missing {required_id}.")
            if provenance.get("provenance_check_required_scenarios") != ["NF06"]:
                failures.append("Duplicate/provenance report must mark NF06 only.")
        except Exception as exc:
            failures.append(f"Failed to read non-line-trip v2 export artifacts: {exc}")

    non_line_export_doc = ROOT / "docs/ieee39_non_line_trip_label_export.md"
    if non_line_export_doc.exists():
        text = _read_text("docs/ieee39_non_line_trip_label_export.md").lower()
        for required in [
            "did not run simulink",
            "did not modify `.slx`",
            "did not fix l12",
            "35 / 33 / 33",
            "non-line-trip candidate labels: `5`",
            "v2 combined candidate rows: `40`",
            "provenance_check_required = true",
            "phasor_rms, not emt",
            "generator_speed_proxy` is not direct frequency",
            "relay proxy is not engineering-grade protection",
        ]:
            if required not in text:
                failures.append(f"Non-line-trip label export doc missing: {required}")

    relay_doc = ROOT / "docs/ieee39_fault_breaker_relay_wrapper.md"
    if relay_doc.exists():
        text = _read_text("docs/ieee39_fault_breaker_relay_wrapper.md").lower()
        for required in ["basic relay proxy", "not engineering-grade", "phasor_rms", "pilot"]:
            if required not in text:
                failures.append(f"IEEE39 relay wrapper doc missing: {required}")
        for overstated in ["emt validation completed", "engineering-grade protection completed", "full protection model completed"]:
            if overstated in text:
                failures.append(f"Overstated IEEE39 relay wrapper claim: {overstated}")

    quality_summary = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json"
    if quality_summary.exists():
        import json

        quality = json.loads(quality_summary.read_text(encoding="utf-8"))
        if not quality.get("allowed_for_dynamic_aware_training", False):
            status_text = _read_text("docs/ieee39_graphical_dynamic_model_status.md").lower()
            if "allowed_for_dynamic_aware_training = false" not in status_text:
                failures.append("IEEE39 status doc must block training when label quality gate is false.")
            real_fault_doc = _read_text("docs/ieee39_real_fault_execution_status.md").lower() if (ROOT / "docs/ieee39_real_fault_execution_status.md").exists() else ""
            if "allowed_for_dynamic_aware_training = false" not in real_fault_doc:
                failures.append("Round 28 real fault doc must block training when label quality gate is false.")
        if quality.get("label_quality_status") != "training_ready_batch":
            for rel_doc in ["docs/ieee39_real_fault_execution_status.md", "docs/ieee39_fault_breaker_relay_wrapper.md"]:
                if (ROOT / rel_doc).exists():
                    text = _read_text(rel_doc).lower()
                    for bad in ["train the dynamic-aware reranker now", "proceed to train dynamic-aware reranker"]:
                        if bad in text:
                            failures.append(f"{rel_doc} must not recommend reranker training before training_ready_batch.")
        for required_key in [
            "num_labels_with_voltage_measurement",
            "num_labels_with_frequency_measurement",
            "num_labels_with_speed_measurement",
            "num_labels_with_rotor_angle_measurement",
            "measurement_quality_status",
            "num_training_ready_timed_line_trip_labels",
            "num_static_topology_disable_rows",
            "num_manual_required_trip_rows",
            "num_training_ready_handwired_line_trip_labels",
            "num_training_ready_handwired_line_trip_labels_by_line",
            "num_unique_handwired_line_ids",
            "num_unique_training_ready_fault_types",
            "num_handwired_validation_passed",
            "handwired_model_used",
            "handwired_model_committed",
        ]:
            if required_key not in quality:
                failures.append(f"IEEE39 quality summary missing key: {required_key}")
        expected_handwired_lines = {f"L{i:02d}": 1 for i in range(1, 35) if i != 12}
        if quality.get("num_training_ready_labels") != 35:
            failures.append("IEEE39 quality summary must report 35 training-ready labels after clean lab L11-L34.")
        if quality.get("num_training_ready_handwired_line_trip_labels") != 33:
            failures.append("IEEE39 quality summary must report 33 training-ready handwired line-trip labels.")
        if quality.get("num_training_ready_handwired_line_trip_labels_by_line") != expected_handwired_lines:
            failures.append("IEEE39 quality summary must report L01-L11 and L13-L34 as handwired training-ready lines.")
        if quality.get("num_unique_handwired_line_ids") != 33:
            failures.append("IEEE39 quality summary must report 33 unique handwired line IDs.")
        if quality.get("num_handwired_validation_passed") != 34:
            failures.append("IEEE39 quality summary must report 34 handwired validation-passed lines including L12.")
        if quality.get("allowed_for_dynamic_aware_training") is not True:
            failures.append("IEEE39 quality summary must allow preview dynamic-aware training once ten labels are ready.")

    line_map = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv"
    if line_map.exists():
        try:
            import pandas as pd

            table = pd.read_csv(line_map)
            if len(table) < 3:
                failures.append("IEEE39 line/breaker map must contain at least three pilot lines.")
            if "mapping_status" not in table.columns:
                failures.append("IEEE39 line/breaker map missing mapping_status.")
        except Exception as exc:
            failures.append(f"Failed to read IEEE39 line/breaker map: {exc}")

    full_line_map = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv"
    full_line_map_summary = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full_summary.json"
    inventory_path = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv"
    if full_line_map.exists():
        try:
            import json
            import pandas as pd

            table = pd.read_csv(full_line_map)
            inventory = pd.read_csv(inventory_path)
            summary = json.loads(full_line_map_summary.read_text(encoding="utf-8"))
            expected_lines = {f"L{i:02d}" for i in range(1, 35)}
            if set(table.get("line_id", pd.Series(dtype=str)).astype(str)) != expected_lines:
                failures.append("IEEE39 full line map must contain L01 through L34.")
            if summary.get("preserved_line_ids") != [f"L{i:02d}" for i in range(1, 11)]:
                failures.append("IEEE39 full line map must preserve L01 through L10.")
            if summary.get("newly_mapped_line_ids") != [f"L{i:02d}" for i in range(11, 35)]:
                failures.append("IEEE39 full line map must newly map L11 through L34.")
            if summary.get("warnings") != []:
                failures.append("IEEE39 full line map summary must not contain warnings.")
            inventory_paths = set(inventory.get("block_path", pd.Series(dtype=str)).astype(str))
            if not set(table.get("line_block_path", pd.Series(dtype=str)).astype(str)).issubset(inventory_paths):
                failures.append("IEEE39 full line map must use only paths found in the Grid inventory.")
        except Exception as exc:
            failures.append(f"Failed to read IEEE39 full line map: {exc}")

    real_fault_doc = ROOT / "docs/ieee39_real_fault_execution_status.md"
    if real_fault_doc.exists():
        text = _read_text("docs/ieee39_real_fault_execution_status.md").lower()
        for overstated in [
            "emt validation completed",
            "engineering-grade protection completed",
            "static topology disable is a timed breaker",
            "full opf dynamic simulation completed",
        ]:
            if overstated in text:
                failures.append(f"Overstated Round 28 claim: {overstated}")

    round29_doc = ROOT / "docs/ieee39_measurement_extraction_and_timed_trip.md"
    if round29_doc.exists():
        text = _read_text("docs/ieee39_measurement_extraction_and_timed_trip.md").lower()
        for required in [
            "generator_speed_proxy",
            "not a direct frequency measurement",
            "static topology disable is not a timed breaker",
            "allowed_for_dynamic_aware_training = true",
        ]:
            if required not in text:
                failures.append(f"Round 29 measurement doc missing required conservative term: {required}")
        for bad in [
            "emt validation completed",
            "engineering-grade protection completed",
            "train the dynamic-aware reranker now",
            "proceed to train dynamic-aware reranker",
        ]:
            if bad in text:
                failures.append(f"Round 29 measurement doc contains an overstatement: {bad}")

    simlog_inventory = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_simlog_tree_inventory.csv"
    if simlog_inventory.exists():
        try:
            import pandas as pd

            table = pd.read_csv(simlog_inventory)
            required = {"node_path", "has_series", "candidate_signal_type", "num_points"}
            if not required.issubset(table.columns):
                failures.append("IEEE39 simlog inventory is missing required Round 29 columns.")
        except Exception as exc:
            failures.append(f"Failed to read IEEE39 simlog inventory: {exc}")

    round30_doc = ROOT / "docs/ieee39_timed_line_trip_probe_status.md"
    manual_doc = ROOT / "docs/ieee39_timed_breaker_manual_wiring_guide.md"
    for rel_doc in ["docs/ieee39_timed_line_trip_probe_status.md", "docs/ieee39_timed_breaker_manual_wiring_guide.md"]:
        path = ROOT / rel_doc
        if path.exists():
            text = _read_text(rel_doc).lower()
            for required in ["manual_required", "static_topology_disable", "not a timed breaker", "generator_speed_proxy", "not a direct frequency"]:
                if required not in text:
                    failures.append(f"Round 30 doc missing conservative term '{required}': {rel_doc}")
            for bad in [
                "static_topology_disable is a timed breaker",
                "timed controlled switch is engineering-grade",
                "engineering-grade protection completed",
                "emt validation completed",
                "train the dynamic-aware reranker now",
                "proceed to train dynamic-aware reranker",
            ]:
                if bad in text:
                    failures.append(f"Round 30 doc contains overstatement '{bad}': {rel_doc}")

    insertion_summary = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_timed_switch_insertion_summary.csv"
    if insertion_summary.exists():
        try:
            import pandas as pd

            table = pd.read_csv(insertion_summary)
            required = {"insertion_success", "trip_implementation", "training_ready_candidate", "note"}
            if not required.issubset(table.columns):
                failures.append("IEEE39 timed switch insertion summary is missing required columns.")
            elif not table.empty and not table["insertion_success"].astype(str).str.lower().isin({"1", "true"}).any():
                if not table["note"].astype(str).str.lower().str.contains("manual_required").any():
                    failures.append("Failed timed switch insertion must include manual_required in the summary note.")
        except Exception as exc:
            failures.append(f"Failed to read IEEE39 timed switch insertion summary: {exc}")

    handwired_doc = ROOT / "docs/ieee39_handwired_breaker_validation.md"
    if handwired_doc.exists():
        text = _read_text("docs/ieee39_handwired_breaker_validation.md").lower()
        for required in ["handwired .slx", "must not be committed", "pilot breaker-like", "not engineering-grade", "phasor_rms", "not emt", "generator_speed_proxy", "not direct frequency"]:
            if required not in text:
                failures.append(f"Handwired validation doc missing conservative term: {required}")
        for bad in ["engineering-grade protection completed", "emt validation completed", "train the dynamic-aware reranker now", "proceed to train dynamic-aware reranker"]:
            if bad in text:
                failures.append(f"Handwired validation doc contains overstatement: {bad}")

    multi_doc = ROOT / "docs/ieee39_multi_handwired_breaker_expansion.md"
    if multi_doc.exists():
        text = _read_text("docs/ieee39_multi_handwired_breaker_expansion.md").lower()
        for required in [
            "handwired .slx",
            "must not be committed",
            "pilot breaker-like",
            "not engineering-grade",
            "phasor_rms",
            "not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "preliminary preview training",
        ]:
            if required not in text:
                failures.append(f"Multi-handwired expansion doc missing conservative term: {required}")
        for bad in [
            "engineering-grade protection completed",
            "emt validation completed",
            "formal dynamic superiority",
            "train the dynamic-aware reranker now",
            "proceed to train dynamic-aware reranker",
        ]:
            if bad in text:
                failures.append(f"Multi-handwired expansion doc contains overstatement: {bad}")

    multi_validation = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv"
    if multi_validation.exists():
        try:
            import pandas as pd

            table = pd.read_csv(multi_validation)
            required = {"line_id", "breaker_block_name", "trip_command_name", "validation_passed", "handwired_model_committed"}
            if not required.issubset(table.columns):
                failures.append("Multi-handwired validation summary is missing required columns.")
            if "L01" not in set(table.get("line_id", [])):
                failures.append("Multi-handwired validation summary must include L01 as the reference line.")
            if table.get("handwired_model_committed", pd.Series([True])).astype(str).str.lower().isin({"1", "true"}).any():
                failures.append("Multi-handwired validation summary must record handwired_model_committed=false.")
        except Exception as exc:
            failures.append(f"Failed to read multi-handwired validation summary: {exc}")

    multi_summary = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_multi_handwired_line_trip_summary.csv"
    if multi_summary.exists():
        try:
            import pandas as pd

            table = pd.read_csv(multi_summary)
            required = {"test_case", "trip_implementation", "training_ready_candidate", "measurement_extraction_status", "tripped_line"}
            if not required.issubset(table.columns):
                failures.append("Multi-handwired line-trip summary is missing required columns.")
        except Exception as exc:
            failures.append(f"Failed to read multi-handwired line-trip summary: {exc}")

    clean_doc = ROOT / "docs/ieee39_clean_breaker_lab_workflow.md"
    if clean_doc.exists():
        text = _read_text("docs/ieee39_clean_breaker_lab_workflow.md").lower()
        for required in [
            "clean breaker lab",
            "clean lab .slx",
            "must not be committed",
            "l02",
            "phasor_rms",
            "not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "pilot breaker-like",
            "not engineering-grade",
            "preview training",
        ]:
            if required not in text:
                failures.append(f"Clean breaker lab doc missing conservative term: {required}")
        for bad in [
            "engineering-grade protection completed",
            "emt validation completed",
            "train the dynamic-aware reranker now",
            "proceed to train dynamic-aware reranker",
        ]:
            if bad in text:
                failures.append(f"Clean breaker lab doc contains overstatement: {bad}")

    per_line_doc = ROOT / "docs/ieee39_per_line_clean_breaker_lab_workflow.md"
    if per_line_doc.exists():
        text = _read_text("docs/ieee39_per_line_clean_breaker_lab_workflow.md").lower()
        for required in [
            "single-line dynamic labels",
            "one independent clean lab .slx per line",
            "clean_breaker_lab_l03.slx",
            "grid/b10 to b13",
            "l03_handwiredtimedbreaker",
            "l03_tripcommand",
            "phasor_rms",
            "not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "not engineering-grade",
            "preview training",
        ]:
            if required not in text:
                failures.append(f"Per-line clean breaker lab doc missing: {required}")
        for bad in [
            "engineering-grade protection completed",
            "emt validation completed",
            "train the dynamic-aware reranker now",
            "proceed to train dynamic-aware reranker",
        ]:
            if bad in text:
                failures.append(f"Per-line clean breaker lab doc contains overstatement: {bad}")

    clean_prepare = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_prepare_summary.json"
    if clean_prepare.exists():
        try:
            import json

            payload = json.loads(clean_prepare.read_text(encoding="utf-8"))
            required = {
                "source_wrapper_path",
                "target_clean_lab_path",
                "source_found",
                "target_created",
                "target_loadable",
                "contains_existing_L01_HandwiredTimedBreaker",
                "contains_existing_L02_HandwiredTimedBreaker",
                "contains_existing_L03_HandwiredTimedBreaker",
                "contains_existing_L04_HandwiredTimedBreaker",
                "clean_lab_committed",
                "note",
            }
            missing = required - set(payload)
            if missing:
                failures.append(f"Clean breaker lab prepare summary missing keys: {sorted(missing)}")
            if payload.get("clean_lab_committed", True):
                failures.append("Clean breaker lab prepare summary must record clean_lab_committed=false.")
        except Exception as exc:
            failures.append(f"Failed to read clean breaker lab prepare summary: {exc}")

    per_line_prepare = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_per_line_prepare_summary.json"
    if per_line_prepare.exists():
        try:
            import json

            payload = json.loads(per_line_prepare.read_text(encoding="utf-8"))
            required = {
                "line_id",
                "source_wrapper_path",
                "target_clean_lab_path",
                "source_found",
                "target_created",
                "target_loadable",
                "contains_existing_L01_HandwiredTimedBreaker",
                "contains_existing_L02_HandwiredTimedBreaker",
                "contains_existing_L03_HandwiredTimedBreaker",
                "contains_existing_L04_HandwiredTimedBreaker",
                "clean_lab_committed",
                "note",
            }
            missing = required - set(payload)
            if missing:
                failures.append(f"Per-line clean breaker lab prepare summary missing keys: {sorted(missing)}")
            if payload.get("line_id") != "L03":
                failures.append("Per-line clean breaker lab prepare summary must currently target L03.")
            if "clean_breaker_lab_L03.slx" not in str(payload.get("target_clean_lab_path", "")):
                failures.append("Per-line clean breaker lab prepare summary must point to the L03 clean lab target.")
            if payload.get("clean_lab_committed", True):
                failures.append("Per-line clean breaker lab prepare summary must record clean_lab_committed=false.")
        except Exception as exc:
            failures.append(f"Failed to read per-line clean breaker lab prepare summary: {exc}")

    clean_validation = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_validation_summary.csv"
    if clean_validation.exists():
        try:
            import pandas as pd

            table = pd.read_csv(clean_validation)
            required = {
                "line_id",
                "clean_lab_model_found",
                "clean_lab_model_loadable",
                "breaker_block_name",
                "trip_command_name",
                "validation_passed",
                "validation_failure_reason",
                "clean_lab_model_committed",
            }
            if not required.issubset(table.columns):
                failures.append("Clean breaker lab validation summary is missing required columns.")
            if "L02" not in set(table.get("line_id", [])):
                failures.append("Clean breaker lab validation summary must include L02.")
            if table.get("clean_lab_model_committed", pd.Series([True])).astype(str).str.lower().isin({"1", "true"}).any():
                failures.append("Clean breaker lab validation summary must record clean_lab_model_committed=false.")
            l02 = table[table.get("line_id", pd.Series("", index=table.index)).astype(str).eq("L02")]
            if l02.empty:
                failures.append("Clean breaker lab validation summary must contain an L02 row.")
            else:
                row = l02.iloc[0]
                for column in ["clean_lab_model_found", "clean_lab_model_loadable", "breaker_block_found", "trip_command_found", "breaker_near_line", "validation_passed"]:
                    if str(row.get(column, "")).lower() not in {"1", "true"}:
                        failures.append(f"Clean breaker lab L02 must have {column}=true after manual wiring.")
        except Exception as exc:
            failures.append(f"Failed to read clean breaker lab validation summary: {exc}")

    clean_line_trip = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_line_trip_summary.csv"
    if clean_line_trip.exists():
        try:
            import pandas as pd

            table = pd.read_csv(clean_line_trip)
            row = table[table.get("test_case", pd.Series("", index=table.index)).astype(str).eq("clean_lab_handwired_line_trip_L02")]
            if row.empty:
                failures.append("Clean breaker lab line-trip summary must include clean_lab_handwired_line_trip_L02.")
            else:
                row = row.iloc[0]
                for column in ["simulation_success", "physical_fault_or_breaker_action_executed", "training_ready_candidate", "breaker_opened"]:
                    if str(row.get(column, "")).lower() not in {"1", "true"}:
                        failures.append(f"Clean lab L02 compact summary must have {column}=true.")
                if row.get("trip_implementation") not in {"handwired_timed_breaker", "handwired_timed_controlled_switch"}:
                    failures.append("Clean lab L02 must use a handwired timed breaker implementation.")
                if row.get("measurement_extraction_status") != "voltage_speed_angle":
                    failures.append("Clean lab L02 must extract voltage_speed_angle measurements.")
                if "frequency=generator_speed_proxy" not in str(row.get("signal_source_summary", "")):
                    failures.append("Clean lab L02 signal summary must keep frequency=generator_speed_proxy.")
                if str(row.get("source_model", "")) != "clean_breaker_lab":
                    failures.append("Clean lab L02 source_model must be clean_breaker_lab.")
        except Exception as exc:
            failures.append(f"Failed to read clean breaker lab line-trip summary: {exc}")

    clean_merge = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_merge_summary.json"
    if clean_merge.exists():
        try:
            import json

            payload = json.loads(clean_merge.read_text(encoding="utf-8"))
            if payload.get("num_training_ready_handwired_rows") != 2:
                failures.append("Clean lab merge summary must report two training-ready handwired rows.")
            if payload.get("num_training_ready_handwired_rows_by_line") != {"L01": 1, "L02": 1}:
                failures.append("Clean lab merge summary must report L01 and L02 handwired ready rows.")
            if payload.get("static_topology_disable_overwrote_handwired") is not False:
                failures.append("Clean lab merge must not let static_topology_disable overwrite handwired rows.")
        except Exception as exc:
            failures.append(f"Failed to read clean breaker lab merge summary: {exc}")

    clean_l03_line_trip = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_L03_line_trip_summary.csv"
    if clean_l03_line_trip.exists():
        try:
            import pandas as pd

            table = pd.read_csv(clean_l03_line_trip)
            row = table[table.get("test_case", pd.Series("", index=table.index)).astype(str).eq("clean_lab_handwired_line_trip_L03")]
            if row.empty:
                failures.append("Clean L03 line-trip summary must include clean_lab_handwired_line_trip_L03.")
            else:
                row = row.iloc[0]
                for column in ["simulation_success", "physical_fault_or_breaker_action_executed", "training_ready_candidate", "breaker_opened"]:
                    if str(row.get(column, "")).lower() not in {"1", "true"}:
                        failures.append(f"Clean L03 compact summary must have {column}=true.")
                if row.get("measurement_extraction_status") != "voltage_speed_angle":
                    failures.append("Clean L03 must extract voltage_speed_angle measurements.")
                if row.get("source_model") != "clean_breaker_lab_L03":
                    failures.append("Clean L03 source_model must be clean_breaker_lab_L03.")
                if "frequency=generator_speed_proxy" not in str(row.get("signal_source_summary", "")):
                    failures.append("Clean L03 signal summary must keep frequency=generator_speed_proxy.")
        except Exception as exc:
            failures.append(f"Failed to read clean L03 line-trip summary: {exc}")

    clean_l03_merge = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l03_merge_summary.json"
    if clean_l03_merge.exists():
        try:
            import json

            payload = json.loads(clean_l03_merge.read_text(encoding="utf-8"))
            if payload.get("num_training_ready_handwired_rows") != 3:
                failures.append("Clean L03 merge summary must report three training-ready handwired rows.")
            if payload.get("num_training_ready_handwired_rows_by_line") != {"L01": 1, "L02": 1, "L03": 1}:
                failures.append("Clean L03 merge summary must report L01, L02, and L03 ready rows.")
            if payload.get("static_topology_disable_overwrote_handwired") is not False:
                failures.append("Clean L03 merge must not let static_topology_disable overwrite handwired rows.")
        except Exception as exc:
            failures.append(f"Failed to read clean L03 merge summary: {exc}")

    clean_l04_l05_merge = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l04_l05_merge_summary.json"
    if clean_l04_l05_merge.exists():
        try:
            import json

            payload = json.loads(clean_l04_l05_merge.read_text(encoding="utf-8"))
            if payload.get("num_training_ready_handwired_rows") != 5:
                failures.append("Clean L04/L05 merge summary must report five training-ready handwired rows.")
            if payload.get("num_training_ready_handwired_rows_by_line") != {"L01": 1, "L02": 1, "L03": 1, "L04": 1, "L05": 1}:
                failures.append("Clean L04/L05 merge summary must report L01 through L05 ready rows.")
            if payload.get("static_topology_disable_overwrote_handwired") is not False:
                failures.append("Clean L04/L05 merge must not let static_topology_disable overwrite handwired rows.")
        except Exception as exc:
            failures.append(f"Failed to read clean L04/L05 merge summary: {exc}")

    batch_prepare = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_prepare_summary.csv"
    if batch_prepare.exists():
        try:
            import pandas as pd

            table = pd.read_csv(batch_prepare)
            expected_paths = {
                "L09": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B16 to B24",
                "L10": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B17 to B27",
            }
            if set(table.get("line_id", pd.Series(dtype=str)).astype(str)) != set(expected_paths):
                failures.append("Batch clean lab prepare summary must currently contain L09 and L10.")
            for line_id, expected_path in expected_paths.items():
                row = table[table["line_id"].astype(str).eq(line_id)]
                if row.empty:
                    failures.append(f"Batch clean lab prepare summary missing {line_id}.")
                    continue
                row = row.iloc[0]
                if str(row.get("line_block_path", "")) != expected_path:
                    failures.append(f"Batch clean lab prepare {line_id} must use verified path {expected_path}.")
                if str(row.get("status", "")) != "prepared":
                    failures.append(f"Batch clean lab prepare {line_id} must be prepared.")
                if str(row.get("clean_lab_committed", "")).lower() not in {"0", "false"}:
                    failures.append(f"Batch clean lab prepare {line_id} must record clean_lab_committed=false.")
                if str(row.get("existing_handwired_breaker_found", "")).lower() not in {"0", "false"}:
                    failures.append(f"Batch clean lab prepare {line_id} must start from a wrapper without handwired breakers.")
        except Exception as exc:
            failures.append(f"Failed to read batch clean lab prepare summary: {exc}")

    batch_validation = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.csv"
    if batch_validation.exists():
        try:
            import pandas as pd

            table = pd.read_csv(batch_validation)
            expected_paths = {
                "L11": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B18 to B17",
                "L12": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B19 to B16",
                "L34": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B9 to B8",
            }
            expected_line_ids = {f"L{i:02d}" for i in range(11, 35)}
            if set(table.get("line_id", pd.Series(dtype=str)).astype(str)) != expected_line_ids:
                failures.append("Batch clean lab validation summary must currently contain L11 through L34.")
            for line_id, expected_path in expected_paths.items():
                row = table[table["line_id"].astype(str).eq(line_id)]
                if row.empty:
                    failures.append(f"Batch clean lab validation summary missing {line_id}.")
                    continue
                row = row.iloc[0]
                if str(row.get("line_block_path", "")) != expected_path:
                    failures.append(f"Batch clean lab validation {line_id} must use verified path {expected_path}.")
                for column in [
                    "clean_lab_model_found",
                    "clean_lab_model_loadable",
                    "breaker_block_found",
                    "trip_command_found",
                    "breaker_near_line",
                    "validation_passed",
                ]:
                    if str(row.get(column, "")).lower() not in {"1", "true"}:
                        failures.append(f"Batch clean lab validation {line_id} must have {column}=true.")
                if str(row.get("clean_lab_model_committed", "")).lower() not in {"0", "false"}:
                    failures.append(f"Batch clean lab validation {line_id} must record clean_lab_model_committed=false.")
        except Exception as exc:
            failures.append(f"Failed to read batch clean lab validation summary: {exc}")

    batch_line_trip = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_line_trip_summary.csv"
    if batch_line_trip.exists():
        try:
            import pandas as pd

            table = pd.read_csv(batch_line_trip)
            expected_line_ids = {f"L{i:02d}" for i in range(11, 35)}
            if set(table.get("tripped_line", pd.Series(dtype=str)).astype(str)) != expected_line_ids:
                failures.append("Batch clean lab compact summary must contain L11 through L34.")
            for line_id in sorted(expected_line_ids - {"L12"}):
                row = table[table.get("tripped_line", pd.Series("", index=table.index)).astype(str).eq(line_id)]
                if row.empty:
                    failures.append(f"Batch clean lab compact summary must include {line_id}.")
                    continue
                row = row.iloc[0]
                for column in [
                    "simulation_success",
                    "physical_fault_or_breaker_action_executed",
                    "training_ready_candidate",
                    "breaker_opened",
                ]:
                    if str(row.get(column, "")).lower() not in {"1", "true"}:
                        failures.append(f"Batch clean lab {line_id} compact summary must have {column}=true.")
                if row.get("measurement_extraction_status") != "voltage_speed_angle":
                    failures.append(f"Batch clean lab {line_id} must extract voltage_speed_angle measurements.")
                if row.get("source_model") != f"clean_breaker_lab_{line_id}":
                    failures.append(f"Batch clean lab {line_id} source_model must be clean_breaker_lab_{line_id}.")
                if "frequency=generator_speed_proxy" not in str(row.get("signal_source_summary", "")):
                    failures.append(f"Batch clean lab {line_id} signal summary must keep frequency=generator_speed_proxy.")
            l12 = table[table.get("tripped_line", pd.Series("", index=table.index)).astype(str).eq("L12")]
            if l12.empty:
                failures.append("Batch clean lab compact summary must include L12 timeout row.")
            else:
                l12 = l12.iloc[0]
                if l12.get("measurement_extraction_status") != "simulation_timeout":
                    failures.append("Batch clean lab L12 must be recorded as simulation_timeout.")
                if str(l12.get("training_ready_candidate", "")).lower() in {"1", "true"}:
                    failures.append("Batch clean lab L12 timeout must not be training-ready.")
        except Exception as exc:
            failures.append(f"Failed to read batch clean lab compact summary: {exc}")

    l12_diagnosis = ROOT / (
        "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/"
        "ieee39_l12_islanding_diagnosis.json"
    )
    if l12_diagnosis.exists():
        try:
            import json

            payload = json.loads(l12_diagnosis.read_text(encoding="utf-8"))
            expected = {
                "line_id": "L12",
                "line_block_path": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B19 to B16",
                "measurement_extraction_status": "simulation_timeout",
            }
            for key, value in expected.items():
                if payload.get(key) != value:
                    failures.append(f"L12 diagnosis must have {key}={value}.")
            for key in ["validation_passed", "breaker_block_found", "trip_command_found", "breaker_near_line", "islanding_candidate"]:
                if payload.get(key) is not True:
                    failures.append(f"L12 diagnosis must set {key}=true.")
            for key in [
                "simulation_success",
                "training_ready_candidate",
                "should_merge_as_training_ready",
                "should_retrain_reranker",
                "component_contains_reference_or_main_grid",
            ]:
                if payload.get(key) is not False:
                    failures.append(f"L12 diagnosis must set {key}=false.")
            if payload.get("removed_edge") != ["B19", "B16"]:
                failures.append("L12 diagnosis must remove edge B19-B16.")
            component = set(payload.get("b19_component_after_l12_open", []))
            if "B19" not in component:
                failures.append("L12 diagnosis B19 component must contain B19.")
            if not payload.get("recommended_manual_checks"):
                failures.append("L12 diagnosis must include recommended manual checks.")
            if "special-case timeout label" not in payload.get("recommended_next_action", ""):
                failures.append("L12 diagnosis must recommend keeping L12 as a special-case timeout label.")
            caveats = "\n".join(payload.get("caveats", [])).lower()
            for required in [
                "phasor_rms, not emt",
                "generator_speed_proxy, not direct frequency",
                "pilot breaker-like validation, not engineering-grade protection",
                "not a verified stable or unstable conclusion",
            ]:
                if required not in caveats:
                    failures.append(f"L12 diagnosis caveats missing: {required}")
        except Exception as exc:
            failures.append(f"Failed to read L12 islanding diagnosis: {exc}")

    l12_doc = ROOT / "docs/ieee39_l12_islanding_timeout_case.md"
    if l12_doc.exists():
        text = _read_text("docs/ieee39_l12_islanding_timeout_case.md").lower()
        for required in [
            "suspected islanding / timeout",
            "training_ready_candidate: `false`",
            "should_merge_as_training_ready: `false`",
            "should_retrain_reranker: `false`",
            "does not prove that l12 is dynamically stable or unstable",
            "phasor_rms",
            "not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "pilot breaker-like",
            "not engineering-grade",
            "do not commit `.slx`",
        ]:
            if required not in text:
                failures.append(f"L12 islanding doc missing: {required}")

    remaining_prepare = ROOT / (
        "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/"
        "ieee39_clean_breaker_lab_remaining_prepare_summary.csv"
    )
    if remaining_prepare.exists():
        try:
            import pandas as pd

            table = pd.read_csv(remaining_prepare)
            expected_lines = {f"L{i:02d}" for i in range(11, 35)}
            if set(table.get("line_id", pd.Series(dtype=str)).astype(str)) != expected_lines:
                failures.append("Remaining clean lab prepare summary must contain L11 through L34.")
            if not table.get("status", pd.Series(dtype=str)).astype(str).eq("prepared").all():
                failures.append("Remaining clean lab prepare summary must mark every row prepared.")
            for column in ["source_found", "target_created", "target_loadable"]:
                if not table.get(column, pd.Series(dtype=str)).astype(str).str.lower().isin({"1", "true"}).all():
                    failures.append(f"Remaining clean lab prepare summary must have {column}=true for all rows.")
            for column in ["existing_handwired_breaker_found", "clean_lab_committed"]:
                if not table.get(column, pd.Series(dtype=str)).astype(str).str.lower().isin({"0", "false"}).all():
                    failures.append(f"Remaining clean lab prepare summary must have {column}=false for all rows.")
            tracked_generated = "\n".join(_git_ls_files("results/gcn_search/ieee39_graphical_dynamic_model/generated_models")).lower()
            for line_id in expected_lines:
                if f"clean_breaker_lab_{line_id.lower()}.slx" in tracked_generated:
                    failures.append(f"Remaining clean lab {line_id} .slx must remain untracked.")
        except Exception as exc:
            failures.append(f"Failed to read remaining clean lab prepare summary: {exc}")

    clean_l06_l07_l08_merge = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l06_l07_l08_merge_summary.json"
    if clean_l06_l07_l08_merge.exists():
        try:
            import json

            payload = json.loads(clean_l06_l07_l08_merge.read_text(encoding="utf-8"))
            expected_lines = {
                "L01": 1,
                "L02": 1,
                "L03": 1,
                "L04": 1,
                "L05": 1,
                "L06": 1,
                "L07": 1,
                "L08": 1,
            }
            if payload.get("num_training_ready_handwired_rows") != 8:
                failures.append("Clean L06/L07/L08 merge summary must report eight training-ready handwired rows.")
            if payload.get("num_training_ready_handwired_rows_by_line") != expected_lines:
                failures.append("Clean L06/L07/L08 merge summary must report L01 through L08 ready rows.")
            if payload.get("static_topology_disable_overwrote_handwired") is not False:
                failures.append("Clean L06/L07/L08 merge must not let static_topology_disable overwrite handwired rows.")
        except Exception as exc:
            failures.append(f"Failed to read clean L06/L07/L08 merge summary: {exc}")

    clean_l09_l10_merge = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l09_l10_merge_summary.json"
    if clean_l09_l10_merge.exists():
        try:
            import json

            payload = json.loads(clean_l09_l10_merge.read_text(encoding="utf-8"))
            expected_lines = {f"L{i:02d}": 1 for i in range(1, 11)}
            if payload.get("num_training_ready_handwired_rows") != 10:
                failures.append("Clean L09/L10 merge summary must report ten training-ready handwired rows.")
            if payload.get("num_training_ready_handwired_rows_by_line") != expected_lines:
                failures.append("Clean L09/L10 merge summary must report L01 through L10 ready rows.")
            if payload.get("static_topology_disable_overwrote_handwired") is not False:
                failures.append("Clean L09/L10 merge must not let static_topology_disable overwrite handwired rows.")
        except Exception as exc:
            failures.append(f"Failed to read clean L09/L10 merge summary: {exc}")

    clean_l11_to_l34_merge = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l11_to_l34_merge_summary.json"
    if clean_l11_to_l34_merge.exists():
        try:
            import json

            payload = json.loads(clean_l11_to_l34_merge.read_text(encoding="utf-8"))
            expected_merged = [f"L{i:02d}" for i in range(11, 35) if i != 12]
            expected_lines = {f"L{i:02d}": 1 for i in range(1, 35) if i != 12}
            if payload.get("merged_line_ids") != expected_merged:
                failures.append("Clean L11-L34 merge summary must merge L11 and L13-L34 only.")
            if payload.get("timeout_line_ids") != ["L12"]:
                failures.append("Clean L11-L34 merge summary must record L12 as timeout.")
            if payload.get("failed_line_ids") != []:
                failures.append("Clean L11-L34 merge summary must have no non-timeout failed lines.")
            if payload.get("num_training_ready_handwired_rows") != 33:
                failures.append("Clean L11-L34 merge summary must report 33 training-ready handwired rows.")
            if payload.get("num_training_ready_handwired_rows_by_line") != expected_lines:
                failures.append("Clean L11-L34 merge summary must report L01-L11 and L13-L34 ready rows.")
            if payload.get("static_topology_disable_overwrote_handwired") is not False:
                failures.append("Clean L11-L34 merge must not let static_topology_disable overwrite handwired rows.")
        except Exception as exc:
            failures.append(f"Failed to read clean L11-L34 merge summary: {exc}")

    readiness = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json"
    if readiness.exists():
        try:
            import json

            payload = json.loads(readiness.read_text(encoding="utf-8"))
            if payload.get("num_training_ready_labels") != 35:
                failures.append("IEEE39 dynamic-aware readiness must report 35 training-ready labels.")
            if payload.get("num_training_ready_handwired_line_trip_labels") != 33:
                failures.append("IEEE39 dynamic-aware readiness must report 33 handwired line-trip labels.")
            if payload.get("num_unique_handwired_line_ids") != 33:
                failures.append("IEEE39 dynamic-aware readiness must report 33 unique handwired line IDs.")
            if payload.get("allowed_for_dynamic_aware_training") is not True:
                failures.append("IEEE39 dynamic-aware readiness must allow preview training.")
            if payload.get("ready_for_preview_training") is not True:
                failures.append("IEEE39 dynamic-aware readiness must set ready_for_preview_training=true.")
        except Exception as exc:
            failures.append(f"Failed to read IEEE39 dynamic-aware readiness summary: {exc}")

    preview_metrics = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_metrics.json"
    if preview_metrics.exists():
        try:
            import json

            payload = json.loads(preview_metrics.read_text(encoding="utf-8"))
            if payload.get("preview_only") is not True:
                failures.append("IEEE39 dynamic-aware reranker preview metrics must set preview_only=true.")
            if payload.get("allowed_for_dynamic_aware_training") is not True:
                failures.append("IEEE39 dynamic-aware reranker preview metrics must preserve allowed_for_dynamic_aware_training=true.")
            if payload.get("ready_for_preview_training") is not True:
                failures.append("IEEE39 dynamic-aware reranker preview metrics must preserve ready_for_preview_training=true.")
            if payload.get("num_samples") != 10:
                failures.append("IEEE39 dynamic-aware reranker preview metrics must report ten samples.")
            if payload.get("num_training_ready_labels") != 10:
                failures.append("IEEE39 dynamic-aware reranker preview metrics must report ten training-ready labels.")
            if payload.get("num_handwired_line_trip_labels") != 8:
                failures.append("IEEE39 dynamic-aware reranker preview metrics must report eight handwired line-trip labels.")
            if "dynamic_stress_score" not in payload.get("target_columns", []):
                failures.append("IEEE39 dynamic-aware reranker preview metrics missing dynamic_stress_score target.")
            if "unstable_flag" not in payload.get("target_columns", []):
                failures.append("IEEE39 dynamic-aware reranker preview metrics missing unstable_flag target.")
            if not payload.get("regression_metrics"):
                failures.append("IEEE39 dynamic-aware reranker preview metrics must include regression_metrics.")
            if not payload.get("classification_metrics") and not payload.get("skipped_metrics_reason"):
                failures.append("IEEE39 dynamic-aware reranker preview must include classification metrics or a skipped reason.")
        except Exception as exc:
            failures.append(f"Failed to read IEEE39 dynamic-aware reranker preview metrics: {exc}")

    preview_predictions = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_predictions.csv"
    if preview_predictions.exists():
        try:
            import pandas as pd

            table = pd.read_csv(preview_predictions)
            required = {
                "line_id",
                "test_case",
                "source_model",
                "y_true_dynamic_stress_score",
                "y_pred_dynamic_stress_score",
                "residual",
                "y_true_unstable_flag",
                "fold_id",
                "note",
            }
            if not required.issubset(table.columns):
                failures.append("IEEE39 dynamic-aware reranker preview predictions missing required columns.")
            if len(table) != 10:
                failures.append("IEEE39 dynamic-aware reranker preview predictions must contain ten rows.")
            for column in ["y_true_dynamic_stress_score", "y_pred_dynamic_stress_score", "residual"]:
                if column in table.columns and not pd.to_numeric(table[column], errors="coerce").notna().all():
                    failures.append(f"IEEE39 dynamic-aware reranker preview predictions must have numeric {column}.")
        except Exception as exc:
            failures.append(f"Failed to read IEEE39 dynamic-aware reranker preview predictions: {exc}")

    expanded_metrics = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_metrics.json"
    expanded_dataset = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_dataset.csv"
    expanded_comparison = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_comparison.json"
    if expanded_metrics.exists() and expanded_dataset.exists():
        try:
            import json
            import pandas as pd

            metrics = json.loads(expanded_metrics.read_text(encoding="utf-8"))
            dataset = pd.read_csv(expanded_dataset)
            if metrics.get("preview_only") is not True:
                failures.append("Expanded dynamic-aware preview metrics must set preview_only=true.")
            if metrics.get("num_samples") != 35:
                failures.append("Expanded dynamic-aware preview metrics must report 35 samples.")
            if len(dataset) != 35:
                failures.append("Expanded dynamic-aware preview dataset must contain 35 rows.")
            if "L12" in set(dataset.get("line_id", pd.Series(dtype=str)).astype(str)):
                failures.append("Expanded dynamic-aware preview dataset must exclude L12.")
            if metrics.get("allowed_for_dynamic_aware_training") is not True:
                failures.append("Expanded dynamic-aware preview metrics must preserve allowed_for_dynamic_aware_training=true.")
            if metrics.get("ready_for_preview_training") is not True:
                failures.append("Expanded dynamic-aware preview metrics must preserve ready_for_preview_training=true.")
            if metrics.get("random_seed") != 42:
                failures.append("Expanded dynamic-aware preview metrics must use random_seed=42.")
            if metrics.get("cv_strategy") != "leave_one_out":
                failures.append("Expanded dynamic-aware preview metrics must use leave_one_out.")
        except Exception as exc:
            failures.append(f"Failed to read expanded dynamic-aware preview artifacts: {exc}")

    if expanded_comparison.exists():
        try:
            import json

            payload = json.loads(expanded_comparison.read_text(encoding="utf-8"))
            if payload.get("original_num_samples") != 10:
                failures.append("Expanded preview comparison must report original_num_samples=10.")
            if payload.get("expanded_num_samples") != 35:
                failures.append("Expanded preview comparison must report expanded_num_samples=35.")
            comparison_text = "\n".join(payload.get("interpretation", []) + payload.get("caveats", [])).lower()
            for required in [
                "compact phasor_rms preview",
                "not a final dynamic performance conclusion",
                "metrics can be optimistic",
                "l12 remains excluded",
            ]:
                if required not in comparison_text:
                    failures.append(f"Expanded preview comparison missing caveat: {required}")
        except Exception as exc:
            failures.append(f"Failed to read expanded preview comparison: {exc}")

    stricter_metrics = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_metrics.json"
    stricter_dataset = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_dataset.csv"
    if stricter_metrics.exists() and stricter_dataset.exists():
        try:
            import json
            import pandas as pd

            metrics = json.loads(stricter_metrics.read_text(encoding="utf-8"))
            dataset = pd.read_csv(stricter_dataset)
            if metrics.get("preview_only") is not True:
                failures.append("Stricter comparison metrics must set preview_only=true.")
            if metrics.get("final_performance_conclusion") is not False:
                failures.append("Stricter comparison metrics must set final_performance_conclusion=false.")
            if metrics.get("num_samples") != 35 or len(dataset) != 35:
                failures.append("Stricter comparison must contain 35 samples.")
            if "L12" in set(dataset.get("line_id", pd.Series(dtype=str)).astype(str)):
                failures.append("Stricter comparison dataset must exclude L12.")
            feature_sets = metrics.get("feature_sets", {})
            for required in [
                "leaky_dynamic_measurement_features",
                "no_dynamic_measurement_features",
                "topology_only_features",
            ]:
                if required not in feature_sets:
                    failures.append(f"Stricter comparison missing feature set: {required}")
            forbidden_measurements = {
                "min_voltage_pu",
                "max_voltage_pu",
                "min_frequency_hz",
                "max_frequency_hz",
                "max_speed_deviation",
                "max_rotor_angle_separation_deg",
            }
            topology_features = set(feature_sets.get("topology_only_features", []))
            if forbidden_measurements & topology_features:
                failures.append("Topology-only stricter features must not contain compact dynamic measurements.")
            for required in ["leave_one_out", "grouped_line_range_holdout", "endpoint_bus_region_holdout", "random_kfold_baseline"]:
                if required not in metrics.get("split_strategies", {}):
                    failures.append(f"Stricter comparison missing split strategy: {required}")
            gap = metrics.get("leakage_gap_summary", {})
            if gap.get("rmse_gap_no_leak_minus_leaky") is None:
                failures.append("Stricter comparison must report leakage RMSE gap.")
        except Exception as exc:
            failures.append(f"Failed to read stricter dynamic-aware comparison: {exc}")

    v2_base = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview"
    v2_runs = {
        "include_all_candidates": {
            "num_samples": 40,
            "contains_nf06": True,
            "non_line_trip_rows": 5,
            "provenance_rows": 1,
        },
        "exclude_provenance_required": {
            "num_samples": 39,
            "contains_nf06": False,
            "non_line_trip_rows": 4,
            "provenance_rows": 0,
        },
    }
    for run_name, expected in v2_runs.items():
        dataset_path = v2_base / run_name / "preview_training_dataset.csv"
        metrics_path = v2_base / run_name / "preview_training_metrics.json"
        predictions_path = v2_base / run_name / "preview_training_predictions.csv"
        if dataset_path.exists() and metrics_path.exists() and predictions_path.exists():
            try:
                import json
                import pandas as pd

                dataset = pd.read_csv(dataset_path)
                predictions = pd.read_csv(predictions_path)
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
                if len(dataset) != expected["num_samples"] or metrics.get("num_samples") != expected["num_samples"]:
                    failures.append(f"v2 preview {run_name} must contain {expected['num_samples']} samples.")
                if bool(metrics.get("contains_nf06")) is not expected["contains_nf06"]:
                    failures.append(f"v2 preview {run_name} has wrong contains_nf06 flag.")
                has_nf06 = "NF06" in set(dataset.get("scenario_id", pd.Series(dtype=str)).astype(str))
                pred_has_nf06 = "NF06" in set(predictions.get("scenario_id", pd.Series(dtype=str)).astype(str))
                if has_nf06 is not expected["contains_nf06"] or pred_has_nf06 is not expected["contains_nf06"]:
                    failures.append(f"v2 preview {run_name} has inconsistent NF06 inclusion.")
                if "L12" in set(dataset.get("line_id", pd.Series(dtype=str)).astype(str)):
                    failures.append(f"v2 preview {run_name} must exclude L12.")
                if metrics.get("preview_only") is not True:
                    failures.append(f"v2 preview {run_name} must set preview_only=true.")
                if metrics.get("final_performance_conclusion") is not False:
                    failures.append(f"v2 preview {run_name} must set final_performance_conclusion=false.")
                if metrics.get("num_existing_formal_dynamic_rows") != 35:
                    failures.append(f"v2 preview {run_name} must record 35 formal v1 rows.")
                if metrics.get("num_handwired_line_trip_rows") != 33:
                    failures.append(f"v2 preview {run_name} must record 33 handwired rows.")
                if metrics.get("num_non_line_trip_candidate_rows") != expected["non_line_trip_rows"]:
                    failures.append(f"v2 preview {run_name} has wrong non-line-trip row count.")
                if metrics.get("provenance_check_required_rows") != expected["provenance_rows"]:
                    failures.append(f"v2 preview {run_name} has wrong provenance row count.")
                holdout = metrics.get("label_family_holdout_metrics", {})
                if not holdout.get("regression"):
                    failures.append(f"v2 preview {run_name} missing label_family_holdout regression.")
                if holdout.get("num_folds") != 1:
                    failures.append(f"v2 preview {run_name} must record one label_family_holdout fold.")
            except Exception as exc:
                failures.append(f"Failed to read v2 preview artifacts for {run_name}: {exc}")

    v2_comparison = v2_base / "v2_preview_comparison.json"
    if v2_comparison.exists():
        try:
            import json

            payload = json.loads(v2_comparison.read_text(encoding="utf-8"))
            if payload.get("preview_only") is not True:
                failures.append("v2 preview comparison must set preview_only=true.")
            if payload.get("final_performance_conclusion") is not False:
                failures.append("v2 preview comparison must set final_performance_conclusion=false.")
            expected_counts = {
                "v1_expanded_num_samples": 35,
                "v2_include_all_num_samples": 40,
                "v2_exclude_provenance_num_samples": 39,
                "non_line_trip_candidate_count": 5,
                "provenance_excluded_count": 1,
            }
            for key, value in expected_counts.items():
                if payload.get(key) != value:
                    failures.append(f"v2 preview comparison must record {key}={value}.")
            if not payload.get("duplicate_measurement_groups"):
                failures.append("v2 preview comparison must record duplicate_measurement_groups.")
            holdout = payload.get("label_family_holdout_metrics", {})
            if not holdout.get("include_all_candidates", {}).get("regression"):
                failures.append("v2 preview comparison missing include_all label_family_holdout regression.")
            if not holdout.get("exclude_provenance_required", {}).get("regression"):
                failures.append("v2 preview comparison missing exclude_provenance label_family_holdout regression.")
        except Exception as exc:
            failures.append(f"Failed to read v2 preview comparison: {exc}")

    v2_doc = ROOT / "docs/ieee39_dynamic_aware_reranker_v2_preview_training.md"
    if v2_doc.exists():
        text = _read_text("docs/ieee39_dynamic_aware_reranker_v2_preview_training.md").lower()
        for required in [
            "does not run simulink",
            "does not modify `.slx`",
            "does not fix l12",
            "does not overwrite the old formal gate",
            "include_all_candidates",
            "exclude_provenance_required",
            "final_performance_conclusion = false",
            "phasor_rms, not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in text:
                failures.append(f"v2 preview training doc missing: {required}")
        for bad in [
            "emt validation completed",
            "engineering-grade protection completed",
            "production ready",
            "is a final dynamic performance conclusion",
        ]:
            if bad in text:
                failures.append(f"v2 preview training doc contains overstatement: {bad}")

    preview_doc = ROOT / "docs/ieee39_dynamic_aware_reranker_preview_training.md"
    if preview_doc.exists():
        text = _read_text("docs/ieee39_dynamic_aware_reranker_preview_training.md").lower()
        for required in [
            "preview dynamic-aware reranker training",
            "not a final dynamic performance conclusion",
            "phasor_rms, not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "pilot breaker-like",
            "not engineering-grade protection",
            "do not commit `.slx`",
            "raw trajectories",
            "full timeseries",
        ]:
            if required not in text:
                failures.append(f"IEEE39 dynamic-aware reranker preview doc missing: {required}")
        for bad in [
            "emt validation completed",
            "engineering-grade protection completed",
            "production ready",
            "is a final dynamic performance conclusion",
        ]:
            if bad in text:
                failures.append(f"IEEE39 dynamic-aware reranker preview doc contains overstatement: {bad}")

    handwired_summary = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_validation_summary.json"
    if handwired_summary.exists():
        try:
            import json

            payload = json.loads(handwired_summary.read_text(encoding="utf-8"))
            for required in ["handwired_model_found", "handwired_model_loadable", "breaker_block_found", "trip_command_found", "validation_passed", "validation_failure_reason", "handwired_model_committed"]:
                if required not in payload:
                    failures.append(f"Handwired validation summary missing key: {required}")
            if payload.get("handwired_model_committed", True):
                failures.append("Handwired validation summary must record handwired_model_committed=false.")
        except Exception as exc:
            failures.append(f"Failed to read handwired validation summary: {exc}")

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

    dependency_doc = ROOT / "docs/ieee39_gcn_dependency_blocker_diagnosis.md"
    dependency_summary = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis/gcn_dependency_diagnosis_summary.json"
    dependency_summary_md = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis/gcn_dependency_diagnosis_summary.md"
    dependency_summary_csv = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis/gcn_dependency_diagnosis_summary.csv"
    dependency_env = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis/python_environment_probe.json"
    dependency_torch = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis/torch_import_probe.json"
    dependency_pyg = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis/torch_geometric_import_probe.json"
    dependency_path = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis/windows_path_dll_probe.json"
    dependency_plan = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis/gcn_dependency_repair_plan.json"
    dependency_required = [
        dependency_doc,
        dependency_summary,
        dependency_summary_md,
        dependency_summary_csv,
        dependency_env,
        dependency_torch,
        dependency_pyg,
        dependency_path,
        dependency_plan,
    ]
    existing_dependency_required = [path for path in dependency_required if path.exists()]
    if existing_dependency_required:
        missing_dependency_required = [path for path in dependency_required if not path.exists()]
        if missing_dependency_required:
            failures.append(
                "Dependency diagnosis artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_dependency_required)
            )
        try:
            payload = _read_json_path(dependency_summary)
            for key, expected in [
                ("diagnosis_scope", "dependency_diagnosis_only"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_run", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("dependency_repair_plan_generated", True),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_gcn_audit_now", False),
            ]:
                if payload.get(key) != expected:
                    failures.append(f"Dependency diagnosis summary must set {key}={expected!r}.")
            for key in [
                "previous_gcn_dependency_status",
                "torch_spec_present",
                "torch_import_ok",
                "torch_geometric_spec_present",
                "torch_geometric_import_ok",
                "suspicious_path_entries",
                "drive_relative_path_entries",
                "likely_winerror87_path_cause",
                "gcn_dependency_blocker_still_present",
                "recommended_next_step",
            ]:
                if key not in payload:
                    failures.append(f"Dependency diagnosis summary missing key: {key}")
        except Exception as exc:
            failures.append(f"Failed to read dependency diagnosis summary: {exc}")

        try:
            path_payload = _read_json_path(dependency_path)
            if path_payload.get("probe_scope") != "windows_path_dll_diagnosis_only":
                failures.append("Windows PATH DLL probe must set probe_scope=windows_path_dll_diagnosis_only.")
            for key in ["recommended_path_fix", "drive_relative_prefix_fields"]:
                if key not in path_payload:
                    failures.append(f"Windows PATH DLL probe missing key: {key}")
        except Exception as exc:
            failures.append(f"Failed to read Windows PATH DLL probe: {exc}")

        try:
            plan_payload = _read_json_path(dependency_plan)
            for key in [
                "route_a_path_dll_cleanup_first",
                "route_b_clean_virtualenv",
                "route_c_conda_optional",
                "verification_commands",
                "prohibited_actions",
            ]:
                if key not in plan_payload:
                    failures.append(f"Dependency repair plan missing key: {key}")
            verification_text = "\n".join(plan_payload.get("verification_commands", []))
            for required in [
                "import torch",
                "import torch_geometric",
                "diagnose_ieee39_gcn_dependency_blocker.py",
                "run_ieee39_strict_no_leakage_gcn_usefulness_audit.py",
            ]:
                if required not in verification_text:
                    failures.append(f"Dependency repair plan verification commands missing: {required}")
        except Exception as exc:
            failures.append(f"Failed to read dependency repair plan: {exc}")

        dependency_text = "\n".join(
            [
                _read_text("docs/ieee39_gcn_dependency_blocker_diagnosis.md"),
                _read_text("docs/gcn_pio_validation_log.md"),
            ]
        ).lower()
        for required in [
            "dependency diagnosis only",
            "did not train gcn",
            "did not rerun the formal gcn usefulness audit",
            "did not run simulink",
            "winerror 87",
            "e:bin",
            "phasor_rms is not emt",
            "generator_speed_proxy is not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in dependency_text:
                failures.append(f"Dependency diagnosis docs missing: {required}")
        for bad in [
            "gcn is useful",
            "gcn is useless",
            "emt validation completed",
            "generator_speed_proxy is direct frequency",
        ]:
            if bad in dependency_text:
                failures.append(f"Dependency diagnosis docs contain overstatement: {bad}")

    repair_doc = ROOT / "docs/ieee39_gcn_dependency_repair.md"
    repair_summary = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair/gcn_dependency_repair_summary.json"
    repair_summary_md = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair/gcn_dependency_repair_summary.md"
    repair_summary_csv = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair/gcn_dependency_repair_summary.csv"
    repair_venv = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair/venv_creation_report.json"
    repair_torch = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair/torch_install_verify_report.json"
    repair_pyg = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair/torch_geometric_install_verify_report.json"
    repair_post = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair/post_repair_dependency_diagnosis_report.json"
    repair_required = [
        repair_doc,
        repair_summary,
        repair_summary_md,
        repair_summary_csv,
        repair_venv,
        repair_torch,
        repair_pyg,
        repair_post,
    ]
    existing_repair_required = [path for path in repair_required if path.exists()]
    if existing_repair_required:
        missing_repair_required = [path for path in repair_required if not path.exists()]
        if missing_repair_required:
            failures.append(
                "Dependency repair artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_repair_required)
            )
        try:
            payload = _read_json_path(repair_summary)
            for key, expected in [
                ("repair_scope", "local_dependency_environment_repair"),
                ("gcn_training_run", False),
                ("formal_gcn_audit_run", False),
                ("simulink_run", False),
                ("labels_exported", False),
                ("reranker_retrained", False),
                ("production_model_saved", False),
                ("torch_install_attempted", True),
                ("torch_geometric_install_attempted", True),
                ("should_train_gcn_now", False),
                ("should_rerun_formal_gcn_audit_now", False),
            ]:
                if payload.get(key) != expected:
                    failures.append(f"Dependency repair summary must set {key}={expected!r}.")
            for key in [
                "new_venv_path",
                "new_python_executable",
                "new_sys_prefix",
                "new_python_prefix_is_absolute",
                "new_python_prefix_is_not_bare_drive",
                "torch_import_ok",
                "torch_geometric_import_ok",
                "dependency_blocker_resolved",
                "recommended_next_step",
            ]:
                if key not in payload:
                    failures.append(f"Dependency repair summary missing key: {key}")
        except Exception as exc:
            failures.append(f"Failed to read dependency repair summary: {exc}")

        repair_text = "\n".join(
            [
                _read_text("docs/ieee39_gcn_dependency_repair.md"),
                _read_text("docs/gcn_pio_validation_log.md"),
            ]
        ).lower()
        for required in [
            "local dependency environment repair",
            "did not train gcn",
            "did not run the formal gcn audit",
            "did not run simulink",
            "did not export labels",
            "sys.prefix = e:",
            "e:bin",
            "phasor_rms is not emt",
            "generator_speed_proxy is not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in repair_text:
                failures.append(f"Dependency repair docs missing: {required}")
        for bad in [
            "gcn is useful",
            "gcn is useless",
            "formal gcn audit rerun completed",
            "emt validation completed",
            "generator_speed_proxy is direct frequency",
        ]:
            if bad in repair_text:
                failures.append(f"Dependency repair docs contain overstatement: {bad}")

    consistency_doc = ROOT / "docs/ieee39_gcn_dependency_repair_consistency_check.md"
    consistency_json = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair_consistency_check/dependency_repair_consistency_check.json"
    consistency_md = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair_consistency_check/dependency_repair_consistency_check.md"
    consistency_required = [consistency_doc, consistency_json, consistency_md]
    existing_consistency_required = [path for path in consistency_required if path.exists()]
    if existing_consistency_required:
        missing_consistency_required = [path for path in consistency_required if not path.exists()]
        if missing_consistency_required:
            failures.append(
                "Dependency repair consistency artifacts are partially present but incomplete:\n"
                + "\n".join(f"  - missing {path.relative_to(ROOT)}" for path in missing_consistency_required)
            )
        try:
            payload = _read_json_path(consistency_json)
            for key, expected in [
                ("check_scope", "dependency_repair_consistency_check"),
                ("gcn_training_run", True),
                ("formal_gcn_audit_run", True),
                ("simulink_run", False),
                ("labels_exported", False),
                ("reranker_retrained", False),
                ("dependency_blocker_resolved", True),
                ("formal_audit_rerun_after_repair", True),
                ("execution_summary_still_baseline_only", False),
                ("execution_doc_matches_execution_summary", True),
                ("premature_gcn_conclusion_removed", True),
                ("final_engineering_conclusion", False),
                ("should_rerun_strict_no_leakage_audit_next", False),
                ("should_deploy_model", False),
                ("should_retrain_reranker_now", False),
            ]:
                if payload.get(key) != expected:
                    failures.append(f"Dependency repair consistency check must set {key}={expected!r}.")
            if payload.get("failed_checks") != []:
                failures.append("Dependency repair consistency check must have failed_checks=[].")
        except Exception as exc:
            failures.append(f"Failed to read dependency repair consistency check: {exc}")

        try:
            execution_summary = _read_json_path(
                ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_execution/gcn_usefulness_audit_execution_summary.json"
            )
            if execution_summary.get("gcn_trained_for_audit") is True:
                if execution_summary.get("gcn_dependency_status") != "torch_and_torch_geometric_available":
                    failures.append("Post-repair audit execution summary must record torch_and_torch_geometric_available when GCN training is reported.")
            else:
                if execution_summary.get("gcn_dependency_status") != "blocked_by_missing_gcn_dependency":
                    failures.append("Baseline-only audit execution summary must explain why GCN training was not run.")
            if execution_summary.get("final_engineering_conclusion") is not False:
                failures.append("Post-repair audit execution summary must keep final_engineering_conclusion=false.")
            if execution_summary.get("should_deploy_model") is not False:
                failures.append("Post-repair audit execution summary must keep should_deploy_model=false.")
            if execution_summary.get("should_retrain_reranker_now") is not False:
                failures.append("Post-repair audit execution summary must keep should_retrain_reranker_now=false.")
        except Exception as exc:
            failures.append(f"Failed to read existing audit execution summary: {exc}")

        consistency_text = "\n".join(
            [
                _read_text("docs/ieee39_gcn_dependency_repair_consistency_check.md"),
                _read_text("docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md"),
                _read_text("docs/ieee39_gcn_dependency_repair.md"),
                _read_text("docs/gcn_pio_validation_log.md"),
            ]
        ).lower()
        for required in [
            "dependency repair consistency check",
            "dependency_blocker_resolved = true",
            "formal_audit_rerun_after_repair = true",
            "execution_summary_still_baseline_only = false",
            "premature_gcn_conclusion_removed = true",
            "audit-level evidence",
            "phasor_rms",
            "not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "not engineering-grade protection",
        ]:
            if required not in consistency_text:
                failures.append(f"Dependency repair consistency docs missing: {required}")
        for bad in [
            "gcn is useful",
            "gcn is not useful",
            "final gcn conclusion",
            "emt validation completed",
            "generator_speed_proxy is direct frequency",
        ]:
            if bad in consistency_text:
                failures.append(f"Dependency repair consistency docs contain overstatement: {bad}")

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
