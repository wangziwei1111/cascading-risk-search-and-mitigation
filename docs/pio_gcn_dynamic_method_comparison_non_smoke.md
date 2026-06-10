# Non-Smoke Dynamic Method Comparison

## Purpose

Round 23 expands the learned path-reranker diagnosis from the minimal smoke dataset to a medium non-smoke dataset, then reruns learned MLP, PIO-GCN, and LODF Top50/Top100 event-driven dynamic comparison.

This is a preliminary diagnostic comparison only. It is not a formal dynamic stability conclusion.

## Dataset And Model

| item | value |
| --- | ---: |
| dataset_source | simulator_derived_medium |
| dataset_scale | medium |
| num samples | 8000 |
| positive samples | 471 |
| positive ratio | 0.058875 |
| train / val / test seeds | 10 / 3 / 3 |
| max paths per seed | 500 |

The learned reranker uses non-label physical and ranking features only. Forbidden label columns such as `opa_is_critical`, `opa_total_load_shed_mw`, `y_critical`, and `y_load_shed` are excluded from model features.

Held-out model metrics:

| metric | value |
| --- | ---: |
| test AUC | 0.7907 |
| test average precision | 0.1340 |
| test precision@20 | 0.1500 |
| test recall@20 | 0.0370 |

## Dynamic Result

The dynamic simulation uses:

```text
results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json
```

| method | Top50 precision | Top100 precision | Top50 mean stress | Top100 mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_mlp | 0.0000 | 0.0000 | 0.1034 | 0.1040 |
| pio_gcn | 0.0000 | 0.0000 | 0.1034 | 0.1040 |
| lodf | 0.0000 | 0.0000 | 0.0856 | 0.0949 |

All Top100 methods have `dynamic_precision_at_k = 0`, so:

```text
calibration_warning = true
calibration_warning_reason = all_stable
dynamic_discrimination_signal = false
```

The learned MLP and PIO-GCN TopK sets are effectively identical in this medium prototype run, so the learned reranker does not add a dynamic-layer discrimination signal here.

## Rank-Depth Curve

At K = 10/20/50/100, learned and PIO-GCN have identical dynamic stress curves. LODF has lower mean stress at each depth in this run.

Therefore, the rank-depth curve does not show learned ranking concentrating dynamic stress earlier than PIO-GCN or LODF.

## OPA / Dynamic Alignment

The OPA label and dynamic stress alignment is weak:

| method | TopK | OPA positives | dynamic unstable | corr(stress, OPA shed) |
| --- | ---: | ---: | ---: | ---: |
| learned_mlp | 50 | 7 | 0 | -0.0675 |
| learned_mlp | 100 | 13 | 0 | -0.0829 |
| pio_gcn | 50 | 7 | 0 | -0.0675 |
| pio_gcn | 100 | 13 | 0 | -0.0829 |
| lodf | 50 | 3 | 0 | 0.0392 |
| lodf | 100 | 7 | 0 | -0.0288 |

This means current simplified dynamic stress is not aligned with OPA load-shedding labels strongly enough to support a method superiority claim.

## Gate Decision

The updated interpretability gate outputs:

```text
allowed_next_step = tune_post_fault_event_strength
dynamic_discrimination_signal = false
```

Because the non-smoke comparison is still all stable, the next step should tune post-fault event strength before expanding claims or figures.

## Round 24 Update

Round 24 fixes the TopK coverage shortfall. The original shortage was caused by duplicate ordered N-2 paths in the input ranking; after unique-path fill, all learned / PIO-GCN / LODF Top50 and Top100 groups have coverage ratio 1.0.

Round 24 also calibrates event-strength thresholds using `recommended_event_strength_options.json`. The calibrated dynamic layer is no longer all-stable or all-unstable:

| method | Top50 precision | Top100 precision |
| --- | ---: | ---: |
| learned_mlp | 0.3000 | 0.2700 |
| pio_gcn | 0.3400 | 0.3600 |
| lodf | 0.2800 | 0.3000 |

This removes the all-stable `calibration_warning`, but it does not create a learned advantage. The updated gate recommends `report_no_dynamic_advantage_preliminary`.

## Limits

No dynamic recall is reported because no full dynamic truth exists.

This remains:

- simplified swing-equation prototype;
- not EMT;
- not full OPF;
- no renewable dynamic validation;
- no exciter, governor, or PSS;
- not an engineering-grade dynamic stability conclusion.
