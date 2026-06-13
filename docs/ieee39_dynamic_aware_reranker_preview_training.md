# IEEE39 Dynamic-Aware Reranker Preview Training

## Purpose

This round starts a preview dynamic-aware reranker training step after the
compact IEEE39 dynamic label gate reached ten training-ready labels. The goal is
workflow validation and sanity checking only. It is not a final dynamic
performance conclusion.

## Current Gate

```text
num_training_ready_labels = 10
num_training_ready_handwired_line_trip_labels = 8
num_unique_handwired_line_ids = 8
allowed_for_dynamic_aware_training = true
ready_for_preview_training = true
```

L01-L08 now form eight handwired line-trip labels. The other two
training-ready labels are the existing three-phase fault and relay proxy cases.

## Training Entry

Run:

```powershell
python scripts/gcn_search/train_ieee39_dynamic_aware_reranker_preview.py ^
  --dynamic-label-summary results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json ^
  --training-readiness results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json ^
  --fault-summary-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08.csv ^
  --output-dir results/gcn_search/ieee39_dynamic_aware_reranker_preview ^
  --random-seed 42
```

The script first checks the gate. If `num_training_ready_labels < 10`,
`allowed_for_dynamic_aware_training != true`, or
`ready_for_preview_training != true`, it refuses to train.

## Dataset And Targets

The preview dataset keeps only rows with:

```text
training_ready_candidate = true
measurement_extraction_status = voltage_speed_angle
```

The continuous preview target is:

```text
dynamic_stress_score =
0.35 * voltage_sag
+ 0.25 * frequency_excursion_hz
+ 0.20 * max_speed_deviation * 100
+ 0.20 * max_rotor_angle_separation_deg / 180
```

This score is a transparent preview stress proxy. It is not a validated
dynamic-stability label.

The binary target is `unstable_flag`. In the current preview dataset both
classes exist, so a lightweight logistic sanity check is also run. If a future
dataset contains only one class, the script skips classification and writes a
skipped reason instead of forcing a classifier.

## Outputs

```text
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_dataset.csv
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_config.json
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_metrics.json
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_predictions.csv
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_model_coefficients.csv
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_dynamic_aware_reranker_model.json
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_readme.md
```

## Preview Result

Current preview run:

```text
num_samples = 10
cv_strategy = leave_one_out
regression_mae = 0.025776
regression_rmse = 0.034688
regression_spearman = 0.899700
classification_accuracy = 1.000000
classification_f1 = 1.000000
classification_roc_auc = 1.000000
```

These numbers are preview-only. They are likely optimistic because the
continuous target is derived from the same compact dynamic measurements that
also appear in the feature set.

## Boundaries

- The IEEE39 model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- The result is only a sanity check and workflow validation.
- It is not an online deployment result.
- It is not a final dynamic performance conclusion.
- Formal experiments need more samples, more fault types, an independent test
  set, and stricter dynamic models.
- The next sample-expansion step prepares independent per-line clean lab `.slx`
  files for L09 and L10: L09 uses `Grid/B16 to B24`, and L10 uses
  `Grid/B17 to B27`.
- The L09/L10 preparation step does not wire breakers, does not run compact
  simulation, and does not retrain the preview reranker.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries.
## Current label gate after L09/L10

The current label gate has advanced beyond the historical preview artifact:

- `num_training_ready_labels = 35`
- `num_training_ready_handwired_line_trip_labels = 33`
- `num_unique_handwired_line_ids = 33`
- `allowed_for_dynamic_aware_training = true`
- `ready_for_preview_training = true`

The historical preview training artifact still contains 10 samples because this
round intentionally does not retrain the dynamic-aware reranker. The artifact is
therefore a workflow sanity check only, not a final dynamic performance
conclusion.

`L09` and `L10` were added through independent per-line clean lab `.slx` models
and passed compact isolated simulation. `L11-L34` clean lab `.slx` files are
prepared locally for future manual wiring, but no breaker was auto-inserted and
no Simscape physical wiring was modified.
## Expanded labels after L11-L34 validation

The current label gate has expanded after validating user-wired per-line clean
lab models for `L11-L34`:

- `num_training_ready_labels = 35`
- `num_training_ready_handwired_line_trip_labels = 33`
- `num_unique_handwired_line_ids = 33`
- `allowed_for_dynamic_aware_training = true`
- `ready_for_preview_training = true`

`L12` timed out in compact isolated simulation and is not counted as
training-ready. The historical preview training artifact still contains 10
samples because this validation round did not retrain the dynamic-aware
reranker. A rerun of preview training or a stricter comparison should be done in
a separate commit after reviewing the expanded labels.
