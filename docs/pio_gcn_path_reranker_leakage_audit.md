# Path Reranker Leakage Audit and Strict Held-Out Validation

## Purpose

The learned path reranker result is very strong, so this round audits whether the high recall is caused by data leakage.

## Leakage Audit

Output:

```text
results/gcn_search/path_reranker_leakage_audit/
```

Audit findings:

| Check | Result |
|---|---|
| Train/val/test seed overlap | Clean |
| Forbidden input features | Not found |
| Near-perfect feature-label correlation | Not found |
| Suspicious high performance warning | Triggered |

Forbidden fields such as `is_critical`, `y_critical`, `y_load_shed`, and `total_load_shed_mw` are present only as labels/evaluation fields, not as model input features.

## Strict Held-Out Validation

Output:

```text
results/gcn_search/path_reranker_strict_heldout_eval/
```

Protocol:

```text
for each fold:
  test_seed = one held-out seed
  val_seed = one different seed
  train_seeds = the remaining three seeds
```

Strict held-out result:

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| rerank_physical_stress | 0.280 | 0.439 | 0.532 | 0.587 |
| learned_logistic_reranker_strict | 0.329 | 0.566 | 0.782 | 0.958 |
| learned_mlp_reranker_strict | 0.341 | 0.694 | 0.940 | 0.993 |

The strict held-out MLP still exceeds `Recall@100 > 0.60` and `Recall@200 > 0.65`, and remains above `rerank_physical_stress`.

## Feature Ablation

| Feature group | Recall@100 | Recall@200 |
|---|---:|---:|
| score_only | 0.706 | 0.929 |
| score_plus_rank | 0.730 | 0.920 |
| physical_only | 0.627 | 0.833 |
| score_plus_physical | 0.922 | 0.993 |
| all_safe_features | 0.937 | 0.996 |

Interpretation: the high recall is not caused by one obvious forbidden feature. The main gain comes from combining score features with physical stress features. Score-only is already strong, so the result may still exploit repeated RTS-79 topology/path patterns across seeds. This is not direct label leakage, but it is a generalization caveat.

## Reporting Guidance

The current result can be reported to an advisor as a strong RTS-79 preliminary finding after leakage audit and strict held-out validation. It should not be described as final evidence or production-ready performance. More operating-condition seeds and renewable per-path evaluation are still needed.
