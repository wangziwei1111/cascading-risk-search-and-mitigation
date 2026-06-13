# IEEE39 Clean Breaker Lab Workflow

## Purpose

The old handwired `.slx` has been edited many times. L01 can still provide one
training-ready handwired line-trip label, and clean/per-line clean lab models
now provide training-ready L02, L03, L04, and L05 labels. To eliminate possible
hidden bypasses, short circuits, wrong control wiring, or abnormal physical
network states, future manual breaker wiring should continue from independent
per-line clean lab models.

## Clean Lab Model

Prepare the local clean model with:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
prepare_ieee39_clean_handwired_breaker_lab()
```

Open this model for the next manual wiring step:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab.slx
```

Do not use the old model for this workflow:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx
```

The clean lab .slx is local only and must not be committed.

## First Manual Target

Wire only one line first:

```text
line_id: L02
line block path: IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B10 to B11
breaker name: L02_HandwiredTimedBreaker
trip command name: L02_TripCommand
trip time: 0.5 s
```

Use `Initial value = 0` and `Final value = 1` first. If the breaker appears to
operate in the opposite direction, try `Initial value = 1` and
`Final value = 0`.

## Validation After Manual Wiring

After saving the clean lab `.slx`, run:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_line()
```

If validation passes, then run:

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trip_isolated.py --line-id L02 --timeout-seconds 240 --simulation-stop-time 0.5
```

Clean L02 is considered usable only when `simulation_success = true` and
`measurement_extraction_status = voltage_speed_angle`.

## Current Clean L02 Result

The user has manually wired L02 in the clean breaker lab model. The current
validation result is:

```text
clean lab L02 validation_passed = true
breaker_block_found = true
trip_command_found = true
breaker_near_line = true
clean_lab_model_committed = false
```

The isolated compact simulation also passes:

```text
simulation_success = true
trip_implementation = handwired_timed_breaker
measurement_extraction_status = voltage_speed_angle
training_ready_candidate = true
breaker_opened = true
min_voltage_pu = 0.971757
max_voltage_pu = 1.063647
min_frequency_hz = 49.942069
max_frequency_hz = 50.043873
max_speed_deviation = 0.001159
max_rotor_angle_separation_deg = 60.015942
```

Clean lab L02 is therefore merged as one training-ready handwired line-trip
label. The old handwired model's L02 timeout row is still not treated as
training-ready.

Current label gate:

```text
num_training_ready_handwired_line_trip_labels = 5
num_unique_handwired_line_ids = 5
num_training_ready_labels = 7
allowed_for_dynamic_aware_training = false
```

Per-line clean L03, L04, and L05 have now passed validation and compact
simulation. The next manual targets should be L06 and L07, if their line blocks
are mapped and independent clean lab `.slx` files are prepared. Do not keep
adding new TripCommand blocks into a clean lab that already contains another
active line trip. If two TripCommand blocks both act at 0.5 s, the simulation
becomes a simultaneous two-line trip and cannot be used as a single-line label.

Per-line L03 reference target:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx
line block path: Grid/B10 to B13
breaker name: L03_HandwiredTimedBreaker
trip command name: L03_TripCommand
```

Per-line clean L03, L04, and L05 have now passed validation and compact
simulation. The current formal label gate is:

```text
num_training_ready_labels = 7
num_training_ready_handwired_line_trip_labels = 5
num_unique_handwired_line_ids = 5
allowed_for_dynamic_aware_training = false
```

The next batch should prepare L06 and L07 as separate per-line clean lab
models when those line IDs are available in the wrapper line map.

## Boundaries

- This model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- If total training-ready labels remain below 10, dynamic-aware reranker training remains blocked.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries.

