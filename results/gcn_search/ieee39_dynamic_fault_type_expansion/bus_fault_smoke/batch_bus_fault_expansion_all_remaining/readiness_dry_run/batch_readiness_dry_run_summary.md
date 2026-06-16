# IEEE39 All-Remaining Bus-Fault Batch Readiness Dry-Run

This round is a batch readiness dry-run. It did not run simulation, did not run
actual smoke, did not export labels, did not train GCN, did not retrain the
reranker, and did not run a GCN usefulness audit.

| metric | value |
| --- | ---: |
| total_targets | 37 |
| num_manual_evidence_passed | 37 |
| num_readiness_dry_run_checked | 37 |
| num_ready_for_next_round_actual_smoke | 37 |
| num_blocked_before_smoke | 0 |

- ready buses: `B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15, B17, B18, B19, B20, B21, B22, B23, B24, B25, B27, B28, B29, B30, B31, B32, B33, B34, B35, B36, B37, B38, B16`
- blocked buses: `none`
- recommended_next_step: `run batch actual temporary smoke for all 37 ready targets in a separate round, without label export or training`

The 37 new targets are not candidate labels and are not smoke success. B39/B26
remain existing candidate labels, not formal labels.
