# IEEE39 SPP001 Bridge Builder Repair Summary

- `repair_scope`: spp001_same_wrapper_bridge_builder_repair
- `gcn_training_run`: False
- `formal_gcn_audit_rerun`: False
- `spp001_smoke_executed`: False
- `selected_32_batch_executed`: False
- `full_1056_generation_run`: False
- `simulink_run`: False
- `labels_exported`: False
- `formal_labels_exported`: False
- `reranker_retrained`: False
- `production_model_saved`: False
- `source_local_validation_commit`: 391a67f1e380d167b39779bfd06c161519eefdfc
- `pair_id`: SPP001
- `prior_outaged_branch`: L15
- `candidate_next_branch`: L04
- `previous_l15_trip_command_found_in_bridge`: False
- `previous_l04_trip_command_found_in_bridge`: True
- `local_bridge_build_attempted`: True
- `local_bridge_validation_attempted`: True
- `local_bridge_built`: True
- `local_bridge_committed`: False
- `source_slx_modified`: False
- `l15_trip_command_found_in_bridge`: True
- `l04_trip_command_found_in_bridge`: True
- `l15_breaker_found_in_bridge`: True
- `l04_breaker_found_in_bridge`: True
- `same_wrapper_confirmed`: True
- `repaired_provenance_manifest_written`: True
- `can_rerun_spp001_after_manual_approval`: True
- `no_label_value_generated`: True
- `raw_trajectories_committed`: False
- `full_timeseries_committed`: False
- `mat_files_committed`: False
- `slx_files_committed`: False
## forbidden_features_detected_in_inputs
```json
[]
```

- `no_leakage_policy_passed`: True
- `blocker_if_any`: None
- `recommended_next_step`: approve rerun of SPP001 single-pair smoke using repaired same-wrapper bridge in a separate round; do not export labels or train
## local_bridge_validation_detail
```json
{
  "local_bridge_path": "results\\gcn_search\\ieee39_spp001_same_wrapper_bridge_builder_repair\\local_bridge_copy\\IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab.slx",
  "local_bridge_file_exists": true,
  "local_bridge_model_name": "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab",
  "l15_trip_command_found_in_bridge": true,
  "l04_trip_command_found_in_bridge": true,
  "l15_breaker_found_in_bridge": true,
  "l04_breaker_found_in_bridge": true,
  "l15_trip_command_path_in_bridge": "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/L15_TripCommand",
  "l04_trip_command_path_in_bridge": "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/L04_TripCommand",
  "same_wrapper_confirmed": true,
  "blocker_if_any": null
}
```
