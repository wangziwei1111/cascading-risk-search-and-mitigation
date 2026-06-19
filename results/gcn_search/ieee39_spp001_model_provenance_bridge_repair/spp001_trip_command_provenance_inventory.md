# IEEE39 SPP001 Trip Command Provenance Inventory

## searched_artifacts
```json
[
  "results\\gcn_search\\ieee39_spp001_single_pair_smoke_rerun\\spp001_rerun_summary.json",
  "results\\gcn_search\\ieee39_spp001_single_pair_smoke_rerun\\spp001_rerun_result.json",
  "results\\gcn_search\\ieee39_l15_handwired_validation_readiness_repair\\repaired_combined_validation_preview.csv",
  "results\\gcn_search\\ieee39_l15_handwired_validation_readiness_repair\\spp001_rerun_readiness_gate.json",
  "results\\gcn_search\\ieee39_matlab_selected_pair_entrypoint_repair\\single_pair_smoke_execution_contract.json",
  "results\\gcn_search\\ieee39_matlab_selected_pair_entrypoint_repair\\entrypoint_component_reuse_report.json",
  "results\\gcn_search\\ieee39_graphical_dynamic_model\\handwired_breaker_validation\\ieee39_multi_handwired_breaker_validation_summary.csv",
  "results\\gcn_search\\ieee39_graphical_dynamic_model\\handwired_breaker_validation\\ieee39_clean_breaker_lab_batch_validation_summary.csv",
  "results\\gcn_search\\ieee39_graphical_dynamic_model\\fault_tests\\ieee39_clean_breaker_lab_batch_line_trip_summary.csv"
]
```

## l15_trip_command_candidates
```json
[
  {
    "line_id": "L15",
    "trip_command_path": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/L15_TripCommand",
    "trip_command_model_source": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15",
    "validation_passed": true,
    "source_artifact": "results\\gcn_search\\ieee39_graphical_dynamic_model\\handwired_breaker_validation\\ieee39_clean_breaker_lab_batch_validation_summary.csv",
    "readiness_status": "ready",
    "provenance": "existing evidence; no Simulink run in this repair round"
  },
  {
    "line_id": "L15",
    "trip_command_path": "",
    "trip_command_model_source": null,
    "validation_passed": false,
    "source_artifact": "results\\gcn_search\\ieee39_graphical_dynamic_model\\fault_tests\\ieee39_clean_breaker_lab_batch_line_trip_summary.csv",
    "readiness_status": "not_ready",
    "provenance": "existing evidence; no Simulink run in this repair round"
  }
]
```

## l04_trip_command_candidates
```json
[
  {
    "line_id": "L04",
    "trip_command_path": "IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker/Grid/L04_TripCommand",
    "trip_command_model_source": "IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker",
    "validation_passed": true,
    "source_artifact": "results\\gcn_search\\ieee39_graphical_dynamic_model\\handwired_breaker_validation\\ieee39_multi_handwired_breaker_validation_summary.csv",
    "readiness_status": "ready",
    "provenance": "existing evidence; no Simulink run in this repair round"
  }
]
```

## loaded_wrapper_candidates
```json
[
  {
    "wrapper_model_source": "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx",
    "wrapper_model_name": "IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker",
    "source_artifact": "results\\gcn_search\\ieee39_matlab_selected_pair_entrypoint_repair\\entrypoint_component_reuse_report.json"
  }
]
```

## same_wrapper_candidates
```json
[]
```

## rejected_candidates
```json
[
  {
    "reason": "L15 TripCommand path belongs to the clean-lab L15 model, not the loaded handwired breaker wrapper",
    "l15_selected_model": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15",
    "l04_selected_model": "IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker",
    "loaded_wrapper_model": "IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker"
  }
]
```

- `selected_candidate_if_any`: None
- `reason_not_selected_if_any`: L15 TripCommand path belongs to the clean-lab L15 model, not the loaded handwired breaker wrapper
