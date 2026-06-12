# IEEE39 Clean Breaker Lab Workflow

## Purpose

The old handwired `.slx` has been edited many times. L01 can still provide one
training-ready handwired line-trip label, but L02-L04 passed structural
validation while compact dynamic simulation failed or timed out. To eliminate
possible hidden bypasses, short circuits, wrong control wiring, or abnormal
physical network states, new manual breaker wiring should start from a clean
lab model.

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

## Boundaries

- This model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- If total training-ready labels remain below 10, dynamic-aware reranker training remains blocked.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries.
