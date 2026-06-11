# IEEE39 Real Fault Execution Status

## Round 28 Goal

Round 28 moves the IEEE39 wrapper from a dry-run/schema interface toward a small number of real executable graphical dynamic cases.

It does not train a dynamic-aware reranker.

## What Changed

The fault-test suite now supports a lightweight selected-case run:

```matlab
run_ieee39_fault_test_suite( ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx", ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests", ...
  true, ...
  ["no_fault_sanity", "three_phase_fault_clear", "single_line_trip"], ...
  0.2 ...
)
```

The suite now records:

- `schema_only`
- `simulation_mode`
- `trip_implementation`
- `fault_configuration_status`
- `measurement_extraction_status`
- `training_ready_candidate`
- `timeout_or_error_message`

## Current Results

| case | real simulation | physical fault / breaker action | training candidate | note |
|---|---:|---:|---:|---|
| no_fault_sanity | yes | no | no | sanity only, not a training label |
| three_phase_fault_clear | yes | yes | yes | uses existing `Fault (Three-Phase)` block |
| relay_trip_test | yes | yes | yes | uses basic relay proxy, not engineering-grade protection |
| single_line_trip | yes | no | no | static topology disable, not timed breaker |

The current label quality gate is:

```text
label_quality_status = partial_physical_execution
allowed_for_dynamic_aware_training = false
```

## Measurement Extraction

Measurement extraction is currently `partial`.

The available `SimulationOutput` exposes Simscape logging, but the compact extractor has not yet mapped bus voltage, frequency, generator speed, and rotor angle from the log tree. Missing values are written as `NaN`; fixed placeholder values such as `1.0` or `50.0` are not reported as measured values.

## Claim Boundaries

- This is `phasor_RMS`, not EMT.
- This is not full OPF dynamic simulation.
- The basic relay proxy is not engineering-grade protection.
- Static topology disable is not a timed breaker.
- No dynamic-aware reranker training is allowed until at least ten training-ready physical labels pass the quality gate.

## Next Step

Map the Simscape log tree to real voltage, frequency, generator speed, and rotor-angle metrics, then add a real timed breaker or controlled-switch implementation for line trips.

## Round 29 Update

Round 29 maps `simlog_IEEE39BusSystem` and extracts compact real measurements from logged generator signals.

Current compact results:

| case | measurement status | min voltage pu | frequency source | training candidate |
|---|---:|---:|---|---:|
| no_fault_sanity | voltage_speed_angle | 0.981209 | generator_speed_proxy | no |
| three_phase_fault_clear | voltage_speed_angle | 0.532828 | generator_speed_proxy | yes |
| single_line_trip | voltage_speed_angle | 0.980882 | generator_speed_proxy | no |
| relay_trip_test | voltage_speed_angle | 0.534852 | generator_speed_proxy | yes |

The frequency values are speed-derived proxies, not direct frequency measurements.

The single-line trip is still `static_topology_disable`. Automatic insertion of a timed controlled switch was not completed because the mapped transmission-line physical ports and available breaker block require careful manual or scripted rewiring. It remains non-training-ready.

Current quality gate:

```text
num_training_ready_labels = 2
measurement_quality_status = partial_dynamic_measurements
label_quality_status = partial_physical_execution
allowed_for_dynamic_aware_training = false
```

## Round 30 Update

Round 30 attempted to move `single_line_trip` from `static_topology_disable` toward a real timed controlled switch.

The line-port inventory shows L01 has four Simscape physical ports. Candidate breaker/switch blocks were found in installed libraries, but the standalone probe did not approve a safe automatic insertion path. The wrapper was not modified.

Current result:

```text
single_line_trip trip_implementation = static_topology_disable
single_line_trip physical_fault_or_breaker_action_executed = false
single_line_trip training_ready_candidate = false
num_training_ready_timed_line_trip_labels = 0
allowed_for_dynamic_aware_training = false
```

Manual physical-port rewiring is still required before `single_line_trip` can become a training-ready timed line-trip label.
