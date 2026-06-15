# IEEE39 Non-Line-Trip Label Candidate Export

## Purpose

This round exports the five successful non-line-trip smoke-test rows as a
separate candidate label set and builds a v2 combined candidate schema. It does
not run Simulink, does not modify `.slx`, does not fix L12, and does not retrain
the dynamic-aware reranker.

## Inputs

- smoke summary:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_summary.csv`
- smoke report:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_report.json`
- existing formal fault summary:
  `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10_l11_to_l34.csv`
- existing formal quality/readiness summaries:
  `results/gcn_search/ieee39_dynamic_labels/`

The original formal line-trip gate is preserved at `35 / 33 / 33`.

## Outputs

- non-line-trip candidates:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_non_line_trip_dynamic_label_candidates.csv`
- combined v2 candidate schema:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_label_schema_v2_combined_candidates.csv`
- v2 quality summary:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_label_quality_summary_v2_with_non_line_trip_candidates.json`
- v2 readiness preview:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_aware_training_readiness_v2_with_non_line_trip_candidates.json`
- duplicate / provenance report:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_non_line_trip_duplicate_provenance_report.md`

## Counts

- original formal training-ready labels: `35`
- original handwired line-trip labels: `33`
- non-line-trip candidate labels: `5`
- v2 combined candidate rows: `40`
- L12 excluded: `true`

The v2 combined candidate set is not the old formal gate. It is a preview
candidate schema for a future training round.

## Duplicate / Provenance Warning

`NF01`, `NF04`, and `NF06` have identical compact measurement values.

- `NF01` and `NF04` are both existing three-phase fault block `0.10 s` cases, so
  identical values are expected.
- `NF06` is `relay_proxy_fault_smoke`, but its current compact measurements
  match the same `0.10 s` fault group.
- `NF06` is retained, but it is marked `provenance_check_required = true` and
  `not_independent_physical_sample_until_verified = true`.

Rows are not deleted because of duplicates, but later training must not treat
all duplicate rows as fully independent physical samples without review.

## Boundaries

- This round did not run Simulink.
- This round did not modify `.slx`.
- This round did not modify Simscape physical wiring.
- This round did not fix L12.
- This round did not retrain the dynamic-aware reranker.
- This round did not overwrite the old formal label gate.
- Non-line-trip labels and handwired line-trip labels are counted separately.
- The model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The relay proxy is not engineering-grade protection.
- This is preview-only, not final dynamic performance conclusion.

## Next Step

Review the duplicate/provenance report first, especially `NF06`. After that,
run a separate v2 preview training round with duplicate/provenance warnings
carried into the metrics and documentation.

## v2 Preview Training Follow-Up

A separate preview-only training round has now used this v2 candidate schema in
two modes:

- `include_all_candidates`: `40` rows, including `NF06`.
- `exclude_provenance_required`: `39` rows, excluding `NF06`.

The old formal gate remains `35 / 33 / 33`; this follow-up does not overwrite
the formal gate. The key output is:

```text
results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/
```

The sensitivity gap is small for leave-one-out RMSE
(`0.028367` versus `0.028697`), but label-family holdout RMSE is much larger
(`0.142731` / `0.142087`). That holdout is the important warning because it
trains on `existing_formal_dynamic` rows and tests on `non_line_trip` rows.

This follow-up does not run Simulink, does not modify `.slx`, does not fix L12,
and remains preview-only. It is not a final dynamic performance conclusion.

## Bus-Fault Smoke Feasibility Follow-Up

A later bus-fault feasibility round audits `BF01-BF04` as different-bus three-phase fault smoke candidates. It does not modify this export directory, does not change the v2 candidate count, and does not merge bus-fault rows into formal labels.

The result is that no current bus-fault scenario is safely runnable because the existing scripts do not expose a target-bus selector. Bus-fault candidates therefore remain smoke feasibility rows only. No GCN training or reranker retraining was run.

## B39 Candidate Export Follow-Up

A later B39 temporary bus-fault smoke result passed quality review and was
exported into a separate v2-plus-B39 candidate file set. This follow-up does
not overwrite the original v2 files in this directory.

- original v2 candidate count in this directory: `40`
- v2-plus-B39 candidate count in the separate export directory: `41`
- old formal gate remains `35 / 33 / 33`
- B39 candidate is not a formal label
- L12 remains excluded
- NF06 duplicate/provenance warning is preserved
- no GCN training
- no reranker retraining
- no v2 preview training update

Separate export directory:

`results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/`
