# PIO-GCN Synthetic Renewable Preliminary Plan

## Status

The synthetic renewable perturbation module, example configuration, tests, and preliminary experiment script have been added. The renewable full-truth experiment was not run in this round because the extended 5-seed full-truth experiment was prioritized.

## Scope

This is only a synthetic renewable perturbation on RTS-79. It is not:

- a real renewable power-system model;
- an EMT simulation;
- a dynamic stability simulation;
- a real SCADA/PMU-connected online deployment.

The purpose is only to check whether PIO-GCN PathRank remains usable when renewable-like output fluctuation changes the initial operating condition.

## Added Module

```text
src/gcn_search/legacy_rts79/renewable_scenarios.py
```

Main API:

```text
RenewableScenarioConfig
apply_renewable_scenario_to_case(case, config)
make_renewable_rts79_initial_config(seed, renewable_config)
summarize_renewable_case(case_before, case_after, config)
```

Example:

```text
examples/rts79_renewable_scenario_example.json
```

## Preliminary Experiment Script

```text
src/gcn_search/legacy_rts79/run_pio_gcn_renewable_preliminary_experiment.py
```

Recommended configuration:

```text
renewable_penetration_ratio = 0.2 or 0.3
fluctuation_low = 0.6
fluctuation_high = 1.1
test_num_seeds = 3 or 5
top_k = 20, 50, 100, 200
run_full_truth = true
```

Expected output directory:

```text
results/gcn_search/pio_renewable_preliminary/
```

## Validation So Far

Unit test added:

```text
tests/test_renewable_scenarios.py
```

The test checks reproducibility, finite values, penetration-ratio recording, and that the original base case is not modified in place.

## Current Limitation

No renewable full-truth result is reported yet. It should be treated as a prepared next experiment, not as completed evidence.
