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
- `allowed_for_dynamic_aware_training = true`

The label count has reached the minimum preview threshold of ten training-ready labels, so preview dynamic-aware reranker training can run in a separate commit.

## Claim Boundaries

- The model is `phasor_RMS`, not EMT.
- The timed controlled switch is not completed.
- The basic relay proxy is not engineering-grade protection.
- This is not full OPF dynamic simulation.
- These are compact preliminary quality-gate results, not final dynamic validation conclusions.

## Round 30 Timed Trip Probe

Round 30 specifically checked whether L01 could be upgraded to a timed controlled switch.

The new line-port inventory confirms that L01 has four Simscape physical ports, and the library search found breaker/switch candidates. However, the standalone probe did not identify an unambiguous controlled switch with a safe port structure for automatic wrapper rewiring.

Current result:

```text
insertion_success = false
trip_implementation = static_topology_disable
training_ready_candidate = false
manual_required
```

The wrapper was left unchanged. `static_topology_disable` is still not a timed breaker.

## Round 31 Handwired Validation

Round 31 stops automatic Simscape physical-port insertion. The project now supports a handwired validation flow: the user manually wires and saves a local handwired wrapper, then `validate_ieee39_handwired_breaker_model.m` checks whether the expected breaker and trip command are present.

Round 32 extends this to a multi-line handwired validation flow. The current
measurement source remains `generator_speed_proxy`, not a direct frequency
measurement. The model remains `phasor_RMS`, not EMT, and the multi-line
workflow still treats preview training as a separate commit after the compact
label gate reaches ten training-ready labels. In the current multi-line run,
L01-L04 pass structure validation. After the user manually revised L02 in the old
handwired Simulink GUI model, the L02 structure validation still passed, but
the isolated compact simulation timed out after 240 seconds. That old L02
timeout row is not counted as training-ready. The user then wired L02 in the
clean breaker lab. Clean lab L02 passes structure validation and isolated
compact simulation, so it is counted as an additional training-ready handwired
line-trip label. Per-line clean L03-L08 now also pass the compact gate.

Per-line clean L03, L04, L05, L06, L07, and L08 single-line labels now use
independent per-line clean lab models. L06/L07/L08 use verified wrapper Grid
paths `Grid/B14 to B15`, `Grid/B15 to B16`, and `Grid/B16 to B17`. Adding a new target into a clean lab that already
contains another active TripCommand can make both TripCommand blocks act at
0.5 s, turning the case into a simultaneous multi-line trip. That kind of
sequential or simultaneous trip experiment should be handled separately and
must not be mixed into the single-line label set.

Per-line clean L03, L04, L05, L06, L07, and L08 now pass structure validation
and compact isolated simulation, so the formal label gate is updated to ten
training-ready labels:

```text
num_training_ready_handwired_line_trip_labels = 8
num_unique_handwired_line_ids = 8
num_training_ready_labels = 10
allowed_for_dynamic_aware_training = true
```

The follow-up preview dynamic-aware reranker training has been run with the
compact label set. This preview training uses the compact phasor_RMS
measurements only as a sanity-check dataset. It does not convert
`generator_speed_proxy` into direct frequency, and it does not establish a
final dynamic performance conclusion.

The next sample-expansion step prepares L09/L10 independent per-line clean lab
models only. L09 maps to `Grid/B16 to B24`, and L10 maps to `Grid/B17 to B27`.
This preparation does not wire breakers, does not run L09/L10 compact
simulation, and does not retrain the dynamic-aware reranker.

Current result:

```text
handwired_model_found = true
handwired_validation_passed_lines = L01, L02, L03, L04, L05, L06, L07, L08
num_training_ready_handwired_line_trip_labels = 8
num_unique_handwired_line_ids = 8
num_training_ready_labels = 10
allowed_for_dynamic_aware_training = true
```

The handwired `.slx` is not committed.


## L09/L10 clean lab measurement update

The latest clean breaker lab compact runs add `L09` and `L10` as
training-ready handwired line-trip labels. Both runs use phasor_RMS, not EMT, and
keep `generator_speed_proxy` as a proxy signal, not direct frequency.

- `L09`: `simulation_success = true`, `breaker_opened = true`,
  `measurement_extraction_status = voltage_speed_angle`
- `L10`: `simulation_success = true`, `breaker_opened = true`,
  `measurement_extraction_status = voltage_speed_angle`

The current gate is:

- `num_training_ready_labels = 35`
- `num_training_ready_handwired_line_trip_labels = 33`
- `allowed_for_dynamic_aware_training = true`

This is still pilot breaker-like validation, not engineering-grade protection.
## L11-L34 measurement extraction update

For the user-wired `L11-L34` per-line clean labs, compact simulation produced
`voltage_speed_angle` measurements for `L11` and `L13-L34`. `L12` timed out and
therefore has no training-ready measurement row.

Current gate:

- `num_training_ready_labels = 35`
- `num_training_ready_handwired_line_trip_labels = 33`
- `num_unique_handwired_line_ids = 33`
- `allowed_for_dynamic_aware_training = true`

These measurements remain phasor_RMS compact dynamic validation results.
`generator_speed_proxy` is still a proxy, not direct frequency, and the
handwired breaker remains pilot breaker-like validation, not engineering-grade
protection.
