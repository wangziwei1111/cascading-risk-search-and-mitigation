# IEEE39 Timed Breaker Manual Wiring Guide

## Why This Guide Exists

Round 30 did not safely insert an automatic timed controlled switch into the IEEE39 wrapper. The L01 line has four Simscape physical ports, while the discovered breaker/switch candidates did not provide an unambiguous, validated four-port controlled replacement path.

The wrapper was left unchanged.

Current status is `manual_required`.

`static_topology_disable` is not a timed breaker.

## Target Line

```text
line_id = L01
line_block_path = IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B1 to B2
mask_type = Transmission Line (Three-Phase)
lconn_count = 2
rconn_count = 2
physical_port_count = 4
```

## Recommended Manual Work

1. Open the generated wrapper locally:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
open_system("../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx")
```

2. Navigate to:

```text
IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B1 to B2
```

3. Inspect the two left physical ports and two right physical ports of the L01 transmission-line block.

4. Insert a Simscape-compatible controlled switch or breaker-like block that preserves the same physical domain connections.

5. Add a control signal with:

```text
closed before 0.5 s
open after 0.5 s
```

6. Save only the handwired wrapper copy locally:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx
```

Do not commit the generated or handwired `.slx`.

7. Rerun the compact suite on the handwired copy:

```matlab
run_ieee39_fault_test_suite( ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests", ...
  true, ...
  ["no_fault_sanity", "three_phase_fault_clear", "single_line_trip", "relay_trip_test"], ...
  0.5, ...
  true ...
)
```

8. Re-export label quality:

```bash
python ../../src/gcn_search/legacy_rts79/export_ieee39_dynamic_labels.py \
  --fault-summary-csv ../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv \
  --event-log-csv ../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_event_log.csv \
  --output-dir ../../results/gcn_search/ieee39_dynamic_labels
```

## Acceptance Criteria

Manual wiring is not accepted until the compact summary reports:

```text
single_line_trip trip_implementation = timed_controlled_switch
physical_fault_or_breaker_action_executed = true
training_ready_candidate = true
trip_time_s = 0.5
```

If these fields are not satisfied, `single_line_trip` must remain non-training-ready.

## Round 31 Validation Interface

Round 31 stops automatic physical-port insertion. After the user manually saves the handwired copy, run:

```matlab
configure_ieee39_short_filegen_paths()
validate_ieee39_handwired_breaker_model( ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation", ...
  "L01", ...
  "L01_HandwiredTimedBreaker", ...
  "L01_TripCommand" ...
)
```

The helper checklist can be printed with:

```bash
python scripts/gcn_search/print_ieee39_handwired_breaker_checklist.py
```

The handwired `.slx` must remain local and must not be committed.

## Windows Path-Length Fix

If Simulink reports that the generated C file path is longer than the Windows
260-character limit, run this before opening or simulating the model:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
```

This redirects Simulink cache/code-generation files to a short local folder
such as `C:\ieee39_codegen`. The folder is outside the repository and must not
be committed.

## Boundaries

- This is still `phasor_RMS`, not EMT.
- This is a pilot breaker-like trip, not engineering-grade protection.
- `static_topology_disable` must not be described as a timed breaker.
- `generator_speed_proxy` is not a direct frequency measurement.
- If `num_training_ready_labels < 10`, do not train the dynamic-aware reranker.
