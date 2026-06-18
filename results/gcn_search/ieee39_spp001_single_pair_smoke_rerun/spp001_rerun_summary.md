# IEEE39 SPP001 Rerun Summary

- `execution_scope`: spp001_single_pair_smoke_rerun
- `gcn_training_run`: False
- `formal_gcn_audit_rerun`: False
- `selected_32_batch_executed`: False
- `full_1056_generation_run`: False
- `labels_exported`: False
- `formal_labels_exported`: False
- `reranker_retrained`: False
- `production_model_saved`: False
- `source_entrypoint_repair_commit`: 4a8284da5ec80d91c30fe814c9823af157e37fe9
- `source_l15_readiness_repair_commit`: a648b8cb2d4fb3a4c27a5e7f3e8e588280ddc0d1
- `pair_id`: SPP001
- `state_id`: single_outage_state_L15
- `prior_outaged_branch`: L15
- `candidate_next_branch`: L04
## planned_contingency_sequence
```json
[
  "L15",
  "L04"
]
```

- `selection_bucket`: high_relay_ratio_pairs
- `l15_ready`: True
- `l04_ready`: True
- `execution_attempted`: True
- `execution_status`: failed
- `single_pair_executed`: False
- `simulink_run`: False
- `pilot_label_value`: None
- `pilot_label_status`: failed
- `dynamic_stress_score_if_available`: None
- `unstable_flag_if_available`: None
- `timeout_or_failure_reason`: single-pair smoke failed: Simulink 对象名称无效: 'IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/L15_TripCommand'。
- `pilot_label_available`: False
- `pilot_labels_are_formal_training_labels`: False
- `raw_trajectories_committed`: False
- `full_timeseries_committed`: False
- `mat_files_committed`: False
- `slx_files_committed`: False
- `slxc_files_committed`: False
- `slprj_committed`: False
- `source_slx_modified`: False
- `bus_fault_labels_used`: False
- `line_trip_labels_first_priority`: True
- `l12_special_case_preserved`: True
- `nf06_warning_preserved`: True
## forbidden_features_detected_in_inputs
```json
[]
```

- `no_leakage_policy_passed`: True
- `final_engineering_conclusion`: False
- `should_train_gcn_now`: False
- `should_rerun_formal_audit_now`: False
- `should_export_formal_labels_now`: False
- `should_retrain_reranker_now`: False
- `should_deploy_model`: False
- `blocker_if_any`: single-pair smoke failed: Simulink 对象名称无效: 'IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/L15_TripCommand'。
- `recommended_next_step`: inspect timeout/failure evidence and rerun one-pair smoke after repair
