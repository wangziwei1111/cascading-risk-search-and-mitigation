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

PIO-GCN PathRank entrypoints:

```powershell
python src/gcn_search/legacy_rts79/generate_rts79_step2_state_dataset.py --num-scenarios 1 --feature-mode physics
python src/gcn_search/legacy_rts79/train_rts79_physics_gcn.py --dataset-npz <physics_dataset.npz> --epochs 1
python src/gcn_search/legacy_rts79/evaluate_rts79_pio_gcn_topk.py --model <model.pt> --normalizer <normalizer.json> --top-k 20 50 100
python src/gcn_search/legacy_rts79/run_pio_gcn_formal_small_experiment.py --output-dir results/gcn_search/pio_formal_preliminary_3seed --test-num-seeds 3 --top-k 20 50 100
python src/gcn_search/legacy_rts79/run_pio_gcn_formal_ablation.py --output-dir results/gcn_search/pio_formal_ablation_3seed --base-experiment-dir results/gcn_search/pio_formal_preliminary_3seed --top-k 20 50 100
python src/gcn_search/legacy_rts79/run_pio_gcn_rank_loss_experiment.py --output-dir results/gcn_search/pio_rank_loss_preliminary_3seed --base-experiment-dir results/gcn_search/pio_formal_preliminary_3seed
python src/gcn_search/legacy_rts79/run_pio_gcn_renewable_preliminary_experiment.py --output-dir results/gcn_search/pio_renewable_preliminary --renewable-penetration-ratio 0.30 --top-k 20 50 100 200
python src/gcn_search/legacy_rts79/analyze_topk_depth_tradeoff.py --output-dir results/gcn_search/pio_topk_depth_tradeoff
python src/gcn_search/legacy_rts79/evaluate_pio_gcn_ensemble_ranking.py --output-dir results/gcn_search/pio_ensemble_preliminary
python src/gcn_search/legacy_rts79/evaluate_pio_gcn_hard_negative_rerank.py --output-dir results/gcn_search/pio_rerank_preliminary
python src/gcn_search/legacy_rts79/build_path_reranker_dataset.py --output-dir results/gcn_search/path_reranker_dataset
python src/gcn_search/legacy_rts79/train_path_reranker.py --dataset-dir results/gcn_search/path_reranker_dataset --output-dir results/gcn_search/path_reranker_models
python src/gcn_search/legacy_rts79/evaluate_path_reranker_fulltruth.py --dataset-dir results/gcn_search/path_reranker_dataset --model-dir results/gcn_search/path_reranker_models --output-dir results/gcn_search/path_reranker_fulltruth_eval
python scripts/gcn_search/check_pio_gcn_artifacts.py
```

JSON measured-state interface example:

```text
examples/rts79_measured_state_example.json
```

Key reports and outputs:

```text
results/gcn_search/
```

Current PIO-GCN PathRank preliminary conclusion:

- The most effective current component is physics-enhanced branch features.
- On the 3-seed RTS-79 full-truth preliminary result, Top-100 recall is around 42%.
- LODF_yP is around 21% Top-100 recall, and the weak paper-feature `GCN_path_prob` baseline is around 14%.
- Candidate mask, original physics loss, and pairwise rank-loss are not the main contributors in the current preliminary results.
- The 5-seed extension shows a depth tradeoff: PIO-GCN PathRank remains better at Top-20/50/100, while a stronger paper-feature baseline can surpass it at Top-200.
- The latest hard-negative-aware rerank improves Top-100 and Top-200 in the 5-seed preliminary check; simple score-level ensemble is feasible but not decisive.
- The learned path reranker is the strongest current result, but it is still only a 5-seed RTS-79 preliminary result.
- The synthetic renewable perturbation run is completed for 3 seeds at 0.30 penetration ratio, but it is only a synthetic RTS-79 robustness check.
- These are RTS-79 3-seed preliminary results, not final paper-scale performance claims.
- The online-state feature is a JSON measured-state interface only; it is not connected to field SCADA/PMU systems.

Stage summary and review materials:

```text
docs/pio_gcn_stage_summary.md
docs/pio_gcn_advisor_brief.md
docs/pio_gcn_pr_description.md
docs/pio_gcn_reproduction_commands.md
docs/pio_gcn_renewable_preliminary.md
docs/pio_gcn_topk_depth_tradeoff.md
docs/pio_gcn_ensemble_rerank_preliminary.md
docs/pio_gcn_path_reranker.md
docs/pio_gcn_hard_negative_analysis.md
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
+ JSON measured-state interface update
+ model-guided small-sample physical simulation
```

Details are summarized in:

```text
docs/gcn_current_progress.md
```
