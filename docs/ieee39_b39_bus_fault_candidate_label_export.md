# IEEE39 B39 Bus-Fault Candidate Label Export

This round exports only one B39 temporary bus-fault candidate label from the
quality-reviewed temporary smoke result. It does not run Simulink, does not
submit `.slx`, does not submit `.slx` artifacts, does not modify source `.slx`, does not train GCN, does not
retrain the dynamic-aware reranker, does not retrain any reranker model, and
does not overwrite the existing v2
preview training artifacts.

## Plain-Language Meaning

The B39 temporary smoke already showed a severe bus-fault response with usable
voltage, speed, and angle measurements. This round only records that result as
a future candidate label. It is like putting the sample into a separate
"candidate box" for later review. It is not yet a formal dynamic label and it
is not used for training in this round.

## Exported Candidate

- scenario_id: `BF_B39_TEMP_SMOKE`
- target_bus: `B39`
- line_id: `NO_LINE`
- fault_type: `three_phase_bus_fault_temp_smoke`
- label_family: `non_line_trip`
- simulation_success: `true`
- physical_fault_or_breaker_action_executed: `true`
- measurement_extraction_status: `voltage_speed_angle`
- signal source includes `frequency=generator_speed_proxy`
- training_ready_label_candidate: `true`
- formal_line_trip_label: `false`
- handwired_line_trip_label: `false`
- non_line_trip_label: `true`
- bus_fault_label: `true`
- candidate_not_formal_label: `true`

## Counts

- previous v2 candidate count: `40`
- new v2-plus-B39 candidate count: `41`
- new B39 bus-fault candidates: `1`
- old formal gate remains: `35 / 33 / 33`
- L12 remains excluded: `true`
- NF06 duplicate/provenance warning preserved: `true`

## Outputs

- candidate CSV:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_b39_bus_fault_dynamic_label_candidate.csv`
- candidate JSON:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_b39_bus_fault_dynamic_label_candidate.json`
- v2-plus-B39 combined schema:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_dynamic_label_schema_v2_plus_b39_candidate.csv`
- quality summary:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_dynamic_label_quality_summary_v2_plus_b39_candidate.json`
- readiness summary:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_dynamic_aware_training_readiness_v2_plus_b39_candidate.json`
- duplicate/provenance report:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_b39_candidate_duplicate_provenance_report.md`

## Boundaries

- labels_exported_this_round: `candidate_only`
- gcn_trained: `false`
- reranker_retrained: `false`
- should_train_now: `false`
- formal_label_gate_changed: `false`
- v2_preview_training_changed: `false`
- source_slx_modified: `false`
- temporary_slx_committed: `false`

The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency; specifically, `generator_speed_proxy` is not direct frequency. The
temporary bus-fault injection is not engineering-grade
protection. In short, this candidate is not engineering-grade protection.

## Recommended Next Step

Run a no-training composition and comparison review first. Only after reviewing
the mixed line-trip / non-line-trip / bus-fault label composition should a
future v2-plus-B39 preview training round be considered.
