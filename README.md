# Cascading Risk Search and Mitigation

Public repository:

```text
https://github.com/wangziwei1111/cascading-risk-search-and-mitigation
```

This repository records the reproduction and extension work for power-system cascading-failure risk search and mitigation.

## Main Contents

### 1. IEEE RTS-79 GCN cascading-failure path search

This is the current GCN-focused work.

Core idea:

```text
Sequential improved OPA simulator
+ reachable GCN
+ path-level probability ranking
```

The reproduced RTS-79 workflow searches ordered N-2 cascading-failure paths. It treats transmission branches as graph nodes, trains a reachable GCN to estimate whether a candidate branch can reach load shedding within the remaining search depth, and ranks complete ordered paths with path-level probability.

Read first:

```text
docs/README_RTS79_REPRODUCTION.md
docs/gcn_current_progress.md
docs/gcn_search_reproduction.md
```

Key source code:

```text
src/gcn_search/legacy_rts79/
```

Key reports and outputs:

```text
results/gcn_search/
```

### 2. RL cascade mitigation reproduction

This part records a separate reinforcement-learning mitigation reproduction line based on IEEE14/IEEE118 experiments.

Read first:

```text
docs/rl_paper_reproduction_status.md
docs/rl_paper_figure_index.md
docs/rl_mitigation_reproduction.md
```

Key source code:

```text
src/rl_mitigation/
scripts/rl_mitigation/
```

## Current RTS-79 GCN Result Boundary

The RTS-79 GCN work has completed:

- improved OPA cascading-failure simulator;
- deterministic ordered N-2 path simulation with `R = 2`;
- relay protection, island load shedding, and redispatch OPF logic;
- Step2-State dataset generation;
- reachable GCN training;
- path-level GCN probability ranking;
- comparison with LODF_yP, random search, and line-order search.

Current test summary:

```text
Average critical paths across 5 load scenarios: 56.6
GCN_path_prob average searches to find all critical paths: 68.2
LODF_yP average searches: 1259.8
random average searches: 1378.0
line_order average searches: 1332.6
```

The current GCN is a ranking accelerator. Final path criticality is still verified by the physical OPA/OPF simulator.

## Suggested Next Extension

The next research direction is:

```text
offline data-driven base model
+ physics constraints
+ online measured-state update
+ model-guided small-sample physical simulation
```

Details are summarized in:

```text
docs/gcn_current_progress.md
```
