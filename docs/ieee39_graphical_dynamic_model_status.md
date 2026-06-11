# IEEE39 Graphical Dynamic Model Status

## Round 26 Status

Round 26 paused dynamic-aware reranker training and focused on finding and preparing an IEEE39 graphical dynamic simulation backend.

## What Was Found

| Model | Path | Status |
|---|---|---|
| MathWorks IEEE39BusSystem example | `C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx` | found and opened |
| Local user copy | `C:/Users/24186/Desktop/山东项目/IEEE39BusSystemExample/IEEE39BusSystem.slx` | found and opened |

Primary model:

`C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx`

## Toolbox Check

Output:

`results/gcn_search/ieee39_graphical_dynamic_model/toolbox_check_summary.json`

Installed:

- Simulink
- Simscape
- Simscape Electrical
- Stateflow
- Simulink Control Design

## Inventory Output

Outputs:

- `results/gcn_search/ieee39_graphical_dynamic_model/model_inventory.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/model_inventory.json`

Current classification:

- model type: `phasor_RMS`
- contains generators: yes
- contains exciters: yes
- contains governors: yes
- contains lines / grid: yes
- contains loads: yes
- contains measurements: yes
- contains protection: not complete / not verified
- contains breakers: not verified by wrapper inventory

## Wrapper Status

Wrapper script:

`matlab/simulink_ieee39/setup_ieee39_dynamic_experiment_wrapper.m`

Generated local copy:

`results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx`

The generated `.slx` is local output and is not committed.

## Fault-Test Status

Fault-test script:

`matlab/simulink_ieee39/run_ieee39_fault_test_suite.m`

Outputs:

- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_event_log.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_signal_summary.csv`

Current interpretation:

- `no_fault_sanity` ran as an open-model sanity check and succeeded.
- `single_line_trip`, `three_phase_fault_clear`, `ordered_N2_trip`, and `relay_trip_test` are schema rows only in this round.
- Real breaker/fault/protection wiring still needs to be added before these rows can be used as physical dynamic labels.

## Dynamic Label Interface

Script:

`src/gcn_search/legacy_rts79/export_ieee39_dynamic_labels.py`

Outputs:

- `results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_preview.csv`
- `results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_schema.json`

The schema is ready for later dynamic-aware reranker training, but the current labels are only preliminary interface rows.

## Limitations

- This is not an EMT claim.
- This is not an engineering-grade protection model.
- The generated wrapper does not yet execute real N-2 breaker trips.
- The current fault-test outputs are interface validation, not final dynamic training labels.
- No dynamic-aware reranker training was performed in Round 26.

## Next Step

Wire physical fault blocks, breaker controls, and measurement export into the IEEE39 wrapper, then run real IEEE39 N-1/N-2 dynamic cases and train the dynamic-aware reranker from the generated labels.

## Round 27 Update

Round 27 started the fault / breaker / measurement / relay wrapper.

New outputs:

- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_build_summary.json`
- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_block_inventory.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_signal_map.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_fault_injection_points.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/protection/ieee39_basic_relay_settings.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/protection/ieee39_basic_relay_status.json`
- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_relay_trip_log.csv`
- `results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json`

Current Round 27 interpretation:

- Existing three-phase fault block was found in the IEEE39 grid subsystem.
- Five pilot line blocks were mapped.
- No explicit breaker block was found automatically.
- Pilot line trips currently use line-block disabling, not timed breaker controls.
- Basic relay proxy was added as settings/status output only; it is not engineering-grade relay coordination.
- Full five-case automated graphical simulation exceeded the available tool timeout, so the current quality gate remains conservative.
- `allowed_for_dynamic_aware_training = false`.

The model is still treated as `phasor_RMS`, not EMT.

## Round 28 Update

Round 28 moves from schema-only rows to partial physical execution.

Current compact results:

- `num_fault_rows = 4`
- `num_physical_executed_rows = 2`
- `num_training_ready_labels = 2`
- `label_quality_status = partial_physical_execution`
- `allowed_for_dynamic_aware_training = false`

The two training-ready candidates are preliminary small-sample physical rows, not enough for training. The current minimum requirement remains at least ten physical executed and simulation-successful labels.

Measurement extraction status is `partial`; unavailable values are recorded as `NaN` rather than fixed placeholders.
