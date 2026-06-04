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
- The synthetic renewable perturbation module is implemented and tested, but renewable full-truth results have not yet been run.
- The measured-state pathway is a JSON measured-state interface only; it is not connected to field SCADA/PMU systems.
- Original physics loss and pairwise rank-loss are implemented and measured, but they are not yet decisive contributors.
- This is a 3-seed RTS-79 full-truth preliminary result, not a final paper-scale claim.

## RL Untouched Statement

This PR does not modify `src/rl_mitigation` or `scripts/rl_mitigation`.

## Reviewer Checklist

- Confirm original `GCN_path_prob` is preserved.
- Confirm script paths in docs match real files.
- Confirm result claims are described as a 3-seed RTS-79 full-truth preliminary result.
- Confirm no `.pt`, `.npz`, full-truth detail, order detail, simulation result detail, smoke-truth detail, or large score-distribution detail is tracked.
- Confirm JSON measured-state interface claims do not imply field measurement system integration.
- Confirm `src/rl_mitigation` and `scripts/rl_mitigation` are untouched.
