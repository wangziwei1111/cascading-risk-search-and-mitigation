# IEEE39 Multi-Handwired Breaker Expansion

## Purpose

Round 32 extends the validated L01 handwired timed breaker workflow to a
multi-line validation and label-expansion workflow. It still does not insert
breakers automatically and does not modify Simscape physical-port wiring.

## Current Status

- L01 has passed handwired validation.
- L01 compact `single_line_trip` is `handwired_timed_breaker`.
- L01 contributes one training-ready handwired line-trip label.
- L02-L04 are now present in the local handwired model and pass structure
  validation.
- L02 compact simulation timed out in the current run. L03-L04 were not counted
  as training-ready after the L02 timeout.

## Naming Convention

Each manually wired line should use:

```text
Lxx_HandwiredTimedBreaker
Lxx_TripCommand
```

Each trip command should use `Step time = 0.5 s`, with default `Initial value =
0` and `Final value = 1`. If the control direction appears reversed, try
`Initial value = 1` and `Final value = 0`.

## Recommended Next Batch

Wire only two or three lines per round. The next recommended lines are:

```text
L02
L03
L04
```

L05 can be added after that. L06-L10 are listed by the checklist as later
targets, but they require the line map to include those lines first.

## Commands

Generate the checklist:

```powershell
python scripts/gcn_search/print_ieee39_multi_handwired_breaker_checklist.py
```

Validate the local handwired model:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
validate_ieee39_multi_handwired_breakers( ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation", ...
  ["L01","L02","L03","L04"], ...
  "%s_HandwiredTimedBreaker", ...
  "%s_TripCommand" ...
)
```

Run compact line-trip simulations:

```matlab
run_ieee39_multi_handwired_line_trip_suite( ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests", ...
  ["L01","L02","L03","L04"], ...
  0.5 ...
)
```

Merge and export the label gate:

```powershell
python src/gcn_search/legacy_rts79/merge_ieee39_handwired_fault_summaries.py --base-summary-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv --multi-handwired-summary-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_multi_handwired_line_trip_summary.csv --output-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_multi_handwired.csv --output-summary-json results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_multi_handwired_merge_summary.json

python src/gcn_search/legacy_rts79/export_ieee39_dynamic_labels.py --fault-summary-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_multi_handwired.csv --event-log-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_event_log.csv --output-dir results/gcn_search/ieee39_dynamic_labels
```

## Current Compact Result

```text
validation_passed lines = 4
passed line IDs = L01, L02, L03, L04
multi line-trip simulation_success count = 1
num_training_ready_handwired_line_trip_labels = 1
num_training_ready_labels = 3
allowed_for_dynamic_aware_training = false
```

The L02 compact simulation timed out. The conservative summary keeps L02-L04 out
of the training-ready set. Training remains blocked because
`num_training_ready_labels < 10`. If the count eventually reaches ten, the next
step is only preliminary preview training, not an official dynamic performance
conclusion.

Recommended fix: isolate L02 in Simulink and confirm that
`L02_TripCommand` opens only the intended breaker. If the control direction is
reversed, set `Initial value = 1` and `Final value = 0`, then rerun the multi
validation and compact suite.

## Boundaries

- The handwired .slx is a local file and must not be committed.
- The model remains `phasor_RMS`, not EMT.
- The handwired breaker is pilot breaker-like validation, not engineering-grade
  protection.
- `generator_speed_proxy` is not direct frequency.
- This round does not train a dynamic-aware reranker.
