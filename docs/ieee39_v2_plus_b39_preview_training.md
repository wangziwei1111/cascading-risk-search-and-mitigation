# IEEE39 v2-plus-B39 Dynamic-Aware Reranker Preview Training

This round runs v2-plus-B39 dynamic-aware reranker preview training. It is not
GCN training; in short, this is not GCN training. It does not run Simulink,
does not submit `.slx`, does not modify source `.slx`, and does not change the
old formal gate. It is preview-only and
`final_performance_conclusion = false`.

## Plain-Language Meaning

The previous round fixed the B39 label table. This round asks a small question:
if B39 is added to the 40-row v2 candidate set, can a lightweight reranker learn
reasonable dynamic-stress patterns? The answer is only a sanity check because
B39 is one bus-fault sample, not a complete bus-fault dataset.

## Dataset

- previous_v2_candidate_count: `40`
- v2-plus-B39 candidate count: `41`
- B39 candidate count: `1`
- old formal gate: `35 / 33 / 33`
- L12 excluded: `true`
- NF06 provenance warning preserved: `true`
- B39 status: candidate label, not formal label

## Training Setup

- regression model: Ridge Regression
- classification model: Logistic Regression
- regression target: `dynamic_stress_score`
- classification target: `unstable_flag`
- random_seed: `42`
- preview_only: `true`
- final_performance_conclusion: `false`

`dynamic_stress_score` is a proxy target synthesized from compact dynamic
measurements. When compact dynamic measurements are also used as input
features, there is target-feature leakage risk. For that reason this round also
reports `no_dynamic_measurement_features`.

## Required Modes

| mode | samples | RMSE / abs error | classification note |
| --- | ---: | ---: | --- |
| include_all_41_candidates | 41 | 0.043432 | F1 = 1.0 |
| exclude_provenance_required | 40 | 0.044357 | F1 = 1.0 |
| no_dynamic_measurement_features | 41 | 0.061018 | F1 = 1.0 |
| label_family_holdout | 41 | 0.179264 | classification skipped: one test class |
| bus_fault_holdout | 41 | B39 abs error = 0.211603 | B39 probability = 0.966723 |

## Interpretation

The include-all metrics are good, but they should not be treated as final
performance because compact dynamic measurements help define the proxy target.
The no-dynamic-measurement result is worse, which confirms leakage risk. The
label-family holdout and B39 bus-fault holdout are much harder; B39 has only one
bus-fault sample, so the result cannot represent all bus faults.

## Artifacts

- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/include_all_41_candidates/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/exclude_provenance_required/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/no_dynamic_measurement_features/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/label_family_holdout/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/bus_fault_holdout/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/v2_plus_b39_preview_comparison.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/v2_plus_b39_preview_comparison.md`

## Boundaries

The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency; specifically, `generator_speed_proxy` is not direct frequency. The
temporary bus-fault injection is not engineering-grade protection. This is not
engineering-grade protection and not a final performance conclusion.

## Recommended Next Step

Use the B39 holdout and no-leakage comparison to decide whether to collect more
bus-fault labels first, or whether to connect dynamic labels back to the main
GCN/reranker workflow.

## Interpretation Follow-Up

A follow-up interpretation concludes that the next priority is to collect more
independent bus-fault evidence before returning dynamic labels to the main
GCN/reranker workflow. B26 is the next manual GUI target. This follow-up does
not run Simulink, does not train GCN, does not retrain the reranker, and does
not export labels.
