# IEEE39 Per-Line Clean Breaker Lab Workflow

## Purpose

The current goal is to collect single-line dynamic labels. A single-line label
means that only the target line's handwired breaker acts during the compact
simulation. It is not a multi-line cascading trip sequence.

Clean L02 has already passed structure validation and isolated compact
simulation, and it is already counted as one training-ready handwired line-trip
label. The next target is L03, but L03 should not be wired into the same clean
lab `.slx` that already contains L02.

## Why One Clean Lab Per Line

If `L02_TripCommand` and `L03_TripCommand` are both present and both act at
0.5 s, the experiment becomes an L02 + L03 simultaneous trip. That result
cannot be treated as a single-line L03 label.

The recommended design is one independent clean lab .slx per line:

```text
one target line -> one independent clean lab .slx
```

Recommended local models:

```text
IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L02.slx
IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx
IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L04.slx
```

These `.slx` files are local-only and must not be committed.

## Prepare Per-Line L03

Run:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
prepare_ieee39_clean_handwired_breaker_lab_for_line("L03")
```

This creates:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx
```

The script only copies the original clean generated wrapper. It does not insert
a breaker and does not modify Simscape physical-port wiring.

## Manual L03 Target

Open:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx
```

Wire only:

```text
line_id: L03
line block path: Grid/B10 to B13
breaker name: L03_HandwiredTimedBreaker
trip command name: L03_TripCommand
Step time: 0.5 s
Initial value: 0
Final value: 1
```

Do not copy the old handwired model's L03. Do not continue from a clean lab
that already contains L02. Drag a fresh same-type breaker from the Library
Browser, place it in series on one side of `Grid/B10 to B13`, open the original
B10 to B10-to-B13 connection, and do not leave any bypass path.

## Validate After Manual Wiring

After the user manually saves the per-line L03 `.slx`, run:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_line("../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx", "L03")
```

If structure validation passes, run the compact isolated simulation:

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trip_isolated.py --line-id L03 --model-path results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx --timeout-seconds 240 --simulation-stop-time 0.5
```

Only `simulation_success = true` and
`measurement_extraction_status = voltage_speed_angle` can become a
training-ready L03 label.

## Current Label Gate

Clean L02 and per-line clean L03 are the latest successful per-line results:

```text
num_training_ready_labels = 5
num_training_ready_handwired_line_trip_labels = 3
num_unique_handwired_line_ids = 3
allowed_for_dynamic_aware_training = false
```

Because the label count is still below 10, dynamic-aware reranker training
remains blocked.

In short, dynamic-aware reranker training remains blocked.

## Boundaries

- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- Sequential or simultaneous multi-line trip experiments can be studied later,
  but they must not be mixed into single-line label collection.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries.
