# IEEE39 Fault / Breaker / Relay Wrapper

## Round 27 Purpose

Round 27 starts wiring a real IEEE39 graphical dynamic wrapper around the local MathWorks `IEEE39BusSystem.slx` model.

The selected model remains:

`C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx`

The source `.slx` is preserved. The wrapper script copies it to:

`results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx`

The generated `.slx` is local output and is not committed.

## Current Model Type

The model is treated as `phasor_RMS` in this project.

This is not EMT-level validation.

## Wrapper Build Status

Outputs:

- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_build_summary.json`
- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_block_inventory.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_signal_map.csv`

Current status:

- Existing three-phase fault block was found.
- Five pilot transmission lines were mapped.
- No explicit breaker blocks were found by automatic inventory.
- Breaker wiring is `manual_required`.
- Pilot line trip currently disables mapped transmission-line blocks before simulation.

## Pilot Line Mapping

Output:

`results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv`

The current map is a pilot map, not a full protection model. It maps at least five line blocks and records missing breaker paths as manual wiring work.

## Basic Relay Proxy

Output:

- `results/gcn_search/ieee39_graphical_dynamic_model/protection/ieee39_basic_relay_settings.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/protection/ieee39_basic_relay_status.json`

The relay logic is a basic relay proxy:

- undervoltage threshold
- underfrequency threshold
- optional overcurrent proxy
- trip latch
- breaker command proxy

It is not engineering-grade relay coordination.

## Fault-Test Status

Output:

- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_event_log.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_signal_summary.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_relay_trip_log.csv`

Important interpretation:

- A real no-fault simulation and a pilot disabled-line simulation were separately verified during development.
- The full five-case automated fault-test run exceeded the available tool timeout in this environment.
- The committed compact summary therefore keeps the quality gate conservative.
- `single_line_trip`, `three_phase_fault_clear`, `ordered_N2_trip`, and `relay_trip_test` are not yet training-ready dynamic labels.

## Dynamic Label Quality Gate

Output:

`results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json`

Current status:

```text
label_quality_status = schema_only
allowed_for_dynamic_aware_training = false
```

Dynamic labels must pass this quality gate before training a dynamic-aware reranker.

## Next Work

The next step is manual or scripted wiring of breaker controls and measurement extraction inside the generated IEEE39 wrapper, followed by a successful full fault-test run with at least ten physical executed and simulation-successful rows.

## Round 28 Update

Round 28 produced a small real-execution set:

- `no_fault_sanity`: real simulation, sanity only.
- `three_phase_fault_clear`: real simulation with the existing `Fault (Three-Phase)` block.
- `relay_trip_test`: real simulation with basic relay proxy.
- `single_line_trip`: real simulation with static topology disable; this is not a timed breaker and is not training-ready.

Current quality gate:

```text
label_quality_status = partial_physical_execution
allowed_for_dynamic_aware_training = false
```

Measurement extraction remains `partial`; missing signals are reported as `NaN`, not placeholder measurements.

## Round 29 Update

Round 29 adds a Simscape log-tree inventory and compact measurement extraction:

- `ieee39_simlog_tree_inventory.csv`
- `ieee39_simlog_tree_inventory.json`
- `ieee39_signal_extraction_debug.json`

The current extractor uses generator terminal voltage, rotor velocity, and rotor electrical angle from `simlog_IEEE39BusSystem`. Frequency is reported as `generator_speed_proxy`, computed from rotor speed, and must not be described as a direct frequency measurement.

The single-line trip check remains conservative. No explicit breaker was found on the mapped line, and automatic insertion of a timed controlled switch was not completed in a way that can be treated as a physical training label. Therefore:

```text
single_line_trip trip_implementation = static_topology_disable
single_line_trip training_ready_candidate = false
allowed_for_dynamic_aware_training = false
```

The next breaker step is manual or carefully scripted Simscape physical-port rewiring, followed by rerunning the same compact fault-test suite.

## Round 30 Update

Round 30 adds a dedicated timed line-trip probe workflow:

- `inspect_ieee39_line_ports.m`
- `find_compatible_ieee39_breaker_blocks.m`
- `probe_ieee39_breaker_insertion_standalone.m`
- `insert_ieee39_timed_line_switch.m`

The L01 transmission line exposes four Simscape physical ports. The installed-library search found many switch/breaker-named candidates, but the standalone probe did not find an unambiguous controlled breaker/switch suitable for automatic wrapper rewiring.

Current line-trip status:

```text
insertion_success = false
implementation_status = manual_required
trip_implementation = static_topology_disable
training_ready_candidate = false
```

This result must not be described as a timed breaker. A timed controlled switch, if later added manually, remains a pilot breaker-like trip and not engineering-grade protection.
