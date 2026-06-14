# IEEE39 Non-Line-Trip Fault Expansion Feasibility Report

## What Can Run Without `.slx` Changes Now

- three_phase_bus_fault_clear baseline through run_ieee39_fault_test_suite
- fault_duration_sweep timing configuration through configure_ieee39_three_phase_fault_case
- relay_proxy_fault baseline through run_ieee39_fault_test_suite relay_trip_test

## Manual Or Future Work

- different-bus three-phase fault selector
- load_step_disturbance
- generator_trip_or_mechanical_power_step
- bus_voltage_disturbance_or_reference_event

## First Smoke-Test Candidates

NF01, NF02, NF03, NF04, NF06

## Risks

- target-feature leakage if compact dynamic measurements are reused as both features and proxy labels
- mixing non-line-trip labels with handwired line-trip labels
- bus-specific fault injection requires manual mapping
- duration sweep must not be reported as suite-grade until a duration-aware smoke runner is used

## Label Boundary

These scenarios do not mix with the handwired line-trip labels. They are an expansion plan only, not new training-ready labels. No Simulink run was executed, no `.slx` was modified, no L12 fix was attempted, and no dynamic-aware reranker was retrained.
