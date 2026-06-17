# IEEE39 Static Case Source Inventory

- `inventory_scope`: ieee39_static_operating_point_source_inventory
## repository_case_sources_found
```json
[
  "docs/ieee39_all_remaining_bus_fault_batch_actual_smoke.md",
  "docs/ieee39_all_remaining_bus_fault_batch_readiness_dry_run.md",
  "docs/ieee39_all_remaining_bus_fault_batch_smoke_quality_review.md",
  "docs/ieee39_all_remaining_bus_fault_candidate_label_export.md",
  "docs/ieee39_all_remaining_bus_fault_manual_connection_evidence.md",
  "docs/ieee39_all_remaining_bus_fault_manual_wiring_plan.md",
  "docs/ieee39_b26_bus_fault_candidate_label_export.md",
  "docs/ieee39_b26_manual_bus_fault_review_result.md",
  "docs/ieee39_b26_manual_bus_fault_verification_plan.md",
  "docs/ieee39_b26_temp_smoke_quality_review.md",
  "docs/ieee39_b26_temp_smoke_readiness.md",
  "docs/ieee39_b26_temporary_bus_fault_smoke.md",
  "docs/ieee39_b39_bus_fault_candidate_label_export.md",
  "docs/ieee39_b39_temp_smoke_quality_review.md",
  "docs/ieee39_b39_temp_smoke_readiness.md",
  "docs/ieee39_b39_temporary_bus_fault_smoke.md",
  "docs/ieee39_batch_per_line_clean_breaker_lab_workflow.md",
  "docs/ieee39_bus_fault_b39_manual_review_result.md",
  "docs/ieee39_bus_fault_gui_manual_checklist.md",
  "docs/ieee39_bus_fault_smoke_tests.md",
  "docs/ieee39_bus_fault_temp_lab_injection.md",
  "docs/ieee39_clean_breaker_lab_workflow.md",
  "docs/ieee39_dynamic_aware_reranker_preview_training.md",
  "docs/ieee39_dynamic_aware_reranker_v2_preview_training.md",
  "docs/ieee39_dynamic_aware_stricter_independent_test_comparison.md",
  "docs/ieee39_fault_breaker_relay_wrapper.md",
  "docs/ieee39_gcn_audit_evidence_diagnosis.md",
  "docs/ieee39_gcn_dependency_blocker_diagnosis.md",
  "docs/ieee39_gcn_dependency_repair.md",
  "docs/ieee39_gcn_dependency_repair_consistency_check.md",
  "docs/ieee39_gcn_usefulness_audit_dry_run_validator.md",
  "docs/ieee39_gcn_usefulness_audit_plan.md",
  "docs/ieee39_graphical_dynamic_model_plan.md",
  "docs/ieee39_graphical_dynamic_model_selection.md",
  "docs/ieee39_graphical_dynamic_model_status.md",
  "docs/ieee39_handwired_breaker_validation.md",
  "docs/ieee39_l12_islanding_timeout_case.md",
  "docs/ieee39_line_map_extension_workflow.md",
  "docs/ieee39_measurement_extraction_and_timed_trip.md",
  "docs/ieee39_multi_handwired_breaker_expansion.md",
  "docs/ieee39_non_line_trip_fault_smoke_tests.md",
  "docs/ieee39_non_line_trip_fault_type_expansion.md",
  "docs/ieee39_non_line_trip_label_export.md",
  "docs/ieee39_paper_aligned_branch_gcn_redesign_consistency_check.md",
  "docs/ieee39_paper_aligned_branch_gcn_redesign_dry_run.md",
  "docs/ieee39_paper_aligned_feature_source_dry_run.md",
  "docs/ieee39_per_line_clean_breaker_lab_workflow.md",
  "docs/ieee39_real_fault_execution_status.md",
  "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md",
  "docs/ieee39_timed_breaker_manual_wiring_guide.md",
  "docs/ieee39_timed_line_trip_probe_status.md",
  "docs/ieee39_v2_plus_all_bus_fault_no_training_composition_review.md",
  "docs/ieee39_v2_plus_all_bus_fault_preview_no_leakage_comparison.md",
  "docs/ieee39_v2_plus_b39_b26_no_training_composition_review.md",
  "docs/ieee39_v2_plus_b39_b26_preview_no_leakage_comparison.md",
  "docs/ieee39_v2_plus_b39_no_training_composition_review.md",
  "docs/ieee39_v2_plus_b39_preview_interpretation.md",
  "docs/ieee39_v2_plus_b39_preview_training.md",
  "matlab/simulink_ieee39/add_ieee39_basic_relay_proxy.m",
  "matlab/simulink_ieee39/check_ieee39_model_toolboxes.m",
  "matlab/simulink_ieee39/configure_ieee39_pilot_line_trip_case.m",
  "matlab/simulink_ieee39/configure_ieee39_short_filegen_paths.m",
  "matlab/simulink_ieee39/configure_ieee39_three_phase_fault_case.m",
  "matlab/simulink_ieee39/extract_ieee39_signal_summary.m",
  "matlab/simulink_ieee39/find_compatible_ieee39_breaker_blocks.m",
  "matlab/simulink_ieee39/insert_ieee39_timed_line_switch.m",
  "matlab/simulink_ieee39/inspect_ieee39_line_ports.m",
  "matlab/simulink_ieee39/inspect_ieee39_wrapper_grid_line_blocks.m",
  "matlab/simulink_ieee39/inventory_ieee39_simlog_tree.m",
  "matlab/simulink_ieee39/map_ieee39_lines_and_breakers.m",
  "matlab/simulink_ieee39/prepare_ieee39_bus_fault_temp_lab_copy.m",
  "matlab/simulink_ieee39/prepare_ieee39_clean_handwired_breaker_lab.m",
  "matlab/simulink_ieee39/prepare_ieee39_clean_handwired_breaker_lab_for_line.m",
  "matlab/simulink_ieee39/prepare_ieee39_clean_handwired_breaker_labs_for_lines.m",
  "matlab/simulink_ieee39/probe_ieee39_breaker_insertion_standalone.m",
  "matlab/simulink_ieee39/run_ieee39_fault_test_suite.m",
  "matlab/simulink_ieee39/run_ieee39_multi_handwired_line_trip_suite.m",
  "matlab/simulink_ieee39/setup_ieee39_dynamic_experiment_wrapper.m",
  "matlab/simulink_ieee39/validate_ieee39_clean_breaker_lab_line.m",
  "matlab/simulink_ieee39/validate_ieee39_clean_breaker_lab_lines_batch.m"
]
```

## installed_case_loaders_found
```json
[
  {
    "module": "pandapower.networks",
    "available": true,
    "error": null,
    "version": null
  },
  {
    "module": "pypower.case39",
    "available": true,
    "error": null,
    "version": null
  },
  {
    "module": "numpy",
    "available": true,
    "error": null,
    "version": "2.3.4"
  },
  {
    "module": "scipy",
    "available": true,
    "error": null,
    "version": "1.16.3"
  }
]
```

- `selected_case_source`: pypower.case39
- `selected_case_source_trust_level`: standard_installed_case_loader_static_pre_fault
- `selected_case_source_provenance`: Loaded with local pypower.case39; no repository parameters were hand-written.
- `baseMVA_available`: True
- `bus_table_available`: True
- `branch_table_available`: True
- `generator_table_available`: True
- `branch_flow_available`: True
- `branch_limit_available`: True
- `bus_load_available`: True
- `can_generate_dc_power_flow`: True
- `source_blocker_if_any`: None
