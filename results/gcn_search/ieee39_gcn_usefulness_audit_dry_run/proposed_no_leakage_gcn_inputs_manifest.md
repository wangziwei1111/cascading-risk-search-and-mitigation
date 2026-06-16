# Proposed No-Leakage GCN Inputs Manifest

- proposed_input_columns: `["fault_type", "duration_s", "fault_start_s", "fault_clear_s", "trip_implementation", "line_id", "target_bus", "target_bus_or_component", "source_model_type"]`
- forbidden_columns_checked: `["min_voltage_pu", "max_voltage_pu", "min_frequency_hz", "max_frequency_hz", "max_speed_deviation", "max_rotor_angle_separation_deg", "measurement_extraction_status", "unstable_flag", "dynamic_stress_score", "trip_time_s", "signal_source_summary", "output_summary_path", "output_event_log_path", "formal_line_trip_label", "handwired_line_trip_label", "non_line_trip_label", "bus_fault_label", "temporary_smoke_candidate", "candidate_not_formal_label", "training_ready_label_v2", "training_ready_candidate", "training_ready_candidate_smoke", "training_ready_label_candidate"]`
- forbidden_columns_present: `[]`
- allowed_columns_present: `["fault_type", "duration_s", "fault_start_s", "fault_clear_s", "trip_implementation", "line_id", "target_bus", "target_bus_or_component", "source_model_type"]`
- conditionally_allowed_columns: `["target_bus", "target_bus_or_component", "duration_s", "fault_start_s", "fault_clear_s"]`
- target_bus_memorization_risk: `true`
- mitigation: `compare against target-bus-only baseline and topology-only baseline`
- post_fault_dynamic_measurement_features_excluded: `true`
- label_derived_features_excluded: `true`
- target_columns_excluded: `true`

## Proposed Input Columns

- `fault_type`
- `duration_s`
- `fault_start_s`
- `fault_clear_s`
- `trip_implementation`
- `line_id`
- `target_bus`
- `target_bus_or_component`
- `source_model_type`

## Forbidden Columns Checked

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

## Allowed Columns Present

- `fault_type`
- `duration_s`
- `fault_start_s`
- `fault_clear_s`
- `trip_implementation`
- `line_id`
- `target_bus`
- `target_bus_or_component`
- `source_model_type`

## Conditionally Allowed Columns

- `target_bus` / `target_bus_or_component` only with explicit target-bus-only baseline comparison
- `duration_s` / `fault_start_s` / `fault_clear_s` only as intervention design variables
