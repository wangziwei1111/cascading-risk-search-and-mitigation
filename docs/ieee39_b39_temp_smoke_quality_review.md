# IEEE39 B39 Temp Smoke Quality Review

This round reviews the B39 temporary bus-fault smoke result from the previous
round. It does not run Simulink, does not submit `.slx`, does not modify the
source `.slx`, does not touch L12, does not export labels, does not train GCN,
and does not retrain the reranker.

## Reviewed Result

- scenario_id: `BF_B39_TEMP_SMOKE`
- target_bus: `B39`
- simulation_success: `true`
- physical_fault_or_breaker_action_executed: `true`
- measurement_extraction_status: `voltage_speed_angle`
- training_ready_candidate_smoke: `true`
- signal source includes `frequency=generator_speed_proxy`
- min_voltage_pu: `0.000160777190390721`
- max_voltage_pu: `1.0635`
- min_frequency_hz: `49.7327386072042`
- max_frequency_hz: `50.1408910900975`
- max_speed_deviation: `0.00534522785591696`
- max_rotor_angle_separation_deg: `73.905967084859`
- unstable_flag: `true`

The near-zero `min_voltage_pu` is consistent with a close-in severe B39
three-phase bus-fault candidate. The `unstable_flag = true` value can be kept as
a candidate record, but it is not a final generalized stability conclusion.

## Quality Decision

The quality review passes for separate candidate export:

- quality_review_passed_for_candidate_export: `true`
- recommended_next_step:
  `export B39 bus-fault candidate label in a separate round, without training`

This does not mean labels were exported in this round.

## Candidate Export Follow-Up

A later export-only round records the reviewed `BF_B39_TEMP_SMOKE` result as one
separate B39 bus-fault candidate label. That follow-up still does not run
Simulink, does not submit `.slx`, does not modify source `.slx`, does not train
GCN, and does not retrain the dynamic-aware reranker.

- exported label scope: `candidate_only`
- previous v2 candidate count: `40`
- v2-plus-B39 candidate count: `41`
- old formal gate remains `35 / 33 / 33`
- B39 is not a formal label
- L12 remains excluded
- NF06 duplicate/provenance warning is preserved

The candidate export is documented in
`docs/ieee39_b39_bus_fault_candidate_label_export.md`.

## Boundary Conditions

- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`
- old formal gate remains `35 / 33 / 33`
- v2 candidate count remains `40`
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

Artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_quality_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_quality_review.md`
