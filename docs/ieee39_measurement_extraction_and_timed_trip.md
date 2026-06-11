# IEEE39 Measurement Extraction and Timed Trip Status

## Round 29 Purpose

Round 29 focuses on two small but important quality gates:

1. Extract real measurements from `simlog_IEEE39BusSystem`.
2. Check whether `single_line_trip` can be upgraded from `static_topology_disable` to a timed controlled switch or breaker-like trip.

This round does not train the dynamic-aware reranker and does not expand N-2 batches.

## Measurement Extraction

The compact extractor now traverses the Simscape log tree and records an inventory:

- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_simlog_tree_inventory.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_simlog_tree_inventory.json`

The extractor uses real logged generator signals:

- voltage: `Generators.*.Terminal_voltage.pu_output`
- speed: `Generators.*.Rotor_velocity.pu_output`
- rotor angle: `Generators.*.Rotor_electrical_angle.pu_output`
- frequency: `generator_speed_proxy`, computed as `speed_pu * 50`

The frequency field is therefore not a direct frequency measurement. It is a generator-speed proxy and is reported with `frequency_source = generator_speed_proxy`.

No fixed placeholder values such as `1.0` or `50.0` are reported as measured values. If a signal is unavailable, the value remains `NaN` and the signal is listed in `missing_signal_list`.

## Current Compact Results

| case | measurement status | min voltage pu | frequency source |
|---|---:|---:|---|
| no_fault_sanity | voltage_speed_angle | 0.981209 | generator_speed_proxy |
| three_phase_fault_clear | voltage_speed_angle | 0.532828 | generator_speed_proxy |
| single_line_trip | voltage_speed_angle | 0.980882 | generator_speed_proxy |
| relay_trip_test | voltage_speed_angle | 0.534852 | generator_speed_proxy |

The voltage drop in `three_phase_fault_clear` is consistent with the existing `Fault (Three-Phase)` block being exercised.

## Timed Trip Status

`single_line_trip` is still not upgraded to a verified timed controlled switch.

The wrapper inventory did not find an explicit breaker on the mapped pilot line. The available Simscape `Circuit Breaker (Three-Phase)` block has a different physical-port structure from the mapped `Transmission Line (Three-Phase)` block, so automatic rewiring is left as `manual_required` in this round.

Current line-trip interpretation:

- `trip_implementation = static_topology_disable`
- `physical_fault_or_breaker_action_executed = false`
- `training_ready_candidate = false`

Static topology disable is not a timed breaker. A future manual or carefully scripted physical-port insertion is required before line-trip rows can be treated as training-ready dynamic labels.

## Label Gate

Current label quality summary:

- `num_training_ready_labels = 2`
- `num_labels_with_voltage_measurement = 4`
- `num_labels_with_frequency_measurement = 4`
- `num_labels_with_speed_measurement = 4`
- `num_labels_with_rotor_angle_measurement = 4`
- `measurement_quality_status = partial_dynamic_measurements`
- `label_quality_status = partial_physical_execution`
- `allowed_for_dynamic_aware_training = false`

The label count is still below the minimum preview threshold of ten training-ready labels, so dynamic-aware reranker training remains blocked.

## Claim Boundaries

- The model is `phasor_RMS`, not EMT.
- The timed controlled switch is not completed.
- The basic relay proxy is not engineering-grade protection.
- This is not full OPF dynamic simulation.
- These are compact preliminary quality-gate results, not final dynamic validation conclusions.
