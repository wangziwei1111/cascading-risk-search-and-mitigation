# PIO-GCN Learned Path Reranker

## Purpose

The original PIO-GCN PathRank and the rule-based rerank are still limited because they use hand-designed score combinations. The learned path reranker turns each ordered N-2 path into one supervised sample and learns which path-level patterns are associated with load shedding.

## Dataset

Output:

```text
results/gcn_search/path_reranker_dataset/
```

The compact dataset contains 7030 ordered N-2 path samples from 5 RTS-79 full-truth seeds. Positive critical paths: 283. Positive ratio: 0.0403.

Features include:

- PIO-GCN path score and rank;
- paper-GCN path score and rank;
- LODF score and rank;
- ensemble alpha=0.75 score;
- line loading ratios and absolute flows;
- first-outage stress features;
- relay and security margins.

## Training

Output:

```text
results/gcn_search/path_reranker_models/
```

Two lightweight PyTorch models are trained:

- `learned_logistic_reranker`
- `learned_mlp_reranker`

The training uses leave-one-seed-out evaluation. Each seed is predicted by a model trained on the other four seeds, which avoids direct train/test seed leakage.

## Result

5-seed RTS-79 full-truth preliminary result:

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.211 | 0.338 | 0.423 | 0.521 |
| rerank_physical_stress | 0.280 | 0.439 | 0.532 | 0.587 |
| learned_logistic_reranker | 0.322 | 0.566 | 0.792 | 0.954 |
| learned_mlp_reranker | 0.333 | 0.698 | 0.944 | 0.997 |

The learned MLP reranker exceeds the requested targets:

```text
Recall@100 > 0.60
Recall@200 > 0.65
```

## Important Caveat

This result is very strong, but it is still RTS-79 preliminary. The dataset has only 5 operating-condition seeds, so the result should be reported as evidence that path-level supervision is promising, not as a final paper-scale conclusion.

## Synthetic Renewable Status

Synthetic renewable learned-reranker evaluation is now completed by regenerating compact per-path features from renewable-updated RTS-79 cases. Full-truth detail files remain local and are not tracked.

Output:

```text
results/gcn_search/path_reranker_renewable_eval/
```

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.237 | 0.347 | 0.426 | 0.495 |
| LODF_yP | 0.262 | 0.586 | 0.721 | 0.791 |
| learned_logistic_reranker_renewable | 0.287 | 0.564 | 0.811 | 0.922 |
| learned_mlp_reranker_renewable | 0.345 | 0.622 | 0.808 | 0.947 |

This is still only a synthetic renewable perturbation on RTS-79. It is not a real renewable dynamic model and not a field-data deployment result.

## Leakage Audit Update

A leakage audit and stricter held-out seed validation were added. No forbidden input feature was found, and strict held-out MLP performance remains high:

```text
Recall@20 = 0.341
Recall@50 = 0.694
Recall@100 = 0.940
Recall@200 = 0.993
```

The high score is therefore not explained by direct label leakage, but the result remains preliminary because RTS-79 topology/path labels repeat across operating-condition seeds.

## External Unseen-Seed Validation

The learned reranker was also evaluated on three unseen RTS-79 full-truth seeds, 20260727-20260729, after training on seeds 20260722-20260726.

Output:

```text
results/gcn_search/path_reranker_extended_strict_eval/
```

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.209 | 0.342 | 0.437 | 0.551 |
| LODF_yP | 0.318 | 0.569 | 0.666 | 0.886 |
| learned_logistic_reranker_external | 0.330 | 0.611 | 0.788 | 0.970 |
| learned_mlp_reranker_external | 0.354 | 0.718 | 0.922 | 0.994 |

This supports the claim that the path-level supervised reranker is not merely reproducing the original five reported seeds. However, it is still the same RTS-79 topology, so topology/path-pattern memorization remains a medium residual risk.
