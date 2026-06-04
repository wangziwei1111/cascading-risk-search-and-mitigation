# PR Description: PIO-GCN RTS-79 Preliminary Search Framework

## Summary

This PR adds and consolidates the RTS-79 PIO-GCN cascading-failure path-search work. It preserves the original `GCN_path_prob` method and adds physics-enhanced features, raw-feature physics losses, candidate masking, measured-state JSON input, formal preliminary experiments, ablations, rank-loss diagnostics, and review-ready documentation.

## Motivation

The original RTS-79 GCN search was too weak to clearly explain where performance gains came from. This PR turns the work into a reviewable preliminary milestone: the simulator, dataset generation, training, online Top-K search, ablation, and reporting artifacts are now organized around the same 3-seed full-truth RTS-79 evaluation.

## Main Changes

- Added physics-feature Step2-state dataset support.
- Added physics-informed GCN training with raw physical features for loss computation.
- Added candidate probability masking for invalid active outage candidates.
- Added JSON measured-state update support for Top-K evaluation.
- Added full-truth 3-seed preliminary experiment scripts and results.
- Added formal ablation separating physics features, mask, physics loss, paper GCN, LODF_yP, random, line order, and oracle.
- Added reachable pairwise rank-loss implementation and preliminary comparison.
- Cleaned large tracked result files and replaced the largest score distribution detail with a compact summary.
- Added stage summary, advisor brief, reproduction commands, and artifact self-check script.

## Validation

Required pytest suite:

```text
python -m pytest tests/test_cascade_from_case_consistency.py tests/test_measured_state_sanity.py tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_gcn_ranking_loss.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py
```

Artifact self-check:

```text
python scripts/gcn_search/check_pio_gcn_artifacts.py
```

## Key Preliminary Results

3 RTS-79 full-truth seeds:

| Method | Top-100 recall |
|---|---:|
| PIO-GCN physics feature | about 42% |
| LODF_yP | about 21% |
| weak paper GCN_path_prob | about 14% |
| oracle | 100% |

Main conclusion: physics-enhanced features are the main contributor. Candidate mask, original physics loss, and rank-loss are not yet major contributors in this small preliminary test.

## Limitations

- RTS-79 only; no Henan-grid reproduction.
- 3-seed preliminary only; not a final statistical claim.
- JSON measured-state input only; no real SCADA/PMU integration.
- Rank-loss does not improve Top-20/Top-50 and only slightly changes Top-100.
- Paper GCN baseline is weak under the current small training setup.

## Files Added

- `docs/pio_gcn_stage_summary.md`
- `docs/pio_gcn_advisor_brief.md`
- `docs/pio_gcn_pr_description.md`
- `docs/pio_gcn_reproduction_commands.md`
- `scripts/gcn_search/check_pio_gcn_artifacts.py`
- `results/gcn_search/tracked_large_files_removed_round8.txt`

## Files Modified

- `.gitignore`
- `README.md`
- `docs/gcn_current_progress.md`
- `docs/gcn_pio_validation_log.md`
- `docs/pio_gcn_formal_small_experiment.md`
- `docs/pio_gcn_method.md`
- GCN result tracking under `results/gcn_search/`

## RL Untouched Statement

This PR does not modify `src/rl_mitigation` or `scripts/rl_mitigation`.

## Reviewer Checklist

- Confirm original `GCN_path_prob` is preserved.
- Confirm no `.pt`, `.npz`, full-truth detail, order detail, simulation result detail, or large score-distribution detail is tracked.
- Confirm RTS-79 result claims are described as 3-seed preliminary.
- Confirm measured-state claims refer only to JSON input, not real SCADA/PMU deployment.
- Confirm RL mitigation files are untouched.
