# IEEE39 Single-Outage Label Loop Dry-Run Summary

- `dry_run_scope`: single_outage_label_loop_dry_run
- `gcn_training_run`: False
- `formal_gcn_audit_rerun`: False
- `simulink_run`: False
- `new_simulink_run`: False
- `labels_exported`: False
- `formal_labels_exported`: False
- `reranker_retrained`: False
- `production_model_saved`: False
- `source_base_state_pilot_commit`: 449f8d1e625672bb6e01fbffd59c6bb97d3d0fe0
- `paper_graph_node_type`: branch
- `paper_graph_edge_rule`: shared_endpoint_bus
- `feature_matrix_with_proxy_ready`: True
- `relay_threshold_is_proxy`: True
- `proxy_allowed_for_audit_only_prototype`: True
- `proxy_allowed_for_production`: False
- `base_state_all_available_labels_negative`: True
- `base_state_should_not_be_used_alone_for_training`: True
- `num_single_outage_states_planned`: 34
- `num_state_branch_pairs_planned`: 1122
- `num_pairs_excluded_due_to_same_branch`: 34
- `num_pairs_excluded_due_to_l12_special`: 66
- `num_pairs_planned_for_future_generation`: 1056
- `num_pairs_available_from_existing_artifacts`: 0
- `can_generate_single_outage_labels_now`: False
- `can_export_formal_single_outage_labels_now`: False
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
- `blocker_if_any`: no approved reusable single_outage_state x next_branch label artifacts are available; this round only prepares the controlled loop dry-run plan
- `recommended_next_step`: implement controlled generation runner for selected single-outage pilot pairs in a separate round
