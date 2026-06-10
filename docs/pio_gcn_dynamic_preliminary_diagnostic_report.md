# PIO-GCN Dynamic Preliminary Diagnostic Report

## 1. Scope And Limitations

This report summarizes the current RTS-79 simplified swing-equation dynamic diagnostic for learned MLP reranker, PIO-GCN, and LODF ordered N-2 path rankings.

This is a preliminary diagnostic result only. It is not EMT, not full OPF, has no renewable dynamic model, and does not include exciter, governor, or PSS models. No dynamic recall is reported because no full dynamic truth exists. It is not an engineering-grade dynamic stability conclusion.

## 2. Dataset And Learned Reranker Summary

The non-smoke medium path-reranker dataset contains 8000 samples, 471 OPA-positive samples, and a positive ratio of 0.058875. The learned reranker held-out metrics are:

| metric | value |
| --- | ---: |
| test AUC | 0.7907 |
| test average precision | 0.1340 |
| test precision@20 | 0.1500 |
| test recall@20 | 0.0370 |

## 3. Dynamic Model Sanity Ladder

Earlier sanity checks confirmed no-trip and post-fault controls are no longer globally degenerate. The model remains a simplified swing-equation prototype, so these checks only make the diagnostic layer interpretable; they do not validate an engineering-grade dynamic model.

## 4. TopK Coverage Fix

Round 24 found that Top50/Top100 case shortfall was caused by duplicate ordered N-2 paths in the input ranking. The TopK preparation now drops duplicate and invalid paths before selection and fills from deeper ranks.

| method | Top50 coverage | Top100 coverage |
| --- | ---: | ---: |
| learned_mlp | 1.0000 | 1.0000 |
| pio_gcn | 1.0000 | 1.0000 |
| lodf | 1.0000 | 1.0000 |

## 5. Event-Strength Calibration

The calibrated setting uses `frequency_unstable_threshold_hz = 49.3` with the existing post-fault options. The goal is to avoid all-stable / all-unstable degeneracy, not to tune results in favor of learned ranking.

After calibration:

```text
nondegenerate_dynamic_layer = true
calibration_warning = false
```

## 6. Dynamic Method Comparison

| method | Top50 precision | Top100 precision | Top50 mean stress | Top100 mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_mlp | 0.3000 | 0.2700 | 0.0985 | 0.0871 |
| pio_gcn | 0.3400 | 0.3600 | 0.0997 | 0.1029 |
| lodf | 0.2800 | 0.3000 | 0.0887 | 0.0900 |

PIO-GCN Top100 precision is higher than learned under the current calibrated setting.

## 7. Rank-Depth Stress Curve

The rank-depth curve does not show learned ranking concentrating dynamic stress earlier than PIO-GCN. Current Top100 mean stress is:

```text
learned_mlp = 0.0871
pio_gcn = 0.1029
lodf = 0.0900
```

## 8. OPA / Dynamic Alignment

Learned has weak positive OPA/dynamic alignment:

```text
learned Top100 corr(stress, OPA shed) = 0.1211
learned Top100 corr(dynamic_unstable, OPA critical) = 0.1461
```

This weak positive correlation is not enough to prove a dynamic advantage because learned Top100 precision remains below PIO-GCN.

## 9. Robustness / Bootstrap CI

Robustness summary:

```text
num_nondegenerate_settings = 9
learned_best_count = 0
pio_best_count = 9
lodf_best_count = 0
learned_advantage_robust = false
```

Bootstrap comparison:

```text
learned_precision_minus_pio_gcn Top100 = -0.09, 95% CI [-0.22, 0.04]
learned_precision_minus_lodf Top100 = -0.03, 95% CI [-0.15, 0.09]
learned_stress_minus_pio_gcn Top100 = -0.0158, 95% CI [-0.0474, 0.0133]
```

The bootstrap intervals do not support a robust learned dynamic advantage.

## 10. Conservative Conclusion

Current conclusion:

```text
no observed learned dynamic advantage
report_conclusion = no_dynamic_advantage_observed_preliminary
```

The current dynamic diagnostic layer is now nondegenerate and reportable as a preliminary negative finding: learned ranking does not show a robust dynamic advantage over PIO-GCN or LODF in this simplified RTS-79 diagnostic.

## 11. Next Steps

Possible next steps:

- expand to a larger or full dataset;
- improve the dynamic model with more realistic generator and control dynamics;
- add renewable, governor, exciter, and PSS models;
- use the current result as a conservative negative finding;
- build full dynamic truth only if dynamic recall is required.
