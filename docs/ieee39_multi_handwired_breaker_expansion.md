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
- The user manually revised L02 in the Simulink GUI, and the L02 structure
  validation still passes.
- The old handwired model's L02 compact simulation timed out in the isolated
  240-second run. That old L02 timeout row is not counted as training-ready.
- The old handwired `.slx` has now been retired for further L02-L04 debugging.
  New manual wiring should use the clean breaker lab workflow instead.
- In the clean breaker lab, the user manually wired L02 and the isolated
  compact simulation succeeded. Clean lab L02 is now counted as one additional
  training-ready handwired line-trip label.

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

Do not continue wiring L02-L04 in the old handwired model. Continue from the
clean breaker lab model. L02 is now passed; the next manual target should be
L03:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab.slx
```

After clean L03 passes structure validation and isolated compact simulation,
then consider L04 in a later round.

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

For robust validation after a timeout, use the isolated Python wrapper. It runs
each line in a separate MATLAB process, writes partial summaries after each
line, and kills the MATLAB process tree on timeout:

```powershell
python scripts/gcn_search/run_ieee39_multi_handwired_line_trip_isolated.py --line-ids L01 L02 L03 L04 --timeout-seconds 240 --simulation-stop-time 0.5
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
num_training_ready_handwired_line_trip_labels = 5
num_unique_handwired_line_ids = 5
num_training_ready_labels = 7
allowed_for_dynamic_aware_training = false
```

The old handwired L02 timeout remains in the historical summary as a failed
row, but it is not promoted to training-ready. Clean lab L02 is the successful
L02 result. Training remains blocked because `num_training_ready_labels < 10`.
If the count eventually reaches ten, the next step is only preliminary preview
training, not an official dynamic performance conclusion.
This remains preliminary preview training guidance only, not a final dynamic
performance conclusion.

Recommended next step: continue with L06/L07 in their own per-line clean breaker
labs when their line blocks are mapped. Confirm that each `Lxx_TripCommand`
opens only the matching `Lxx_HandwiredTimedBreaker`, the breaker is really
inserted on the intended line, and opening it does not create an abnormal
Simscape island or disconnected physical network.

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L06.slx
```

Do not add a new target to the same clean lab that already contains another
active line trip. If multiple
TripCommand blocks act at 0.5 s, the run becomes a simultaneous multi-line trip,
not a single-line label. Sequential or simultaneous trip experiments can be
studied later, but they must not be mixed into the single-line label set.

Per-line clean L03, L04, and L05 now pass and are merged as training-ready
handwired line-trip labels. Current formal label gate:

Historical per-line L03 reference model:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx
```

```text
num_training_ready_handwired_line_trip_labels = 5
num_unique_handwired_line_ids = 5
num_training_ready_labels = 7
allowed_for_dynamic_aware_training = false
```

The next manual batch should use independent per-line clean labs for L06 and
L07 if those line IDs are available in the wrapper line map.

## Boundaries

- The handwired .slx is a local file and must not be committed.
- The model remains `phasor_RMS`, not EMT.
- The handwired breaker is pilot breaker-like validation, not engineering-grade
  protection.
- `generator_speed_proxy` is not direct frequency.
- This round does not train a dynamic-aware reranker.

