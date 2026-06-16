# IEEE39 Baseline Comparison Plan

Future GCN usefulness audit must compare against no-leakage baselines.

- `Ridge Regression`: numeric regression baseline for proxy target difficulty
- `Logistic Regression`: binary stable / unstable baseline
- `RandomForest or GradientBoosting`: nonlinear tabular baseline if repo dependencies allow
- `simple ranking baseline`: rank-order baseline without GCN message passing
- `topology-only baseline`: check how much graph structure alone explains labels
- `target-bus-only baseline`: detect whether target_bus encoding can memorize label distribution

## GCN Can Be Called Useful Only If

- uses no-leakage features
- beats simple baselines on bus_fault_holdout and leave_one_bus_fault_out
- does not depend on post-fault compact dynamic measurements
- does not silently fail on B1 stable/low-risk marker
- does not look good only on random split
- keeps explicit confidence and limitation language, not final engineering conclusion
