# IEEE39 SPP001 Bridge Component Plan

- `plan_scope`: spp001_same_wrapper_bridge_component_plan
- `pair_id`: SPP001
- `source_base_wrapper`: results\gcn_search\ieee39_graphical_dynamic_model\generated_models\IEEE39BusSystem_dynamic_experiment_wrapper.slx
- `fallback_handwired_wrapper`: results\gcn_search\ieee39_graphical_dynamic_model\generated_models\IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx
- `matlab_builder_skeleton`: matlab\simulink_ieee39\prepare_ieee39_spp001_same_wrapper_bridge_lab.m
- `local_lab_copy_path_planned`: results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/local_lab_copy/IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab.slx
## required_trip_commands
```json
[
  "L15_TripCommand",
  "L04_TripCommand"
]
```

## required_breaker_blocks
```json
[
  "L15_HandwiredTimedBreaker",
  "L04_HandwiredTimedBreaker"
]
```

- `trip_command_name_conflict`: False
- `local_lab_copy_only`: True
- `source_slx_modified`: False
- `simulink_run`: False
- `formal_labels_exported`: False
- `notes`: Build in a future approved round only; this dry-run does not create or commit .slx files.
