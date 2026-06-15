# IEEE39 B39 Temp Smoke Quality Review

This artifact reviews the already completed B39 temporary bus-fault smoke. This
round does not run Simulink, does not submit `.slx`, does not export labels,
does not train GCN, and does not retrain the reranker.

## Result

- target_bus: `B39`
- scenario_id: `BF_B39_TEMP_SMOKE`
- simulation_success: `true`
- physical_fault_or_breaker_action_executed: `true`
- measurement_extraction_status: `voltage_speed_angle`
- training_ready_candidate_smoke: `true`
- signal_source_has_frequency_proxy: `true`
- min_voltage_pu: `0.000160777190390721`
- max_voltage_pu: `1.0635`
- min_frequency_hz: `49.7327386072042`
- max_frequency_hz: `50.1408910900975`
- max_speed_deviation: `0.00534522785591696`
- max_rotor_angle_separation_deg: `73.905967084859`
- min_voltage_near_zero: `true`
- unstable_flag: `true`

The near-zero minimum voltage is expected for a close-in three-phase bus-fault
candidate. It is a severe disturbance indicator, but it is not a final
stability conclusion. The `unstable_flag = true` value is plausible for this
severe B39 temporary smoke, but it should be treated as a candidate record
until a separate export review.

## Quality Gate

The quality review passes for candidate export because all required smoke
quality inputs are available and finite, the dynamic measurement status is
`voltage_speed_angle`, and the signal source summary includes
`frequency=generator_speed_proxy`.

- quality_review_passed_for_candidate_export: `true`
- recommended_next_step:
  `export B39 bus-fault candidate label in a separate round, without training`

## Boundaries

- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`
- source_slx_modified: `false`
- temporary_slx_committed: `false`
- l12_touched: `false`
- old formal gate remains `35 / 33 / 33`
- v2 candidate count remains `40`
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
