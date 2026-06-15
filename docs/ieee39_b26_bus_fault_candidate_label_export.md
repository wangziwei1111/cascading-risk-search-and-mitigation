# IEEE39 B26 Bus-Fault Candidate Label Export

This round exports only one B26 temporary bus-fault candidate label from the
quality-reviewed temporary smoke result. It does not run Simulink, does not
submit `.slx`, does not modify source `.slx`, does not train GCN, does not
retrain the reranker, and does not run a GCN usefulness audit.

## Plain-Language Meaning

The B26 temporary smoke already ran successfully and produced voltage, speed,
and rotor-angle measurements. This round only puts that reviewed sample into
the candidate-label table for later composition review. It is not a formal
label and it is not used for training in this round.

## Exported Candidate

- scenario_id: `BF_B26_TEMP_SMOKE`
- target_bus: `B26`
- target_bus_or_component: `B26`
- line_id: `NO_LINE`
- fault_type: `three_phase_bus_fault_temp_smoke`
- label_family: `non_line_trip`
- simulation_success: `true`
- physical_fault_or_breaker_action_executed: `true`
- measurement_extraction_status: `voltage_speed_angle`
- signal source includes `frequency=generator_speed_proxy`
- dynamic_stress_score: `0.5314759474846006`
- unstable_flag: `true`
- training_ready_label_candidate: `true`
- formal_line_trip_label: `false`
- handwired_line_trip_label: `false`
- non_line_trip_label: `true`
- bus_fault_label: `true`
- candidate_not_formal_label: `true`

## Counts

- previous v2-plus-B39 count: `41`
- new B26 bus-fault candidates: `1`
- new v2-plus-B39+B26 candidate count: `42`
- old formal gate remains: `35 / 33 / 33`
- B39 status: `candidate_label_not_formal`
- L12 remains excluded: `true`
- NF06 duplicate/provenance warning preserved: `true`

## Outputs

- candidate CSV:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_dynamic_label_candidate.csv`
- candidate JSON:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_dynamic_label_candidate.json`
- v2-plus-B39+B26 combined schema:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_dynamic_label_schema_v2_plus_b39_b26_candidate.csv`
- export summary:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_candidate_export_summary.json`
- training readiness:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_v2_plus_b39_b26_training_readiness.json`

## Boundaries

- labels_exported_this_round: `candidate_only`
- gcn_trained: `false`
- reranker_retrained: `false`
- should_train_now: `false`
- formal_label_gate_changed: `false`
- source_slx_modified: `false`
- temporary_slx_committed: `false`

B26 is a candidate label, not a formal label. B39 is also a candidate label,
not a formal label. The model remains `phasor_RMS`, not EMT.
`generator_speed_proxy` is not direct frequency. Temporary bus-fault injection
is not engineering-grade protection.

## Recommended Next Step

Run a v2-plus-B39+B26 no-training composition review before any training. That
review should check mixed label-family composition, no-leakage risk, and
bus-fault holdout requirements.

## No-Training Composition Review Follow-Up

The v2-plus-B39+B26 no-training composition review has been completed:

- v2-plus-B39+B26 candidate count: `42`
- num_bus_fault_candidates: `2`
- bus-fault targets: `B39`, `B26`
- b39_b26_schema_consistency_passed: `true`
- count_consistency_passed: `true`
- export_boundary_passed: `true`
- leakage_risk_reviewed: `true`
- should_train_now: `false`

The review records that post-fault compact dynamic measurements have
target-feature leakage risk if used as model input features. The next step is a
separate preview/no-leakage comparison, not training.

## Preview/No-Leakage Comparison Follow-Up

The v2-plus-B39+B26 preview/no-leakage comparison has been completed without
running Simulink, exporting labels, training GCN, running a GCN usefulness
audit, or retraining the formal reranker.

Key B26 result:

- B26 true dynamic_stress_score: `0.5314759474846003`
- B26 predicted dynamic_stress_score in B26 holdout: `0.667249711719703`
- B26 holdout absolute error: `0.1357737642351028`
- B26 unstable probability: `0.9927567600955874`

Together with the B39 holdout result, this suggests that bus-fault
generalization is still a small-sample problem. The recommended next step is
to collect more bus-fault candidates before GCN usefulness audit.
