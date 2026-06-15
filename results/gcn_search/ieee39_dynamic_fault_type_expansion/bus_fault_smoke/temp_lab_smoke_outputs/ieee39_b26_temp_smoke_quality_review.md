# IEEE39 B26 Temp Smoke Quality Review

This is a quality review of the already completed B26 temporary bus-fault smoke.
It does not run Simulink, does not submit `.slx`, does not modify source `.slx`,
does not export labels, does not train GCN, and does not retrain the reranker.

## Reviewed Result

- target_bus: `B26`
- scenario_id: `BF_B26_TEMP_SMOKE`
- simulation_success: `true`
- physical_fault_or_breaker_action_executed: `true`
- measurement_extraction_status: `voltage_speed_angle`
- training_ready_candidate_smoke: `true`
- selected_fault_block_path: `Grid/Fault_B26_TEMP`
- selected_injection_block_path: `Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node`
- signal_source_has_frequency_proxy: `true`
- dynamic_measurement_available: `true`
- min_voltage_pu: `0.525205016184139`
- max_voltage_pu: `1.0635`
- min_frequency_hz: `49.9925858325228`
- max_frequency_hz: `50.4143232407741`
- max_speed_deviation: `0.00828646481548212`
- max_rotor_angle_separation_deg: `86.3888369812931`
- unstable_flag: `true`

## Interpretation

B26 `min_voltage_pu` is about `0.525`, so it is not near zero like the B39
close-in severe case, but it is still a clear voltage sag. The
`max_rotor_angle_separation_deg` value is about `86.39`, indicating a strong
dynamic disturbance. The `unstable_flag = true` value is a compact smoke
threshold flag, not a final stability conclusion.

B26 and B39 are both temporary bus-fault evidence at this stage. B26 is not a
formal label, and B26 candidate label exported is still false. Even if B26 is
exported in a later round, it should still go through composition review and
no-leakage preview before any training use.

## Quality Decision

- metrics_all_finite: `true`
- quality_review_passed_for_candidate_export: `true`
- recommended_next_step:
  `export B26 bus-fault candidate label in a separate round, without training`

## Boundaries

- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`
- source_slx_modified: `false`
- temporary_slx_committed: `false`
- l12_touched: `false`
- old_formal_gate_preserved: `true`
- old formal gate: `35 / 33 / 33`
- v2_plus_b39_count_preserved: `true`
- v2-plus-B39 count: `41`
- b39_status: `candidate_label_not_formal`
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
