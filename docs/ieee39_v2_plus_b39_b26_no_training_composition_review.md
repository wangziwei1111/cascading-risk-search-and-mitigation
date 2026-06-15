# IEEE39 v2-plus-B39+B26 No-Training Composition Review

This round only reviews the already exported 42-row candidate dataset. It does
not run Simulink, does not export new labels, does not train GCN, does not
retrain the reranker, does not run preview training, and does not run a GCN
usefulness audit.

## Plain-Language Meaning

B39 and B26 are now both temporary bus-fault candidate labels. This review
checks whether the expanded table is internally consistent before any later
model experiment. It is a data-composition gate, not a training result.

## Review Result

- review_scope: `no_training_composition_comparison`
- v2-plus-B39+B26 candidate count: `42`
- previous v2-plus-B39 count: `41`
- bus-fault candidates: `B39`, `B26`
- num_bus_fault_candidates: `2`
- num_non_line_trip_candidates: `7`
- B39 status: `candidate_label_not_formal`
- B26 status: `candidate_label_not_formal`
- old formal gate: `35 / 33 / 33`
- L12 excluded: `true`
- NF06 provenance warning preserved: `true`
- b39_b26_schema_consistency_passed: `true`
- count_consistency_passed: `true`
- export_boundary_passed: `true`
- all_no_training_composition_checks_passed: `true`
- should_train_now: `false`

## Duplicate And Provenance

- b39_exact_duplicate: `false`
- b26_exact_duplicate: `false`
- b39_b26_duplicate_measurement_group: `false`
- scenario_id_duplicates: `[]`
- label_id_v2_duplicates: `[]`

B39 and B26 have complete `target_bus`, `target_bus_or_component`, and
`line_id = NO_LINE` schema fields. Both are candidate labels, not formal labels.

## Leakage Risk

The compact dynamic measurement columns, including `min_voltage_pu`,
`max_voltage_pu`, `min_frequency_hz`, `max_frequency_hz`,
`max_speed_deviation`, and `max_rotor_angle_separation_deg`, are post-fault
measurements. They can support target construction and quality review, but they
create target-feature leakage risk if used directly as main GCN or reranker
input features.

Any later preview or model evaluation must include a no-dynamic-measurement
feature version and explicit no-leakage comparison.

## Future Holdout Requirements

Before any model claim, a later separate round should include:

- label-family holdout
- bus-fault holdout
- B39 holdout
- B26 holdout
- no-dynamic-measurement feature comparison

## Outputs

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_composition_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_composition_review.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_label_family_counts.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_fault_type_counts.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_bus_fault_comparison.csv`

## Boundaries

B39 and B26 are candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.

## Recommended Next Step

Run v2-plus-B39+B26 preview/no-leakage comparison in a separate round, still
not GCN usefulness audit.
