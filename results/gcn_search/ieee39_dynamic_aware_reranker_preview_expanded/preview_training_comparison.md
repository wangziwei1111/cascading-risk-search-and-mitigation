# IEEE39 Expanded Preview Training Comparison

This comparison is preview-only. It is not a final dynamic performance conclusion.

| item | historical preview | expanded preview |
| --- | ---: | ---: |
| num_samples | 10 | 35 |
| preview_only | True | True |

## Regression Metrics

```json
{
  "historical": {
    "mae": 0.025775603456558487,
    "rmse": 0.034688070217683144,
    "pearson": 0.9852496527991237,
    "spearman": 0.8997002046464956
  },
  "expanded": {
    "mae": 0.022533466364098566,
    "rmse": 0.03082235601126514,
    "pearson": 0.9686676624285414,
    "spearman": 0.5763708957337677
  }
}
```

## Classification Metrics

```json
{
  "historical": {
    "accuracy": 1.0,
    "f1": 1.0,
    "roc_auc": 1.0
  },
  "expanded": {
    "accuracy": 1.0,
    "f1": 1.0,
    "roc_auc": 1.0
  }
}
```

## Interpretation

- The expanded run uses more samples than the historical 10-sample preview and is therefore a more complete workflow sanity check.
- The result is still a compact phasor_RMS preview, not EMT and not a final dynamic performance conclusion.
- dynamic_stress_score is still a synthetic proxy target derived from compact dynamic measurements.
- Because the feature set also contains compact dynamic measurement quantities, the reported metrics can be optimistic and should not be treated as independent generalization evidence.
- A stricter next step should use an independent test set, more fault types, and target-feature leakage checks.

## Caveats

- preview_only comparison
- phasor_RMS, not EMT
- generator_speed_proxy is not direct frequency
- handwired breaker is pilot breaker-like validation, not engineering-grade protection
- L12 remains excluded because it is a simulation_timeout / suspected islanding special case
