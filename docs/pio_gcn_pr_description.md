# PR Description: PIO-GCN PathRank RTS-79 Preliminary Milestone

## Summary

This PR consolidates the RTS-79 PIO-GCN PathRank cascading-failure path-search work into a review-ready preliminary milestone. It preserves the original `GCN_path_prob` method and adds physics-enhanced features, candidate mask support, original physics loss analysis, pairwise rank-loss analysis, JSON measured-state interface support, compact result artifacts, and review documentation.

## Motivation

The previous GCN search artifacts were spread across smoke runs and intermediate validation folders. This PR cleans that state and makes the current conclusion reviewable: in the 3-seed RTS-79 full-truth preliminary result, the largest observed gain comes from physics-enhanced features, not from candidate mask, original physics loss, or pairwise rank-loss.

## What Changed

- Added and organized PIO-GCN PathRank documentation.
- Preserved original `GCN_path_prob`; no old method is overwritten.
- Added physics-enhanced Step2-state feature support and training documentation.
- Added raw-feature-aware original physics loss logging and analysis.
- Added candidate mask analysis for invalid active outage candidates.
- Added pairwise rank-loss implementation and preliminary comparison.
- Added JSON measured-state interface support for root-case updates.
- Added compact formal preliminary, ablation, and rank-loss result summaries.
- Removed old smoke/full-truth/detail artifacts from Git tracking while keeping local files.
- Added artifact self-check script for PR review.

## Key Preliminary Result Table

3-seed RTS-79 full-truth preliminary result:

| Method | Found@20 | Found@50 | Found@100 | Recall@100 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank with physics-enhanced features | 12.00 | 19.00 | 23.33 | about 42% |
| LODF_yP | 2.00 | 8.00 | 11.67 | about 21% |
| Weak paper-feature `GCN_path_prob` | 5.67 | 7.00 | 8.00 | about 14% |
| Oracle upper bound | 20.00 | 50.00 | 55.33 | 100% |

Next-stage 5-seed RTS-79 full-truth result:

| Method | Recall@100 | Recall@200 |
|---|---:|---:|
| PIO-GCN PathRank | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.350 | 0.568 |
| LODF_yP | 0.207 | 0.329 |

## Ablation Conclusion

- Main contributor: physics-enhanced features.
- Candidate mask: not a major contributor in the current 3-seed preliminary result.
- Original physics loss: very small effect in the current setup.
- Pairwise rank-loss: no Top-20/Top-50 improvement; only a small Top-100 change, so it is not yet decisive.

## Validation Commands

```text
python -m pytest tests/test_cascade_from_case_consistency.py tests/test_measured_state_sanity.py tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_gcn_ranking_loss.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py tests/test_pio_gcn_imports.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
```

## Artifact Policy

Tracked artifacts are limited to docs, config JSON, aggregate summary CSV, method comparison CSV, small diagnostics summary CSV, figures, training metrics CSV, dataset stats JSON, and validation logs.

The following are intentionally not tracked:

- `.pt`
- `.npz`
- full-truth details
- order details
- simulation result details
- smoke-truth details
- per-path score distribution details
- scenario checkpoints

Round-8 cleanup list:

```text
results/gcn_search/tracked_large_files_removed_round8.txt
```

## Limitations

- Only RTS-79 is covered.
- Only 3 full-truth test seeds are used for the key preliminary result.
- The paper-feature baseline is weak under the current small training setup.
- The stronger paper-feature baseline was only trained with 6 completed scenarios because the 20-scenario attempt exceeded the interactive runtime budget.
- The stronger paper-feature baseline v2 was requested for 10 scenarios but completed 7 before the interactive timeout.
- The synthetic renewable perturbation full-truth preliminary run is completed for 3 seeds at 0.30 penetration ratio, but it is still only a synthetic RTS-79 perturbation.
- The measured-state pathway is a JSON measured-state interface only; it is not connected to field SCADA/PMU systems.
- Original physics loss and pairwise rank-loss are implemented and measured, but they are not yet decisive contributors.
- This is a 3-seed RTS-79 full-truth preliminary result, not a final paper-scale claim.

## Synthetic Renewable Preliminary Result

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.237 | 0.347 | 0.426 | 0.495 |
| paper_GCN_path_prob_strong | 0.232 | 0.306 | 0.379 | 0.456 |
| LODF_yP | 0.037 | 0.071 | 0.076 | 0.220 |

This is a synthetic renewable perturbation robustness check only.

## Top-K Depth Tradeoff

PIO-GCN PathRank is stronger at Top-20/50/100 in the 5-seed RTS-79 full-truth extension. The stronger paper-feature baseline surpasses PIO-GCN at Top-200, so the method should be described as useful for rapid small-Top-K screening rather than as a universal winner at all ranking depths.

## Ensemble and Rerank Preliminary

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.211 | 0.338 | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.176 | 0.254 | 0.350 | 0.568 |
| ensemble_alpha_0.75 | 0.200 | 0.345 | 0.444 | 0.549 |
| rerank_physical_stress | 0.280 | 0.439 | 0.532 | 0.587 |

The simple score-level ensemble is feasible but not decisive. The hard-negative-aware rerank gives the clearest improvement in this round, improving Top-100 and Top-200 in the 5-seed RTS-79 preliminary check.

## Learned Path Reranker

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| rerank_physical_stress | 0.280 | 0.439 | 0.532 | 0.587 |
| learned_logistic_reranker | 0.322 | 0.566 | 0.792 | 0.954 |
| learned_mlp_reranker | 0.333 | 0.698 | 0.944 | 0.997 |

The learned path reranker is the strongest current result and exceeds the requested Top-100/Top-200 targets. It is still a 5-seed RTS-79 preliminary result and should not be described as final evidence.

## Leakage Audit and Strict Held-Out Validation

No forbidden input feature was found in the learned path reranker. Strict held-out seed validation still shows strong performance:

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| learned_mlp_reranker_strict | 0.341 | 0.694 | 0.940 | 0.993 |

Feature ablation indicates the strongest signal comes from combining score-derived features with physical stress features. The remaining caveat is limited seed diversity and possible RTS-79 path-pattern memorization, not direct label leakage.

## RL Untouched Statement

This PR does not modify `src/rl_mitigation` or `scripts/rl_mitigation`.

## Reviewer Checklist

- Confirm original `GCN_path_prob` is preserved.
- Confirm script paths in docs match real files.
- Confirm result claims are described as a 3-seed RTS-79 full-truth preliminary result.
- Confirm no `.pt`, `.npz`, full-truth detail, order detail, simulation result detail, smoke-truth detail, or large score-distribution detail is tracked.
- Confirm JSON measured-state interface claims do not imply field measurement system integration.
- Confirm `src/rl_mitigation` and `scripts/rl_mitigation` are untouched.
