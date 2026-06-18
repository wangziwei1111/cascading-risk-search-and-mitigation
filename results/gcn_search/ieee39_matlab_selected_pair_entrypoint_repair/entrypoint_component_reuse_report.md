# IEEE39 Entrypoint Component Reuse Report

## reused_matlab_components
```json
[
  "matlab/simulink_ieee39/run_ieee39_multi_handwired_line_trip_suite.m",
  "matlab/simulink_ieee39/validate_ieee39_multi_handwired_breakers.m",
  "matlab/simulink_ieee39/extract_ieee39_signal_summary.m",
  "matlab/simulink_ieee39/configure_ieee39_short_filegen_paths.m"
]
```

## reused_python_components
```json
[
  "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
  "scripts/gcn_search/parse_ieee39_selected_pair_execution_evidence.py"
]
```

- `available_wrapper_model_source`: results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx
- `available_line_mapping_source`: results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv
- `two_step_sequence_strategy`: set prior TripCommand time first, set candidate TripCommand time later, set all other validated trip commands far in the future
## remaining_missing_components
```json
[]
```

## unsafe_components_rejected
```json
[
  "full 1056 batch generation",
  "formal label export",
  "raw trajectory or full timeseries persistence",
  "source SLX modification"
]
```

- `source_slx_modified`: False
