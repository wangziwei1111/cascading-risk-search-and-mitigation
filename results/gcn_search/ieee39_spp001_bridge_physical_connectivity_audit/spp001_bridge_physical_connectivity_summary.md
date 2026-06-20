# IEEE39 SPP001 Bridge Physical Connectivity Summary

- `audit_scope`: spp001_bridge_physical_connectivity_audit
- `gcn_training_run`: False
- `formal_gcn_audit_rerun`: False
- `spp001_smoke_executed`: False
- `selected_32_batch_executed`: False
- `full_1056_generation_run`: False
- `labels_exported`: False
- `formal_labels_exported`: False
- `reranker_retrained`: False
- `production_model_saved`: False
- `source_solver_runtime_diagnosis_commit`: b049b41c7ee6d6824264cb4da4bfa6e1b308bf78
- `pair_id`: SPP001
- `prior_outaged_branch`: L15
- `candidate_next_branch`: L04
- `local_bridge_loaded_for_static_audit`: True
- `source_slx_modified`: False
- `l15_trip_command_block_exists`: True
- `l15_breaker_block_exists`: True
- `l15_trip_command_to_breaker_control_connected`: False
- `l15_breaker_physical_ports_connected`: False
- `l15_breaker_in_series_with_actual_l15_branch`: False
- `l04_trip_command_block_exists`: True
- `l04_breaker_block_exists`: True
- `l04_trip_command_to_breaker_control_connected`: True
- `l04_breaker_physical_ports_connected`: True
- `l04_breaker_in_series_with_actual_l04_branch`: False
- `unconnected_physical_ports_detected`: True
- `unconnected_control_ports_detected`: True
- `physical_bridge_valid`: False
- `same_wrapper_block_presence_only`: True
- `can_run_initialization_profile_after_manual_approval`: False
- `can_run_full_spp001_smoke_after_manual_approval`: False
- `no_label_value_generated`: True
- `raw_trajectories_committed`: False
- `full_timeseries_committed`: False
- `mat_files_committed`: False
- `slx_files_committed`: False
- `local_bridge_committed`: False
## forbidden_features_detected_in_inputs
```json
[]
```

- `no_leakage_policy_passed`: True
- `matlab_returncode`: 0
- `matlab_timeout`: False
- `sim_called`: False
- `blocker_if_any`: SPP001 bridge physical connectivity is not proven by static port/line audit; block presence alone is insufficient
- `recommended_next_step`: freeze SPP001 dynamic pair extension; do not run further solver profiles; continue core paper-aligned GCN work using offline sequential labels and existing single-line dynamic validation
