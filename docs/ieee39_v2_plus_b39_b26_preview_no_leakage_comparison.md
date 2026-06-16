# IEEE39 v2-plus-B39+B26 Preview/No-Leakage Comparison

This round runs a preview/no-leakage comparison on the 42-row
v2-plus-B39+B26 candidate table. It does not run Simulink, does not export
labels, does not train GCN, does not run a GCN usefulness audit, and does not
retrain the formal reranker.

## Plain-Language Meaning

B39 and B26 are both temporary bus-fault candidate labels. This round asks a
small question before any larger model work: if compact post-fault dynamic
measurements are used as input features, do the preview metrics look too good,
and do B39/B26 still look hard when they are held out?

## Boundary Flags

- preview_only: `true`
- final_performance_conclusion: `false`
- simulink_run: `false`
- labels_exported: `false`
- gcn_trained: `false`
- gcn_usefulness_audit_run: `false`
- formal_reranker_retrained: `false`
- old formal gate: `35 / 33 / 33`
- v2-plus-B39+B26 candidate count: `42`
- bus-fault candidates: `2`
- B39 status: `candidate_label_not_formal`
- B26 status: `candidate_label_not_formal`
- L12 excluded: `true`
- NF06 provenance warning preserved: `true`

## Preview Metrics

| mode | RMSE / absolute error | interpretation |
| --- | ---: | --- |
| include_all_42_candidates | `0.046807699921347506` | leaky upper-bound because compact dynamic measurements are used as inputs |
| exclude_provenance_required | `0.04639916608302391` | similar to include-all after excluding provenance-required row |
| no_dynamic_measurement_features | `0.061163642668586794` | leakage-reduced sanity check, more important than include-all |
| label_family_holdout | `0.16895513293724` | train formal rows, test non-line-trip candidates |
| bus_fault_holdout | `0.14967340256432293` | train non-bus-fault rows, test B39+B26 |
| B39 holdout absolute error | `0.20370360540758992` | one-sample holdout |
| B26 holdout absolute error | `0.1357737642351028` | one-sample holdout |

## B39/B26 Detail

| target | true stress | predicted stress | absolute error | unstable probability |
| --- | ---: | ---: | ---: | ---: |
| B39 | `0.6057813745060507` | `0.4020777690984608` | `0.20370360540758992` | `0.9913769399660165` |
| B26 | `0.5314759474846003` | `0.667249711719703` | `0.1357737642351028` | `0.9927567600955874` |

## Conservative Interpretation

The include-all preview remains a leaky upper-bound because
`dynamic_stress_score` is synthesized from compact dynamic measurements and the
same measurement family is also used as input. The no_dynamic_measurement mode
is worse, and the label-family and bus-fault holdouts are much harder. This is
evidence that leakage risk and weak bus-fault generalization remain important.

This round cannot directly validate GCN because no GCN usefulness audit was
run. It also cannot support a final dynamic performance conclusion because B39
and B26 are only two candidate bus-fault samples.

## Recommended Next Step

Collect more bus-fault candidates before GCN usefulness audit.

## All-Remaining Bus-Fault Manual Wiring Follow-Up

Following this recommendation, a separate all-remaining bus-fault manual wiring
plan has been prepared. It is not training, not a GCN audit, not smoke, and not
label export. It only gives the user an auditable package for wiring one
`Grid/Fault_<BUS>_TEMP` block per independent ignored temporary local copy.

- excluded existing candidate labels: `B39`, `B26`
- normal new targets: `B1-B15`, `B17-B25`, `B27-B38`
- special target: `B16`
- total new target count: `37`
- every new target starts with `human_verified_injection_point=false`,
  `safe_to_run_smoke_recommendation=false`, `smoke_success=false`, and
  `candidate_label_exported=false`

## Outputs

- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/v2_plus_b39_b26_preview_comparison.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/v2_plus_b39_b26_preview_comparison.md`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/include_all_42_candidates/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/exclude_provenance_required/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/no_dynamic_measurement_features/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/label_family_holdout/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/bus_fault_holdout/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/b39_holdout/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/b26_holdout/preview_training_metrics.json`

## Boundaries

B39 and B26 are candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.

## All-Bus-Fault Candidate Export Follow-Up

A later candidate-only export round added the 37 all-remaining bus-fault
quality-passed samples. The combined candidate count is now 79, and B1-B39 all
have bus-fault candidates. This did not run Simulink, did not train GCN, did
not retrain the reranker, and did not run a GCN usefulness audit.

These bus-fault labels are still candidate_not_formal_label entries, not formal
labels. The next required step is v2-plus-all-bus-fault no-training composition
review before any training.

## V2 Plus All Bus-Fault Composition Follow-Up

The v2-plus-all-bus-fault no-training composition review later passed. It
confirmed 79 candidate rows, 39 bus-fault candidates, all B1-B39 bus-fault
coverage, no duplicate scenario IDs, and no duplicate label IDs. This review
did not train GCN and did not run a GCN usefulness audit.

The next step is preview/no-leakage comparison in a separate round, not direct
training.
