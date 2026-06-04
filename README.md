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
docs/pio_gcn_method.md
```

Key source code:

```text
src/gcn_search/legacy_rts79/
```

PIO-GCN smoke entrypoints:

```powershell
python generate_rts79_step2_state_dataset.py --num-scenarios 1 --feature-mode physics
python train_rts79_physics_gcn.py --dataset-npz <physics_dataset.npz> --epochs 1
python evaluate_rts79_pio_gcn_topk.py --model <model.pt> --normalizer <normalizer.json> --top-k 20 50 100
python run_pio_gcn_ablation.py --model <model.pt> --normalizer <normalizer.json>
```

Online measured-state input example:

```text
examples/rts79_measured_state_example.json
```

Key reports and outputs:

```text
results/gcn_search/
```

Current PIO-GCN preliminary conclusion:

- The most effective current component is physics-enhanced branch features.
- On 3 RTS-79 full-truth preliminary seeds, Top-100 recall is around 42%.
- LODF_yP is around 21% Top-100 recall, and the weak paper-feature `GCN_path_prob` baseline is around 14%.
- Candidate mask, original physics loss, and rank-loss are not the main contributors in the current preliminary results.
- These are RTS-79 3-seed preliminary results, not final paper-scale performance claims.
- The online-state feature is a JSON measured-state interface only; it is not a real SCADA/PMU integration.

Stage summary and review materials:

```text
docs/pio_gcn_stage_summary.md
docs/pio_gcn_advisor_brief.md
docs/pio_gcn_pr_description.md
docs/pio_gcn_reproduction_commands.md
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
