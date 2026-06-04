# PIO-GCN Top-K Depth Tradeoff

## Purpose

This note explains why PIO-GCN PathRank is stronger at Top-20/50/100 while a stronger paper-feature `GCN_path_prob` baseline can surpass it at Top-200.

## Result Source

```text
results/gcn_search/pio_topk_depth_tradeoff/
```

The analysis reuses the 5-seed RTS-79 full-truth preliminary result and compares PIO-GCN PathRank with stronger paper-feature baselines, LODF_yP, random, line order, and oracle.

## Key Results

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.211 | 0.338 | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.176 | 0.254 | 0.350 | 0.568 |
| paper_GCN_path_prob_strong_v2 | 0.176 | 0.244 | 0.330 | 0.565 |
| LODF_yP | 0.036 | 0.134 | 0.207 | 0.329 |

## Interpretation

PIO-GCN PathRank concentrates many critical paths near the front of the ranked list, so it is better for small Top-K rapid screening. The stronger paper-feature baseline finds fewer critical paths in the first 100 candidates, but it spreads useful critical paths deeper into the ranked list and overtakes at Top-200.

The honest conclusion is therefore not “PIO-GCN wins at all depths.” The safer conclusion is:

```text
PIO-GCN PathRank is currently best suited for rapid small-Top-K screening on RTS-79.
For deeper Top-K search, stronger paper-feature GCN and possible ensemble ranking need further study.
```

## Ensemble Status

A score-level ensemble is feasible, but it was not implemented in this round because the review-safe tracked artifacts intentionally exclude per-path score distribution and order detail files. To make ensemble evaluation reproducible without committing large details, the next stage should either regenerate scores inside an ensemble script or save compact top-N per-path score summaries only.
