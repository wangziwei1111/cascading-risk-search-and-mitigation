# IEEE39 All-Remaining Bus-Fault Batch Actual Smoke

This round ran actual Simulink smoke for the readiness-passed temporary local
copies. It did not export labels, did not train GCN, did not retrain the
reranker, and did not run a GCN usefulness audit.

| metric | value |
| --- | ---: |
| total_targets | 37 |
| num_smoke_attempted | 37 |
| num_simulation_success | 37 |
| num_simulation_failed | 0 |
| num_timeout | 0 |
| unstable_flag_true_count | 36 |

Successful smoke is only temporary smoke evidence. The 37 new targets are not
candidate labels. The next step is smoke quality review for successful buses
before any label export.
