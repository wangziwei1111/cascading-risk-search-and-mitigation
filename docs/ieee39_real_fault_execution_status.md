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
