# IEEE39 Timed Line-Trip Probe Status

## Round 30 Goal

Round 30 specifically checks whether the IEEE39 wrapper `single_line_trip` can be upgraded from `static_topology_disable` to a real in-simulation timed controlled switch or breaker-like trip.

No dynamic-aware reranker training is performed in this round.

## What Was Checked

The pilot line is:

```text
line_id = L01
line_block_path = IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B1 to B2
```

New compact outputs:

- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_port_inventory.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_compatible_breaker_candidates.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/breaker_probe/breaker_probe_summary.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_timed_switch_insertion_summary.csv`

## Result

The L01 line block exposes four Simscape physical ports:

```text
lconn_count = 2
rconn_count = 2
physical_port_count = 4
port_domain_guess = simscape_physical
switch_insertion_feasible = true
```

The library search found breaker/switch candidates, but the standalone probe did not find an unambiguous candidate with the exact physical-port and control-port structure needed for safe automatic wrapper rewiring.

Current insertion result:

```text
insertion_success = false
trip_implementation = static_topology_disable
physical_fault_or_breaker_action_executed = false
training_ready_candidate = false
note = manual_required
```

Therefore `single_line_trip` has not been upgraded to `timed_controlled_switch`.

## Current Label Gate

```text
num_training_ready_labels = 2
num_training_ready_three_phase_fault_labels = 1
num_training_ready_relay_proxy_labels = 1
num_training_ready_timed_line_trip_labels = 0
measurement_quality_status = partial_dynamic_measurements
label_quality_status = partial_physical_execution
allowed_for_dynamic_aware_training = false
```

## Boundaries

- `static_topology_disable` is not a timed breaker.
- A future `timed_controlled_switch` would still be a pilot breaker-like trip, not engineering-grade protection.
- Frequency remains `generator_speed_proxy`, not a direct frequency measurement.
- The current model is `phasor_RMS`, not EMT.
- With fewer than ten training-ready labels, dynamic-aware reranker training remains blocked.

## Round 31 Follow-Up

Round 31 stops automatic physical-port insertion. The next route is user handwiring in Simulink GUI followed by script validation.

Current handwired validation state:

```text
handwired_model_found = false
validation_passed = false
num_training_ready_handwired_line_trip_labels = 0
```

The handwired `.slx` is a local artifact and must not be committed.
