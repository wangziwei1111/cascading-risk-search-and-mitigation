# IEEE39 B39 Temporary Bus-Fault Smoke

This round runs one actual B39 temporary bus-fault smoke using only the ignored
local temporary `.slx` copy:

`results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B39_TEMP_LOCAL_ONLY.slx`

No source `.slx` was modified, no `.slx` was submitted, L12 was not touched, no
labels were exported, GCN was not trained, and the dynamic-aware reranker was
not retrained.

## Smoke Result

- scenario_id: `BF_B39_TEMP_SMOKE`
- target_bus: `B39`
- fault_start_s: `0.5`
- fault_clear_s: `0.58`
- duration_s: `0.08`
- simulation_success: `true`
- physical_fault_or_breaker_action_executed: `true`
- measurement_extraction_status: `voltage_speed_angle`
- training_ready_candidate_smoke: `true`
- min_voltage_pu: `0.000160777190390721`
- max_voltage_pu: `1.0635`
- min_frequency_hz: `49.7327386072042`
- max_frequency_hz: `50.1408910900975`
- max_speed_deviation: `0.00534522785591696`
- max_rotor_angle_separation_deg: `73.905967084859`
- unstable_flag: `true`
- signal_source_summary:
  `voltage=generator_terminal_voltage_pu;speed=generator_rotor_velocity_pu;frequency=generator_speed_proxy;rotor_angle=generator_rotor_electrical_angle`

## Artifacts

- summary CSV:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_summary.csv`
- report JSON:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.json`
- report MD:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.md`

## Boundaries

- source_slx_modified: `false`
- temporary_slx_committed: `false`
- formal_label_gate_changed: `false`
- v2_candidate_count_changed: `false`
- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`
- l12_touched: `false`
- old formal gate remains `35 / 33 / 33`
- v2 candidate count remains `40`

This is a temporary smoke candidate only. Even though the smoke run succeeded,
it is not yet a formal dynamic label. The next step is to review the B39 smoke
quality first, then export a B39 bus-fault candidate label in a separate round.

The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency. The temporary bus-fault injection is not engineering-grade
protection.

## Quality Review Follow-Up

A follow-up quality review was completed without running Simulink again. It
checks whether the previous B39 temporary smoke has enough measurement quality
for a separate candidate-label export round.

- quality_review_passed_for_candidate_export: `true`
- min_voltage_near_zero: `true`
- min_voltage interpretation: expected for a close-in three-phase B39 bus-fault
  candidate, still requiring separate review before export
- unstable_flag interpretation: plausible for severe B39 temporary smoke, not a
  final stability conclusion
- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`

Quality review artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_quality_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_quality_review.md`
- `docs/ieee39_b39_temp_smoke_quality_review.md`
