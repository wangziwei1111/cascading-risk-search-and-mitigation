# IEEE39 Handwired Breaker Validation

## Round 31 Purpose

Round 31 stops automatic Simscape physical-port breaker insertion. The project now supports a safer workflow:

1. The user manually wires a pilot L01 timed breaker or timed controlled switch in Simulink GUI.
2. The user saves a local handwired copy.
3. Codex scripts validate the handwired copy and update the compact label gate.

No dynamic-aware reranker training is performed in this round.

## Why The Workflow Changed

Round 30 found that L01 has four Simscape physical ports and that breaker/switch candidates exist, but the standalone probe did not approve safe automatic physical-port rewiring. To avoid damaging the IEEE39 wrapper, automatic rewiring is stopped.

## Expected Handwired Model

The user should save the handwired local model as:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx
```

This handwired .slx is a local artifact and must not be committed.

Recommended names:

```text
breaker/switch block: L01_HandwiredTimedBreaker
trip command: L01_TripCommand
trip time: 0.5 s
```

## Validation Script

MATLAB script:

```text
matlab/simulink_ieee39/validate_ieee39_handwired_breaker_model.m
```

Before opening or simulating the handwired model on Windows, run:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
```

This avoids the Windows 260-character generated-code path failure by moving
Simulink cache/code-generation artifacts to a short local folder such as
`C:\ieee39_codegen`.

Outputs:

- `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_validation_summary.json`
- `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_validation_summary.csv`
- `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_block_inventory.csv`

Current validation result:

```text
handwired_model_found = false
validation_passed = false
validation_failure_reason = handwired model file not found
```

## Label Gate

The label exporter now recognizes:

- `handwired_timed_breaker`
- `handwired_timed_controlled_switch`

Current compact gate:

```text
num_training_ready_labels = 2
num_training_ready_handwired_line_trip_labels = 0
num_handwired_validation_passed = 0
handwired_model_used = false
handwired_model_committed = false
allowed_for_dynamic_aware_training = false
```

If a future handwired model passes validation and the compact suite confirms `single_line_trip`, then that case can become a training-ready pilot line-trip label. If total training-ready labels remain below ten, dynamic-aware reranker training remains blocked.

## Round 32 Multi-Line Expansion

Round 32 adds a multi-line validation path for future user handwired breakers.
The first recommended expansion batch is `L02`, `L03`, and `L04`, using
`Lxx_HandwiredTimedBreaker` and `Lxx_TripCommand`. L01 remains the reference
passed line. The new scripts validate missing lines without changing the model,
run compact simulations only for validation-passed lines, and keep training
blocked while the total training-ready label count is below ten.

## Boundaries

- Handwired breaker validation is pilot breaker-like validation, not engineering-grade protection.
- The IEEE39 model is `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired `.slx` must not be committed.
- `static_topology_disable` is not a training-ready line-trip label.
