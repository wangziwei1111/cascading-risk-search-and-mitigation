# IEEE39 Single-Outage Pilot Pair Runner Dry-Run Summary

- `dry_run_scope`: single_outage_pilot_pair_runner_dry_run
- `gcn_training_run`: False
- `formal_gcn_audit_rerun`: False
- `simulink_run`: False
- `new_simulink_run`: False
- `labels_exported`: False
- `formal_labels_exported`: False
- `reranker_retrained`: False
- `production_model_saved`: False
- `source_single_outage_loop_commit`: b5e98d4fd27f438b2d46e6ec0ec60b46e21bcda9
- `feature_matrix_with_proxy_ready`: True
- `relay_threshold_is_proxy`: True
- `proxy_allowed_for_audit_only_prototype`: True
- `proxy_allowed_for_production`: False
- `base_state_should_not_be_used_alone_for_training`: True
- `num_candidate_pairs_available`: 1056
- `num_pilot_pairs_selected`: 32
- `num_high_relay_ratio_pairs`: 10
- `num_shared_bus_neighbor_pairs`: 10
- `num_non_neighbor_control_pairs`: 12
- `label_values_fabricated`: False
- `selected_pairs_label_status`: planned
- `can_execute_future_generation_runner_after_approval`: True
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
- `should_run_simulink_now`: False
- `should_export_formal_labels_now`: False
- `should_retrain_reranker_now`: False
- `should_deploy_model`: False
- `blocker_if_any`: None
- `recommended_next_step`: approve and execute selected single-outage pilot pair generation in a separate round
