# IEEE39 B26 Temp Smoke Quality Review

This round only reviews the B26 temporary bus-fault smoke output that was
already generated in the previous round. It does not run Simulink, does not
submit `.slx`, does not modify source `.slx`, does not export labels, does not
train GCN, and does not retrain the reranker.

## Reviewed Result

- target_bus: `B26`
- scenario_id: `BF_B26_TEMP_SMOKE`
- simulation_success: `true`
- physical_fault_or_breaker_action_executed: `true`
- measurement_extraction_status: `voltage_speed_angle`
- training_ready_candidate_smoke: `true`
- signal source includes `frequency=generator_speed_proxy`
- min_voltage_pu: `0.525205016184139`
- max_voltage_pu: `1.0635`
- min_frequency_hz: `49.9925858325228`
- max_frequency_hz: `50.4143232407741`
- max_speed_deviation: `0.00828646481548212`
- max_rotor_angle_separation_deg: `86.3888369812931`
- unstable_flag: `true`

## Conservative Interpretation

B26 `min_voltage_pu` is about `0.525`. It is not near zero like the B39 close-in
severe case, but it is still a clear voltage sag. The rotor-angle separation is
about `86.39` degrees, which means the compact phasor_RMS smoke output shows a
strong dynamic disturbance.

The `unstable_flag = true` value is only a compact smoke threshold marker. It is
not a final stability conclusion. B26 remains temporary bus-fault evidence, not
a formal label. B26 candidate label exported remains false in this round.

## Quality Decision

The quality review passes for a separate candidate-label export round:

- metrics_all_finite: `true`
- quality_review_passed_for_candidate_export: `true`
- recommended_next_step:
  `export B26 bus-fault candidate label in a separate round, without training`

This does not mean the B26 candidate label was exported in this round. A later
export round should still perform composition review and no-leakage preview
before any model training.

## Boundary Conditions

- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`
- source_slx_modified: `false`
- temporary_slx_committed: `false`
- L12 touched: `false`
- old formal gate remains `35 / 33 / 33`
- v2-plus-B39 count remains `41`
- B39 remains `candidate_label_not_formal`
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

Artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_quality_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_quality_review.md`
