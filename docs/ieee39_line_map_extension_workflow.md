# IEEE39 Line Map Extension Workflow

## Purpose

This round extends the IEEE39 wrapper line map before any new manual breaker
wiring. The goal is to confirm real Simulink `Grid` block paths from the
generated wrapper inventory, then prepare independent local clean lab `.slx`
files for later user wiring.

Current successful single-line labels:

```text
L01
clean lab L02
per-line clean lab L03
per-line clean lab L04
per-line clean lab L05
num_training_ready_labels = 10
num_training_ready_handwired_line_trip_labels = 8
num_unique_handwired_line_ids = 8
allowed_for_dynamic_aware_training = true
```

The label count has now reached the preview threshold after L06/L07/L08
validation. Do not train the dynamic-aware reranker in this round; run preview training in a separate commit.
The follow-up preview training commit uses
`scripts/gcn_search/train_ieee39_dynamic_aware_reranker_preview.py` and keeps
the result explicitly preview-only.

## Inventory Step

Run the read-only Simulink inventory:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
inspect_ieee39_wrapper_grid_line_blocks()
```

Outputs:

```text
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.json
```

The inventory is produced from real blocks under
`IEEE39BusSystem_dynamic_experiment_wrapper/Grid`. Do not invent a block path.

## Extended Map Rule

Run:

```powershell
python scripts/gcn_search/update_ieee39_line_breaker_map_from_inventory.py
```

Outputs:

```text
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extended.csv
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extension_summary.json
```

Mapping rule: preserve L01-L05 exactly from the existing map. For L06-L10, use
unused real line-like Grid blocks from the inventory in ascending
`inventory_index` order. If a later line cannot be verified from inventory, it
must remain `not_in_current_line_map`.

Mapped and validated L06/L07/L08 targets:

```text
L06 -> Grid/B14 to B15
L07 -> Grid/B15 to B16
L08 -> Grid/B16 to B17
```

Mapped next manual targets:

```text
L09 -> Grid/B16 to B24
L10 -> Grid/B17 to B27
```

## Clean Lab Preparation

Run:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
prepare_ieee39_clean_handwired_breaker_labs_for_lines(string({'L09','L10'}))
```

Local-only prepared models:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L09.slx
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L10.slx
```

One line uses one independent per-line clean lab .slx:

```text
L09 model: wire only L09_HandwiredTimedBreaker and L09_TripCommand on Grid/B16 to B24
L10 model: wire only L10_HandwiredTimedBreaker and L10_TripCommand on Grid/B17 to B27
```

Do not place multiple active breakers in one single-line label model. Sequential
or simultaneous multi-line trip experiments can be studied later, but must not
be mixed into the single-line label set.

## After Manual Wiring

After the user manually wires and saves L09/L10, validation should run first:

```matlab
validate_ieee39_clean_breaker_lab_lines_batch(["L09","L10"])
```

Only after validation passes, run compact simulation:

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L09 L10 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx" --timeout-seconds 240 --simulation-stop-time 0.5
```

This round only prepares L09/L10 clean lab files. It does not wire breakers,
run L09/L10 compact simulation, or train the dynamic-aware reranker.

## Boundaries

- Do not automatically insert breakers.
- Do not modify Simscape physical-port wiring.
- Do not overwrite L02/L03/L04/L05 successful results.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- .slx files are local-only and must not be committed.
- Do not commit `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries.

## Full line map and remaining clean lab preparation

The latest full map file is:

- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv`

It preserves the verified `L01-L10` mapping and appends unused line-like Grid
blocks as `L11-L34`. The current gate is:

- `num_training_ready_labels = 12`
- `num_training_ready_handwired_line_trip_labels = 10`
- `num_unique_handwired_line_ids = 10`
- `allowed_for_dynamic_aware_training = true`

`L09` and `L10` have passed validation and compact isolated simulation:

- `L09`: `Grid/B16 to B24`
- `L10`: `Grid/B17 to B27`

Remaining prepared-but-unwired clean lab models are `L11-L34`. They are local
`.slx` files prepared from the wrapper only; the prepare step does not invent a
block path, does not auto-insert breakers, does not modify Simscape physical
wiring, and no dynamic-aware reranker training was run.
