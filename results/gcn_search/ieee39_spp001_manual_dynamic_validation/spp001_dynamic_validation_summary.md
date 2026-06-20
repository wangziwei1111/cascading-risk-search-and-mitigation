# SPP001 Dynamic Validation Summary

- `validation_scope`: spp001_manual_dynamic_validation
- `pair_id`: SPP001
- `prior_outaged_branch`: L15
- `candidate_next_branch`: L04
- `manual_bridge_build_attempted`: True
- `manual_bridge_built`: True
- `physical_bridge_valid`: True
- `static_gate_passed`: True
- `dynamic_stages_requested`: 5
- `dynamic_stages_completed`: 0
- `dynamic_stages_stopped_early`: True
- `earliest_failed_stage_if_any`: A
- `full_spp001_dynamic_validation_completed`: False
- `gcn_training_run`: False
- `formal_gcn_audit_rerun`: False
- `selected_32_batch_executed`: False
- `full_1056_generation_run`: False
- `labels_exported`: False
- `formal_labels_exported`: False
- `reranker_retrained`: False
- `production_model_saved`: False
- `pilot_label_value`: None
- `no_formal_label_generated`: True
- `raw_trajectories_committed`: False
- `full_timeseries_committed`: False
- `mat_files_committed`: False
- `slx_files_committed`: False
- `slxc_files_committed`: False
- `slprj_committed`: False
- `local_bridge_committed`: False
- `source_slx_modified`: False
- `bus_fault_labels_used`: False
## forbidden_features_detected_in_inputs
```json
[]
```

- `no_leakage_policy_passed`: True
- `blocker_if_any`: Stage A initialization timed out after the static gate passed; stopped immediately and did not run stages B-E.
- `recommended_next_step`: diagnose Stage A initialization timeout on the manual SPP001 bridge before any post-trip stage, label export, selected batch, or GCN training
