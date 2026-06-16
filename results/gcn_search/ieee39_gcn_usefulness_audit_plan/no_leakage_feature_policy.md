# IEEE39 No-Leakage Feature Policy

This file defines the future GCN usefulness audit feature boundary.

## Forbidden Post-Fault Dynamic Measurement Features

- `min_voltage_pu`
- `max_voltage_pu`
- `min_frequency_hz`
- `max_frequency_hz`
- `max_speed_deviation`
- `max_rotor_angle_separation_deg`
- `measurement_extraction_status`
- `unstable_flag`
- `dynamic_stress_score`
- `trip_time_s`
- `signal_source_summary`
- `output_summary_path`
- `output_event_log_path`

## Forbidden Label-Derived Features

- `formal_line_trip_label`
- `handwired_line_trip_label`
- `non_line_trip_label`
- `bus_fault_label`
- `temporary_smoke_candidate`
- `candidate_not_formal_label`
- `training_ready_label_v2`
- `training_ready_candidate`
- `training_ready_candidate_smoke`
- `training_ready_label_candidate`

## Allowed Input Categories

- network topology / graph structure
- line_id / target_bus metadata encoded without target leakage
- pre-fault static electrical metadata if available
- disturbance type / planned contingency descriptor
- duration_s, fault_start_s, fault_clear_s only if treated as intervention design variables and documented

## Conditionally Allowed

- candidate family flags only if explicitly audited for leakage risk

## Proposed No-Leakage GCN Input Columns

- `fault_type`
- `duration_s`
- `fault_start_s`
- `fault_clear_s`
- `trip_implementation`
- `line_id`
- `target_bus`
- `target_bus_or_component`
- `source_model_type`

## Status

- feature_policy_passed: `true`
- include_all_79 feature set: `forbidden_for_gcn_audit`
- no_dynamic_measurement feature set: `required_baseline`
