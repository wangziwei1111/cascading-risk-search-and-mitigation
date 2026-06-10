# Dynamic Method Comparison Top100

## Purpose

Round 22 expands the event-driven dynamic diagnostic from Top20 to Top50/Top100 after the Round 21 post-fault sanity ladder passed.

This compares:

```text
learned_mlp
pio_gcn
lodf
```

The comparison is preliminary diagnostic only. It is not a formal dynamic stability conclusion.

## Setup

Inputs are generated from the local `learned_mlp_per_path_ranking.csv`:

```text
learned_mlp: reranker_score descending
pio_gcn: pio_score descending
lodf: lodf_score descending
```

`opa_is_critical` and `opa_total_load_shed_mw` are not used for sorting.

The dynamic simulation uses:

```text
results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json
```

## Result

| method | Top50 precision | Top100 precision | Top100 mean stress |
| --- | ---: | ---: | ---: |
| learned_mlp | 0.0000 | 0.0000 | 0.0881 |
| pio_gcn | 0.0000 | 0.0000 | 0.1013 |
| lodf | 0.0000 | 0.0000 | 0.1007 |

All Top100 methods have `dynamic_precision_at_k = 0`. Therefore:

```text
calibration_warning = true
dynamic_discrimination_signal = false
```

The current post-fault options remove the all-unstable degeneracy, but now the Top100 comparison is all stable. This means the dynamic layer is still not discriminative enough for a method superiority claim.

## Rank-Depth Curve

The rank-depth stress curve shows small stress differences, but learned does not consistently concentrate higher dynamic stress earlier than PIO-GCN or LODF.

At Top100:

```text
learned_mlp mean stress = 0.0881
pio_gcn mean stress = 0.1013
lodf mean stress = 0.1007
```

Thus there is no preliminary dynamic discrimination signal in favor of learned ranking.

## Interpretation

Round 22 allows the next step to expand to a non-smoke dataset for diagnosis, but it does not prove dynamic superiority.

Round 23 performs this non-smoke expansion. The medium dataset has 8000 samples and 471 positives, but the learned / PIO-GCN / LODF Top100 dynamic precision values are still all 0. The non-smoke result therefore remains a `calibration_warning`, with `dynamic_discrimination_signal = false`.

Round 24 fixes duplicate-path TopK coverage and calibrates event-strength thresholds. The calibrated non-smoke dynamic layer is nondegenerate: learned Top100 precision is 0.27, PIO-GCN Top100 precision is 0.36, and LODF Top100 precision is 0.30. This is still a preliminary diagnostic result, and it does not show learned dynamic superiority.

No dynamic recall is reported because no full dynamic truth exists.

This remains:

- simplified swing-equation prototype;
- not EMT;
- not full OPF;
- no renewable dynamic validation;
- no exciter, governor, or PSS;
- not an engineering-grade dynamic stability conclusion.
