# PIO-GCN Loss Diagnostics Recommendations

This diagnostic is based on existing metrics only. It does not rerun training or full-truth simulations.

## Current Answers

- Over-prediction: check `overprediction_summary.csv`. If positive prediction rate at 0.5 is high while precision remains limited, the model is likely over-predicting high-risk branches.
- Original physics loss: current ablation indicates it changes probability calibration more than Top-K ordering. It is not yet a decisive ranking contributor.
- Pairwise rank-loss: current diagnostics show whether positive-negative score gap increases, but the existing 3-seed result does not show Top-20/Top-50 improvement.
- Hard negative mining: recommended as a next step because many noncritical high-score candidates can dominate the front of the ranking.
- Path-level loss: recommended for future work because the online task ranks ordered paths, while current losses are mostly branch/state level.

## Input Summaries

- Ablation summary: `results/gcn_search/pio_formal_ablation_3seed/ablation_method_comparison.csv`
- Pairwise rank-loss summary: `results/gcn_search/pio_rank_loss_preliminary_3seed/aggregate_method_comparison.csv`

## Recommendation

Treat original physics loss and pairwise rank-loss as implemented diagnostics, not as proven improvements. The next useful experiments are hard negative mining and path-level ranking loss.
