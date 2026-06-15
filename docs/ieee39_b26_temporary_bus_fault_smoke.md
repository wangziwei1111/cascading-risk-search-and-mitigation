# IEEE39 B26 Temporary Bus-Fault Smoke

This round ran the actual B26 temporary bus-fault smoke using only the ignored
temporary local copy:

`results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B26_TEMP_LOCAL_ONLY.slx`

Plain wording: the temporary B26 fault was actually simulated once, and compact
dynamic measurements were extracted. This is still only a temporary smoke
candidate. It is not a formal label, and this round does not export any B26
candidate label.

## Smoke Result

- target_bus: `B26`
- scenario_id: `BF_B26_TEMP_SMOKE`
- actual_simulink_run: `true`
- dry_run: `false`
- simulation_success: `true`
- physical_fault_or_breaker_action_executed: `true`
- measurement_extraction_status: `voltage_speed_angle`
- training_ready_candidate_smoke: `true`
- selected_fault_block_path: `Grid/Fault_B26_TEMP`
- selected_injection_block_path: `Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node`
- min_voltage_pu: `0.525205016184139`
- max_voltage_pu: `1.0635`
- min_frequency_hz: `49.9925858325228`
- max_frequency_hz: `50.4143232407741`
- max_speed_deviation: `0.00828646481548212`
- max_rotor_angle_separation_deg: `86.3888369812931`
- unstable_flag: `true`
- signal_source_summary: `voltage=generator_terminal_voltage_pu;speed=generator_rotor_velocity_pu;frequency=generator_speed_proxy;rotor_angle=generator_rotor_electrical_angle`

The `unstable_flag = true` is driven by the compact smoke thresholds, especially
the low minimum voltage. This means the next step should be a B26 smoke quality
review before any label export.

## Boundaries

- source `.slx` modified: `false`
- `.slx` submitted: `false`
- temporary `.slx` committed: `false`
- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`
- formal_label_gate_changed: `false`
- v2_plus_b39_count_changed: `false`
- old formal gate: `35 / 33 / 33`
- v2-plus-B39 count: `41`
- b39_status: `candidate_label_not_formal`
- L12 touched: `false`

B39 remains a candidate label, not a formal label. B26 is not a formal label.
`phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. The
temporary bus-fault injection is not engineering-grade protection.

## Artifacts

- B26 smoke summary:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_summary.csv`
- B26 smoke report JSON:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_report.json`
- B26 smoke report Markdown:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_report.md`

## Recommended Next Step

Review B26 smoke output quality before any label export. Do not immediately
export labels or train GCN / reranker from this smoke output.
