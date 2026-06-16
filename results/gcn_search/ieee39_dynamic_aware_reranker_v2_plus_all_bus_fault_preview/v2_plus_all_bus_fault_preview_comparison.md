# IEEE39 v2-plus-all-bus-fault Preview/No-Leakage Comparison

This round is preview/no-leakage comparison only. It did not run Simulink, did
not run actual smoke, did not export labels, did not train GCN, did not
retrain the formal reranker, and did not run a GCN usefulness audit.

## Plain-Language Meaning

This step uses very small preview models to ask one narrow question: if we keep
post-fault compact dynamic measurements as inputs, do we get leakage-like
performance inflation, and if we remove them, how hard is bus-fault
generalization really?

## Boundary Flags

- preview_only: `true`
- final_performance_conclusion: `false`
- simulink_run: `false`
- actual_smoke_run: `false`
- labels_exported: `false`
- gcn_trained: `false`
- formal_reranker_retrained: `false`
- gcn_usefulness_audit_run: `false`
- should_train_now: `false`
- total_candidate_rows: `79`
- num_total_bus_fault_candidates: `39`
- all_ieee39_buses_have_bus_fault_candidate: `true`
- unstable_flag_false_buses: `['B1']`
- old_formal_gate: `35 / 33 / 33`

## Metrics Summary

| mode | RMSE | MAE | note |
| --- | ---: | ---: | --- |
| include_all_79_candidates | 0.047793 | 0.037348 | leaky upper-bound |
| no_dynamic_measurement_features | 0.076096 | 0.056225 | leakage-reduced sanity check |
| label_family_holdout | 0.229895 | 0.208437 | train formal, test non-formal families |
| bus_fault_holdout | 0.165132 | 0.135876 | train non-bus-fault, test 39 bus-fault candidates |
| leave_one_bus_fault_out | 0.061684 | 0.050703 | one bus-fault candidate held out each time |
| no_dynamic_measurement_leave_one_bus_fault_out | 0.086604 | 0.069158 | stricter no-leakage bus-fault generalization |

## B1 Detail

B1 keeps `unstable_flag=false` as a low-risk / stable marker. That is not an
error.

| target | true stress | predicted stress | absolute error | true unstable | unstable probability |
| --- | ---: | ---: | ---: | ---: | ---: |
| B1 | 0.196026 | 0.393280 | 0.197254 | 0 | 0.884100 |

## Conservative Interpretation

- `include_all_79_candidates` is a leaky upper-bound because post-fault compact
  dynamic measurements also help define the proxy target.
- `no_dynamic_measurement_features` and
  `no_dynamic_measurement_leave_one_bus_fault_out` are more important than the
  include-all score.
- The 79-row dataset still contains candidate labels, not formal labels.
- Bus-fault rows remain temporary smoke candidates, not engineering-grade
  protection labels.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- This round cannot directly prove GCN useful or not useful because no GCN
  usefulness audit ran.

## Recommended Next Step

`leakage risk confirmed; prepare GCN usefulness audit only with no-leakage features and strict holdouts, not training yet`
