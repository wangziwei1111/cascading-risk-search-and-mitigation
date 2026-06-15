# IEEE39 v2-plus-B39 No-Training Composition Review

This round fixes the B39 candidate label schema and performs a no-training
composition/comparison review. It does not run Simulink, does not submit `.slx`,
does not modify source `.slx`, does not train GCN, does not retrain the
dynamic-aware reranker, and does not overwrite the existing v2 preview training
results.

## Plain-Language Meaning

B39 is a bus-fault candidate, so the label table must say clearly which bus was
faulted. The previous export had `target_bus_or_component = B39`, but the
separate `target_bus` field was empty or missing. This round fills that field
and then checks whether adding one B39 candidate changes the label composition.

## Schema Fix

- B39 `target_bus`: `B39`
- B39 `target_bus_or_component`: `B39`
- B39 `line_id`: `NO_LINE`
- B39 `fault_type`: `three_phase_bus_fault_temp_smoke`
- B39 `label_family`: `non_line_trip`
- B39 `bus_fault_label`: `true`
- B39 `candidate_not_formal_label`: `true`
- B39 `formal_line_trip_label`: `false`
- B39 `handwired_line_trip_label`: `false`
- B39 `non_line_trip_label`: `true`

The old v2 40 rows are not overwritten. The v2-plus-B39 file still contains
`41` rows.

## Review Result

- previous_v2_candidate_count: `40`
- v2-plus-B39 candidate count: `41`
- old formal gate: `35 / 33 / 33`
- num_formal_v1_existing: `35`
- num_handwired_line_trip: `33`
- num_non_line_trip_candidates: `6`
- num_bus_fault_candidates: `1`
- num_temporary_smoke_candidates: `1`
- num_candidate_not_formal_label: `1`
- num_training_ready_label_candidate: `41`
- L12 excluded: `true`
- NF06 provenance warning preserved: `true`
- B39 exact duplicate: `false`
- B39 provenance risk: `false`
- b39_schema_consistency_passed: `true`
- count_consistency_passed: `true`
- export_boundary_passed: `true`
- should_train_now: `false`

## Artifacts

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_composition_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_composition_review.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_label_family_counts.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_fault_type_counts.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_bus_fault_comparison.csv`

## Boundaries

B39 remains a candidate label, not a formal label. This is not a final
performance conclusion. The model remains `phasor_RMS`, not EMT.
`generator_speed_proxy` is not direct frequency. The temporary bus-fault
injection is not engineering-grade protection.

## Recommended Next Step

A later separate round may optionally run v2-plus-B39 preview training, but it
must include label-family holdout and no-leakage comparison. This round keeps
`should_train_now = false`.
