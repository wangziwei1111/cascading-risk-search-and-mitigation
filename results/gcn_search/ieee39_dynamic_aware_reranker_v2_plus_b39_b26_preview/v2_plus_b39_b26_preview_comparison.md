# IEEE39 v2-plus-B39+B26 Preview/No-Leakage Comparison

This round is preview-only. It does not run Simulink, does not export labels,
does not train GCN, does not run a GCN usefulness audit, and does not retrain
the formal reranker.

## Plain-Language Meaning

B39 and B26 are now both temporary bus-fault candidate labels. This comparison
uses only small preview models to check whether the compact dynamic measurement
features create target-feature leakage risk and whether B39/B26 holdout
generalization is still weak.

## Boundary Flags

- preview_only: `true`
- final_performance_conclusion: `false`
- simulink_run: `false`
- labels_exported: `false`
- gcn_trained: `false`
- gcn_usefulness_audit_run: `false`
- formal_reranker_retrained: `false`
- old formal gate: `35 / 33 / 33`
- candidate count: `42`
- bus-fault candidates: `2`

## Metrics Summary

| mode | RMSE | leakage note |
| --- | ---: | --- |
| include_all_42_candidates | 0.046808 | leaky upper-bound |
| exclude_provenance_required | 0.046399 | NF06/provenance-required row excluded |
| no_dynamic_measurement_features | 0.061164 | leakage-reduced sanity check |
| label_family_holdout | 0.168955 | train formal, test non-line-trip |
| bus_fault_holdout | 0.149673 | train non-bus-fault, test B39+B26 |
| B39 holdout | 0.203704 | one-sample absolute error |
| B26 holdout | 0.135774 | one-sample absolute error |

## B39/B26 Holdout Detail

| target | true stress | predicted stress | absolute error | unstable probability |
| --- | ---: | ---: | ---: | ---: |
| B39 | 0.605781 | 0.402078 | 0.203704 | 0.991377 |
| B26 | 0.531476 | 0.667250 | 0.135774 | 0.992757 |

## Conservative Interpretation

The include-all mode uses post-fault compact dynamic measurements, while
`dynamic_stress_score` is also synthesized from compact dynamic measurements.
Therefore include-all should be read as a leaky upper-bound rather than a
formal performance result. The no_dynamic_measurement_features and holdout
modes are more important for judging leakage and small-sample generalization.

This round cannot directly validate GCN because no GCN usefulness audit was
run. B39 and B26 are candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.

## Recommended Next Step

`collect more bus-fault candidates before GCN usefulness audit`
