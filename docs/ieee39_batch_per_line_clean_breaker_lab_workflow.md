# IEEE39 Batch Per-Line Clean Breaker Lab Workflow

## Purpose

Clean lab L02 and per-line clean lab L03, L04, and L05 have passed as
single-line handwired line-trip labels. This workflow records how batch
per-line clean labs are prepared, validated, and simulated. The same pattern can
be reused for later targets such as L06/L07 when their line blocks are mapped.

This is still single-line label collection, not simultaneous or sequential
multi-line trip experimentation. Each `.slx` must contain only the breaker for
its own target line.

## Current Successful Labels

```text
L01
clean lab L02
per-line clean lab L03
per-line clean lab L04
per-line clean lab L05
```

Current label gate:

```text
num_training_ready_labels = 7
num_training_ready_handwired_line_trip_labels = 5
num_unique_handwired_line_ids = 5
allowed_for_dynamic_aware_training = false
```

Because labels are still below 10, dynamic-aware reranker training remains
blocked.

## L04/L05 Batch Prepare And Validation Reference

Run:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
prepare_ieee39_clean_handwired_breaker_labs_for_lines(["L04","L05"])
```

This creates local-only models:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L04.slx
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L05.slx
```

The script only copies the original clean generated wrapper. It does not
insert breakers and does not modify Simscape physical-port wiring.

## Manual Targets

L04:

```text
line block path: Grid/B11 to B6
breaker name: L04_HandwiredTimedBreaker
trip command name: L04_TripCommand
```

L05:

```text
line block path: Grid/B13 to B14
breaker name: L05_HandwiredTimedBreaker
trip command name: L05_TripCommand
```

For each target:

```text
Step time = 0.5 s
Initial value = 0
Final value = 1
```

One line uses one `.slx`. Do not wire L05 inside the L04 `.slx`. Do not copy
from the old handwired model or from clean labs that already contain L02 or
L03. During a single-line label run, only the target breaker may act.

## Batch Validation After Manual Wiring

After the user manually wires and saves L04/L05, run:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_lines_batch(["L04","L05"])
```

If validation passes, run. In PowerShell, quote the model path pattern so
`{line_id}` is preserved:

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L04 L05 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx" --timeout-seconds 240 --simulation-stop-time 0.5
```

Each line runs in its own MATLAB process. A timeout on one line must not block
the next line.

The current L04/L05 compact simulations both passed:

```text
L04: simulation_success = true, measurement_extraction_status = voltage_speed_angle, breaker_opened = true
L05: simulation_success = true, measurement_extraction_status = voltage_speed_angle, breaker_opened = true
```

## Boundaries

- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- Sequential or simultaneous multi-line trip experiments can be studied later,
  but they must not be mixed into single-line labels.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries.

