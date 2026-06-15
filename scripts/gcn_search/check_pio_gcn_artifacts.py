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
    ".pt",
    ".npz",
    ".pkl",
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


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


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
            "v2 candidate count remains `40`",
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
            "v2 candidate count remains `40`",
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
                        "source_model_saved",
                        "temporary_model_committed",
                    ]:
                        if template.get(key) is not False:
                            failures.append(f"Manual bus-fault template {target_bus} must default {key}=false.")
                    if template.get("next_action") != "manual review required before smoke":
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
