# RL Mitigation Reproducibility Gaps

The current implementation is a runnable reproduction framework, not an exact numerical reproduction.

## Data Gaps

- The original paper's IEEE14 one-week 5-minute generation and load chronics are not available in this workspace.
- The repository uses deterministic surrogate chronics with daily load variation, weekly variation, and wind variability.

## Power-Flow Gaps

- The environment currently uses `SurrogatePowerFlowBackend`, a deterministic debug backend that redistributes outage stress to connected lines.
- A production reproduction should add a pandapower or pypower AC backend with explicit islanding and generator-load balancing.

## IEEE5 Gaps

- The IEEE5 case is a mechanism reproduction with 5 buses, 2 generators, 3 loads, and 8 lines.
- It should not be described as exact paper-parameter reproduction unless the paper's full parameters are imported.

## PPO Gaps

- The current PPO trainer is a smoke-capable actor-critic/PPO-style implementation for proving wiring, logs, masking, and artifacts.
- For final paper-level experiments, replace or extend it with full clipped PPO batching and long-run training across all chronics and sampled contingencies.

## Claims Boundary

Do not claim exact reproduction of the paper's numeric figures until the original data, AC backend, random seeds, and environment settings are matched.
