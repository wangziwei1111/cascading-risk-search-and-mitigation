# PIO-GCN Ensemble Feasibility Note

Score-level ensemble ranking is a reasonable next step because PIO-GCN PathRank is stronger in the shallow Top-K region, while the stronger paper-feature baseline is more competitive at Top-200.

The simplest ensemble would combine normalized scores:

```text
ensemble_score = w1 * PIO_GCN_score + w2 * paper_GCN_score + w3 * LODF_yP_score
```

This round did not implement the ensemble because the current PR artifact policy intentionally does not track per-path score distributions, order details, full-truth details, or simulation-result details. Those local files can be large and are not suitable for review tracking.

Recommended next-stage implementation:

1. Add a small ensemble evaluator that regenerates PIO-GCN, paper-GCN, and LODF_yP path scores from the saved models and full-truth seed config.
2. Save only compact top-N ensemble summaries, not all per-path score distributions.
3. Compare ensemble recall at Top-20/50/100/200 against PIO-GCN PathRank and strong paper-feature baseline.

Current conclusion: ensemble is feasible and well motivated, but not yet evaluated.
