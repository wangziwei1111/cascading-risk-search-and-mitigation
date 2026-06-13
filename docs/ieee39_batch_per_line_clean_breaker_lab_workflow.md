# IEEE39 Batch Per-Line Clean Breaker Lab Workflow

## Purpose

Clean lab L02 and per-line clean lab L03, L04, L05, L06, L07, and L08 have
passed as single-line handwired line-trip labels. This workflow records how
batch per-line clean labs are prepared, validated, and simulated. The latest
successful simulated batch targets were L06/L07/L08. The current prepared next
manual targets are L09/L10, whose paths were verified from the wrapper Grid
inventory.

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
per-line clean lab L06
per-line clean lab L07
per-line clean lab L08
```

Current label gate:

```text
num_training_ready_labels = 10
num_training_ready_handwired_line_trip_labels = 8
num_unique_handwired_line_ids = 8
allowed_for_dynamic_aware_training = true
```

The label count has reached the preview threshold. Dynamic-aware reranker
preview training should run in a separate commit, not in this validation round.
That separate preview training round has now been run with the lightweight
script `scripts/gcn_search/train_ieee39_dynamic_aware_reranker_preview.py`.
The result is preview-only sanity-check evidence, not a final dynamic
performance conclusion.

## L09/L10 Batch Prepare

Run:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
prepare_ieee39_clean_handwired_breaker_labs_for_lines(string({'L09','L10'}))
```

This creates local-only models:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L09.slx
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L10.slx
```

The script only copies the original clean generated wrapper. It does not
insert breakers and does not modify Simscape physical-port wiring.

## Manual Targets

The line block paths below come from the wrapper Grid inventory. Do not invent a block path.
For any later line that remains `not_in_current_line_map`, do not wire until mapped.

L09:

```text
line block path: Grid/B16 to B24
breaker name: L09_HandwiredTimedBreaker
trip command name: L09_TripCommand
```

L10:

```text
line block path: Grid/B17 to B27
breaker name: L10_HandwiredTimedBreaker
trip command name: L10_TripCommand
```

For each target:

```text
Step time = 0.5 s
Initial value = 0
Final value = 1
```

One line uses one `.slx`. Do not wire more than one target breaker inside the
same per-line `.slx`. Do not copy from the old handwired model or from clean
labs that already contain L02-L08. During a single-line label run, only the
target breaker may act.

## Batch Validation After Manual Wiring

After the user manually wires and saves L09/L10, run:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_lines_batch(["L09","L10"])
```

If validation passes, run. In PowerShell, quote the model path pattern so
`{line_id}` is preserved:

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L09 L10 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx" --timeout-seconds 240 --simulation-stop-time 0.5
```

Each line runs in its own MATLAB process. A timeout on one line must not block
the next line.

This round only prepares the L09/L10 clean lab `.slx` files. It does not wire
breakers, run L09/L10 compact simulation, or train the dynamic-aware reranker.
In short: it does not wire breakers and does not train the dynamic-aware reranker.

The current L06/L07/L08 compact simulations passed:

```text
L06 path = Grid/B14 to B15
L07 path = Grid/B15 to B16
L08 path = Grid/B16 to B17
L06: simulation_success = true, measurement_extraction_status = voltage_speed_angle, breaker_opened = true
L07: simulation_success = true, measurement_extraction_status = voltage_speed_angle, breaker_opened = true
L08: simulation_success = true, measurement_extraction_status = voltage_speed_angle, breaker_opened = true
```

The current L04/L05 compact simulations both passed and remain preserved:

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


