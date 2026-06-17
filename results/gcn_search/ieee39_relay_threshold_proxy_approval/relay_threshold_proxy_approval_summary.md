# IEEE39 Relay Threshold Proxy Approval Summary

- `approval_scope`: relay_threshold_proxy_approval
- `gcn_training_run`: False
- `formal_gcn_audit_rerun`: False
- `simulink_run`: False
- `labels_exported`: False
- `reranker_retrained`: False
- `production_model_saved`: False
- `source_static_feature_commit`: a29bc6e209afe764aa8bf57613d66dd53114fba9
- `relay_threshold_source_ready`: False
- `relay_threshold_proxy_approved`: True
- `relay_threshold_proxy_allowed_for_audit_only_prototype`: True
- `relay_threshold_proxy_allowed_for_production`: False
- `proxy_formula`: beta * RATE_A
- `beta_value`: 1.2
- `beta_value_source`: project default beta = 1.2
- `line_limit_source`: pypower.case39 branch RATE_A
- `branch_flow_source_ready`: True
- `line_limit_source_ready`: True
- `bus_load_source_ready`: True
- `can_build_required_paper_features_without_proxy`: False
- `can_build_required_paper_features_with_approved_proxy`: True
- `can_build_l01_l34_paper_feature_matrix_with_proxy`: True
## forbidden_features_detected_in_inputs
```json
[]
```

- `no_leakage_policy_passed`: True
- `l12_special_case_preserved`: True
- `final_engineering_conclusion`: False
- `should_train_gcn_now`: False
- `should_rerun_formal_audit_now`: False
- `should_retrain_reranker_now`: False
- `should_deploy_model`: False
- `recommended_next_step`: prepare paper-style branch vulnerability label generator dry-run for line-trip labels
- `source_proxy_was_previously_allowed_for_training_now`: False
