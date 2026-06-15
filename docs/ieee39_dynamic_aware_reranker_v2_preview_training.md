# IEEE39 Dynamic-Aware Reranker v2 Preview Training

## Purpose

This round runs a lightweight preview training step on the IEEE39 dynamic label
schema v2 candidate set. It does not run Simulink, does not modify `.slx`, does
not fix L12, does not overwrite the old formal gate, and is not a final dynamic
performance conclusion.

Two versions are compared:

- `include_all_candidates`: uses all `40` v2 candidate rows and includes `NF06`.
- `exclude_provenance_required`: excludes `NF06`, which is marked
  `provenance_check_required = true`, and uses `39` rows.

The old formal gate remains `35 / 33 / 33`.

## Outputs

- include-all run:
  `results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/include_all_candidates/`
- exclude-provenance run:
  `results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/exclude_provenance_required/`
- comparison:
  `results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/v2_preview_comparison.md`

Each run writes:

- `preview_training_dataset.csv`
- `preview_training_config.json`
- `preview_training_metrics.json`
- `preview_training_predictions.csv`
- `preview_model_coefficients.csv`
- `preview_dynamic_aware_reranker_model.json`
- `preview_training_readme.md`

## Key Metrics

| mode | samples | contains NF06 | LOO RMSE | label-family-holdout RMSE |
| --- | ---: | ---: | ---: | ---: |
| include_all_candidates | 40 | true | 0.028367 | 0.142731 |
| exclude_provenance_required | 39 | false | 0.028697 | 0.142087 |

The include/exclude leave-one-out gap is small:

```text
rmse_exclude_minus_include = 0.000330
```

The label-family holdout error is much larger than leave-one-out error. This is
the more important warning: training on existing formal line-trip rows and
testing on non-line-trip rows is a harder generalization smoke check.

Classification for label-family holdout is skipped because the non-line-trip
test fold contains only one `unstable_flag` class. Regression still runs.

## Duplicate / Provenance Warning

`NF01`, `NF04`, and `NF06` share the same duplicate measurement group.

- `NF01` and `NF04` are both existing three-phase fault block `0.10 s` cases.
- `NF06` is a relay proxy case, but its current measurements match the same
  group.
- `NF06` is excluded in the sensitivity check.

Duplicate smoke candidates are not necessarily independent physical samples.

## Boundaries

- This is preview-only.
- It is not a final dynamic performance conclusion.
- `final_performance_conclusion = false`.
- It does not run Simulink.
- It does not modify `.slx`.
- It does not fix L12.
- It does not overwrite the old formal gate.
- The model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The relay proxy is not engineering-grade protection.
- More genuinely independent non-line-trip fault types are still needed,
  especially different-bus three-phase faults, load step, and generator trip.

## Bus-Fault Smoke Feasibility Follow-Up

A follow-up now audits different-bus three-phase fault smoke candidates: `BF01/B16`, `BF02/B39`, `BF03/B21`, and `BF04/B26`. This is meant to address the need for more independent non-line-trip fault types.

The current bus-fault audit found no safe target-bus selector, so no bus-fault Simulink smoke execution was forced. The old formal gate remains `35 / 33 / 33` and the v2 candidate count remains `40`. This follow-up does not retrain the reranker, does not train GCN, does not export labels, and does not modify source `.slx`.

## Temporary Lab Bus-Fault Injection Follow-Up

The next follow-up prepares temporary lab copies for bus-specific three-phase
fault injection checks. It prioritizes `B39` and then checks fallback `B26`.
This is still not the full pipeline.

The temporary lab workflow found candidate target-bus blocks for both buses,
but it did not verify a safe automatic physical terminal wiring rule:

- `B39`: `injection_point_found = false`, `safe_to_run_smoke = false`.
- `B26`: `injection_point_found = false`, `safe_to_run_smoke = false`.

The B39 smoke runner was invoked only as a conservative dry run and refused
execution because `safe_to_run_smoke = false`. The source `.slx` remains
unmodified and uncommitted, temporary `.slx` copies remain local-only and
ignored, L12 remains excluded, the old formal gate remains `35 / 33 / 33`, and
the v2 candidate count remains `40`.

## GUI Manual Checklist Follow-Up

The current follow-up adds only a GUI manual checklist and review templates for
B39/B26 bus-fault injection. It does not run Simulink, does not modify `.slx`,
does not commit temporary `.slx`, does not fix L12, does not train GCN, does not
retrain the dynamic-aware reranker, and does not export labels.

B39 now has a human-verified temporary injection point, but it is not smoke
success. B26 remains unverified. The current consolidation recommendation is
`manual_review_supports_next_round_inventory_update`, so the next round may
prepare temporary B39 smoke. The old formal gate remains `35 / 33 / 33`, and
the v2 candidate count remains `40`.

## B39 Candidate Export Follow-Up

After the B39 temporary smoke and quality-review rounds, one B39 bus-fault
candidate label was exported to a separate v2-plus-B39 candidate set. The
existing v2 preview training results above are not overwritten or updated by
this export.

- original v2 preview candidate count: `40`
- v2-plus-B39 candidate count: `41`
- B39 status: candidate label only, not formal label
- old formal gate remains `35 / 33 / 33`
- L12 remains excluded
- NF06 duplicate/provenance warning is preserved
- GCN trained: `false`
- reranker retrained: `false`
- v2 preview training changed: `false`
- should_train_now: `false`

The recommended next step is a no-training composition/comparison review before
any future v2-plus-B39 preview training.
