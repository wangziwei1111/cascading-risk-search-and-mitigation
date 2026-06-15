# IEEE39 v2-plus-B39 Dynamic-Aware Reranker Preview Training

This is preview-only and `final_performance_conclusion = false`. It is dynamic-aware reranker preview training, not GCN training. It does not run Simulink and does not submit `.slx`.

## Counts

- previous_v2_candidate_count: `40`
- v2_plus_b39_candidate_count: `41`
- b39_candidate_count: `1`
- old_formal_gate: `35 / 33 / 33`
- L12 excluded: `true`
- NF06 provenance warning preserved: `true`

## Metrics Summary

| mode | samples | regression RMSE | classification F1 | note |
| --- | ---: | ---: | ---: | --- |
| include_all_41_candidates | 41 | 0.043432 | 1.0 | compact dynamic measurements included |
| exclude_provenance_required | 40 | 0.044357 | 1.0 | NF06 removed |
| no_dynamic_measurement_features | 41 | 0.061018 | 1.0 | leakage reduced |
| label_family_holdout | 41 | 0.179264 | None | train formal, test non-line-trip |
| bus_fault_holdout | 41 | 0.211603 | 0.9667234869320884 | B39-only test |

## Interpretation

- `dynamic_stress_score` is a proxy target synthesized from compact dynamic measurements.
- Strong include-all metrics can reflect target-feature leakage because compact dynamic measurements are also input features.
- The no_dynamic_measurement_features mode is the no-leakage sanity check.
- B39 is only one bus-fault sample, so the B39 holdout result cannot represent all bus faults.
- NF06 provenance warning remains.
- Label-family holdout remains important.

## Boundaries

The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency. The temporary bus-fault injection is not engineering-grade protection.
