# PIO-GCN PathRank Learned Reranker External Validation

## Purpose

This validation checks whether the learned path reranker still works on RTS-79 operating-condition seeds that were not used in its five-seed training dataset.

## Setup

- Training seeds: 20260722-20260726.
- External full-truth test seeds: 20260727-20260729.
- System: IEEE RTS-79 only.
- Search target: ordered N-2 cascading-failure paths.
- Full truth: yes, all legal ordered N-2 paths are physically simulated for each external seed.

Output:

```text
results/gcn_search/path_reranker_extended_strict_eval/
```

## Key Result

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.209 | 0.342 | 0.437 | 0.551 |
| paper_GCN_path_prob_strong | 0.197 | 0.256 | 0.345 | 0.586 |
| LODF_yP | 0.318 | 0.569 | 0.666 | 0.886 |
| rerank_physical_stress | 0.313 | 0.503 | 0.628 | 0.706 |
| learned_logistic_reranker_external | 0.330 | 0.611 | 0.788 | 0.970 |
| learned_mlp_reranker_external | 0.354 | 0.718 | 0.922 | 0.994 |

## Interpretation

The learned MLP reranker remains strong on three unseen RTS-79 seeds. This reduces the concern that the model only memorized the original five operating-condition seeds.

The main remaining limitation is that all seeds still share the same RTS-79 topology. Therefore this is external-seed validation, not proof of broad grid-to-grid generalization.

## Diagnostics

```text
results/gcn_search/path_reranker_extended_strict_eval/diagnostics/external_seed_missed_critical.csv
results/gcn_search/path_reranker_extended_strict_eval/diagnostics/external_seed_rescued_critical.csv
results/gcn_search/path_reranker_extended_strict_eval/diagnostics/external_seed_rank_shift_summary.csv
```

The diagnostics are intended to show whether critical paths are ranked after Top-200 or recovered by the learned reranker compared with PIO-GCN PathRank.
