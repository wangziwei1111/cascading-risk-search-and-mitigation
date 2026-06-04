# PIO-GCN Ensemble and Rerank Preliminary

## Purpose

This note records the performance-improvement check after the Top-K depth tradeoff result. The question is whether PIO-GCN PathRank can keep its Top-20/50/100 strength while reducing the Top-200 gap against the stronger paper-feature baseline.

## Scope

All results are RTS-79 5-seed full-truth preliminary results. They are not final paper-scale claims.

```text
seeds = 20260722, 20260723, 20260724, 20260725, 20260726
top_k = 20, 50, 100, 200
full_truth = true
```

## Score-Level Ensemble

The ensemble score is:

```text
ensemble_score = alpha * normalized_pio_score + (1 - alpha) * normalized_paper_score
```

The path scores are regenerated from the saved local PIO-GCN and paper-GCN models. No fake per-path score is used.

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.211 | 0.338 | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.176 | 0.254 | 0.350 | 0.568 |
| ensemble_alpha_0.25 | 0.172 | 0.285 | 0.392 | 0.574 |
| ensemble_alpha_0.50 | 0.187 | 0.319 | 0.426 | 0.567 |
| ensemble_alpha_0.75 | 0.200 | 0.345 | 0.444 | 0.549 |

Interpretation: ensemble helps Top-100 when PIO has a large weight, but it does not clearly solve the Top-200 problem. The alpha=0.25 case slightly improves Top-200, but sacrifices Top-20/50/100.

## Hard-Negative-Aware Rerank

The rerank stage reorders the top 300 PIO-GCN candidate paths with a compact physics-aware score:

```text
rerank_score = w1 * normalized_pio_score
             + w2 * normalized_lodf_score
             + w3 * normalized_loading_stress
             + w4 * normalized_relay_risk
```

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.211 | 0.338 | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.176 | 0.254 | 0.350 | 0.568 |
| rerank_pio_dominant | 0.258 | 0.380 | 0.469 | 0.556 |
| rerank_balanced | 0.289 | 0.410 | 0.521 | 0.576 |
| rerank_physical_stress | 0.280 | 0.439 | 0.532 | 0.587 |

Interpretation: hard-negative-aware rerank is the most useful performance-improvement result in this round. It improves Top-20/50/100 over PIO-GCN and improves Top-200 beyond the stronger paper-feature baseline in this 5-seed preliminary check.

## Current Conclusion

- PIO-GCN PathRank remains useful for small Top-K rapid screening.
- Score-level ensemble is feasible, but the simple alpha sweep is not yet a robust solution.
- Hard-negative-aware rerank gives the clearest improvement in this round.
- The result is still RTS-79 preliminary and needs more seeds before being used as a final claim.
