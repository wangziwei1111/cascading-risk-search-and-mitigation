# PIO-GCN Synthetic Renewable Preliminary Result

## Status

The synthetic renewable perturbation module, example configuration, tests, preliminary experiment script, and 3-seed full-truth preliminary run have been completed.

## Scope

This is only a synthetic renewable perturbation on RTS-79. It is not:

- a real renewable power-system model;
- an EMT simulation;
- a dynamic stability simulation;
- a field SCADA/PMU integration.

The purpose is only to check whether PIO-GCN PathRank remains usable when renewable-like output fluctuation changes the initial operating condition. It is a synthetic renewable robustness check, not a real renewable grid study.

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

## Completed Preliminary Experiment

```text
src/gcn_search/legacy_rts79/run_pio_gcn_renewable_preliminary_experiment.py
```

Completed configuration:

```text
renewable_penetration_ratio = 0.30
fluctuation_low = 0.6
fluctuation_high = 1.1
test_seed_start = 20260722
test_num_seeds = 3
top_k = 20, 50, 100, 200
run_full_truth = true
```

Output directory:

```text
results/gcn_search/pio_renewable_preliminary/
```

## Key Results

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.237 | 0.347 | 0.426 | 0.495 |
| paper_GCN_path_prob_strong | 0.232 | 0.306 | 0.379 | 0.456 |
| LODF_yP | 0.037 | 0.071 | 0.076 | 0.220 |
| oracle | 0.368 | 0.913 | 1.000 | 1.000 |

PIO-GCN PathRank remains ahead of the stronger paper-feature baseline and LODF_yP through Top-200 in this 3-seed synthetic renewable preliminary result.

## Validation

Unit test:

```text
tests/test_renewable_scenarios.py
```

The test checks reproducibility, finite values, penetration-ratio recording, and that the original base case is not modified in place.

## Current Limitation

This is still a synthetic renewable perturbation on RTS-79 only. It should not be reported as a real renewable power-system conclusion, a dynamic stability result, or field-measurement validation.
