# PIO-GCN Stage Summary

## Project Goal

This project reproduces and extends RTS-79 cascading-failure path search. The goal is to build a stable improved OPA simulator and use GCN-based ranking to find critical ordered N-2 outage paths faster than simple exhaustive search or physical-rule ordering.

In plain Chinese: we first make a simulator that can follow "trip one line, settle the system, trip the next line", then train a model to rank which ordered paths are more likely to cause load shedding.

## Limitation of the Original GCN_path_prob Baseline

The original `GCN_path_prob` path score is preserved and not overwritten. It ranks a path by multiplying GCN probabilities along the path:

```text
score(L_i -> L_j) = p_shed(L_i | S0) * p_shed(L_j | S1(i))
```

Its limitation in this project is not the path-probability idea itself, but the weak information available to the model when using the original paper-style 4-feature input and small preliminary training. On the 3-seed full-truth RTS-79 preliminary test, the weak paper-feature model reaches only about 14% Top-100 recall.

## PIO-GCN Improvements

PIO-GCN adds four practical improvements around the preserved path-probability search:

- Physics-enhanced branch features: loading ratio, relay margin, security margin, online status, candidate status, and related physical quantities.
- Raw-feature-aware original physics loss: model input uses normalized features, while physics constraints use raw loading and status features.
- Candidate mask: offline, used, or invalid branches are masked out during candidate scoring.
- JSON measured-state interface: online state can update the root case before Top-K search. This is a JSON measured-state interface only, not connected to field SCADA/PMU systems.

## Current Code Modules

- `src/gcn_search/legacy_rts79/rts79_cascade.py`: RTS-79 improved OPA cascade simulator.
- `src/gcn_search/legacy_rts79/generate_rts79_step2_state_dataset.py`: Step2-state dataset generation.
- `src/gcn_search/legacy_rts79/train_rts79_physics_gcn.py`: physics-enhanced feature and physics-informed GCN training.
- `src/gcn_search/legacy_rts79/gcn_physics_constraints.py`: candidate mask, relay/security original physics losses, and pairwise rank-loss.
- `src/gcn_search/legacy_rts79/evaluate_rts79_pio_gcn_topk.py`: PIO-GCN Top-K online search evaluation.
- `src/gcn_search/legacy_rts79/run_pio_gcn_formal_small_experiment.py`: 3-seed RTS-79 full-truth preliminary result.
- `src/gcn_search/legacy_rts79/run_pio_gcn_formal_ablation.py`: formal preliminary ablation.
- `src/gcn_search/legacy_rts79/run_pio_gcn_rank_loss_experiment.py`: pairwise rank-loss preliminary comparison.

## Fifth-Round 3-Seed Full-Truth Preliminary Result

Output directory:

```text
results/gcn_search/pio_formal_preliminary_3seed/
```

Key result:

| Method | Top-20 found | Top-50 found | Top-100 found | Top-100 recall |
|---|---:|---:|---:|---:|
| PIO_GCN_Top100 | 12.00 | 19.00 | 23.33 | 0.4213 |
| original_GCN_path_prob | 5.67 | 7.00 | 8.00 | 0.1435 |
| LODF_yP | 2.00 | 8.00 | 11.67 | 0.2099 |
| oracle | 20.00 | 50.00 | 55.33 | 1.0000 |

This shows that the physics-enhanced features in PIO-GCN PathRank are much better than the weak paper-feature GCN and LODF_yP in this small RTS-79 preliminary setting.

## Sixth-Round Ablation Result

Output directory:

```text
results/gcn_search/pio_formal_ablation_3seed/
```

Key result:

| Method | Top-100 recall | Main interpretation |
|---|---:|---|
| physics_ce_no_mask | 0.4209 | Physics-enhanced features are already effective. |
| physics_ce_mask | 0.4209 | Candidate mask does not materially change this 3-seed result. |
| physics_loss_no_mask | 0.4213 | Original physics loss adds only a tiny change. |
| physics_loss_mask | 0.4213 | Mask plus original physics loss is still not the main contributor. |
| paper_gcn_path_prob | 0.1435 | Weak paper-feature baseline. |
| LODF_yP | 0.2099 | Physical-rule baseline. |

The most credible conclusion is that the main gain currently comes from physics-enhanced features, not from candidate mask or original physics loss.

## Seventh-Round Pairwise Rank-Loss Result

Output directory:

```text
results/gcn_search/pio_rank_loss_preliminary_3seed/
```

Pairwise rank-loss tries to directly improve path ordering by making reachable positive branches score higher than negative candidate branches within the same state.

| Method | Top-20 found | Top-50 found | Top-100 found | Top-100 recall |
|---|---:|---:|---:|---:|
| physics_ce_mask | 12.33 | 19.33 | 23.33 | 0.4209 |
| physics_loss_mask | 12.00 | 19.00 | 23.33 | 0.4213 |
| physics_rank_loss_mask | 12.33 | 19.33 | 24.00 | 0.4337 |

The pairwise rank-loss model does not improve Top-20 or Top-50. It gives a small Top-100 increase, but this is not yet strong enough to call pairwise rank-loss a major contributor. For reporting, the honest conclusion is: pairwise rank-loss is implemented and may slightly help Top-100, but it has not yet produced a clear, robust improvement.

## Most Trustworthy Current Conclusions

- The improved OPA simulator and ordered N-2 search workflow are in place.
- The most effective component so far is physics-enhanced features.
- Preliminary Top-100 recall is around 42% on 3 RTS-79 full-truth seeds.
- LODF_yP is around 21% Top-100 recall.
- The weak paper-feature GCN_path_prob baseline is around 14% Top-100 recall.
- Candidate mask, original physics loss, and pairwise rank-loss are not the main sources of improvement in the current experiment.

## What We Cannot Claim Yet

- We cannot claim final performance.
- We cannot claim large-scale statistical significance.
- We cannot claim Henan-grid reproduction.
- We cannot claim connection to field SCADA/PMU measurement systems.
- We cannot claim that original physics loss is already a decisive improvement.
- We cannot claim pairwise rank-loss has robustly improved Top-20 or Top-50 search.

## Next-Stage Suggestions

- Expand from 3 seeds to a larger RTS-79 test set.
- Train on more load scenarios and tune `lambda_rank`, `rank_margin`, and candidate sampling.
- Calibrate model probabilities to reduce over-prediction.
- Compare against stronger physical baselines and a better-trained paper-feature model.
- Keep the current PIO-GCN branch as a reviewable preliminary milestone before adding new algorithms.

## Next-Stage Shortcoming Fixes

The next-stage update expands the evaluation beyond the original 3-seed preliminary result.

Extended full-truth output:

```text
results/gcn_search/pio_extended_fulltruth_5seed/
```

Key 5-seed RTS-79 full-truth result:

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.211 | 0.338 | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.176 | 0.254 | 0.350 | 0.568 |
| LODF_yP | 0.036 | 0.134 | 0.207 | 0.329 |
| oracle | 0.356 | 0.890 | 1.000 | 1.000 |

The stronger paper-feature baseline was trained with 6 completed scenarios after the intended 20-scenario run exceeded the interactive runtime budget. It is stronger than the old weak baseline, but still not a fully tuned paper baseline.

The synthetic renewable perturbation module and tests are implemented, but the renewable full-truth experiment has not yet been run. It remains a prepared next experiment, not a completed result.
