# IEEE39 v2 Dynamic-Aware Preview Comparison

This comparison is preview-only and final_performance_conclusion=false.

```text
v1_expanded_num_samples: `35`
v2_include_all_num_samples: `40`
v2_exclude_provenance_num_samples: `39`
provenance_excluded_count: `1`
```

| item | value |
| --- | ---: |
| v1 expanded samples | 35 |
| v2 include_all samples | 40 |
| v2 exclude_provenance samples | 39 |
| non-line-trip candidates | 5 |
| provenance excluded count | 1 |

## Sensitivity Gap

```json
{
  "leave_one_out_rmse_include_all": 0.028367154633199117,
  "leave_one_out_rmse_exclude_provenance": 0.02869708538223394,
  "rmse_exclude_minus_include": 0.00032993074903482286,
  "label_family_holdout_rmse_include_all": 0.1427311567269787,
  "label_family_holdout_rmse_exclude_provenance": 0.1420873898567332
}
```

## Label-Family Holdout Metrics

```json
{
  "include_all_candidates": {
    "regression": {
      "mae": 0.14265646129941315,
      "rmse": 0.1427311567269787,
      "pearson": 0.9998743620184952,
      "spearman": 0.8944271909999159
    },
    "classification": {},
    "classification_skipped_reason": "Test predictions contain only one unstable_flag class.",
    "num_predictions": 5,
    "num_folds": 1,
    "folds": [
      {
        "fold_id": "holdout_non_line_trip",
        "num_train": 35,
        "num_test": 5
      }
    ]
  },
  "exclude_provenance_required": {
    "regression": {
      "mae": 0.14200115165805172,
      "rmse": 0.1420873898567332,
      "pearson": 0.9998657371686579,
      "spearman": 0.9486832980505139
    },
    "classification": {},
    "classification_skipped_reason": "Test predictions contain only one unstable_flag class.",
    "num_predictions": 4,
    "num_folds": 1,
    "folds": [
      {
        "fold_id": "holdout_non_line_trip",
        "num_train": 35,
        "num_test": 4
      }
    ]
  }
}
```

## Interpretation

- The v2 preview is a candidate schema sanity check only.
- include_all_candidates may be affected by NF06 duplicate/provenance risk.
- exclude_provenance_required is a sensitivity check that removes NF06.
- label_family_holdout is the closest current smoke check to training on line-trip labels and testing on non-line-trip labels.
- This is not a final dynamic performance conclusion.
- More independent non-line-trip fault types are needed, especially different-bus faults, load step, and generator trip.
- phasor_RMS, not EMT.
- generator_speed_proxy is not direct frequency.
- relay proxy is not engineering-grade protection.

## Caveats

- duplicate smoke candidates are not necessarily independent physical samples
- dynamic_stress_score is a compact proxy target
- measurement-derived features may be optimistic
- small sample preview only
