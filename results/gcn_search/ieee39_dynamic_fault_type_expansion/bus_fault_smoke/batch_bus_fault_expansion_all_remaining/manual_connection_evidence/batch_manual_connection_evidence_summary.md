# Batch Manual Connection Evidence Summary

This round collected and consolidated manual connection evidence only. It did
not run Simulink simulation, did not run actual smoke, did not export labels,
did not train GCN, did not retrain the reranker, and did not run a GCN
usefulness audit.

| metric | value |
| --- | ---: |
| total_targets | 37 |
| num_temp_models_found | 37 |
| num_fault_blocks_found | 37 |
| num_update_diagram_success | 37 |
| num_automated_evidence_check_passed | 37 |
| num_human_verified_injection_point | 37 |
| num_safe_to_run_smoke_recommendation | 37 |

## Ready / Blocked

- buses ready for readiness dry-run: `B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15, B17, B18, B19, B20, B21, B22, B23, B24, B25, B27, B28, B29, B30, B31, B32, B33, B34, B35, B36, B37, B38, B16`
- buses blocked: `none`
- recommended_next_step: `prepare batch readiness dry-run for all 37 targets in a separate round`

B39 and B26 remain existing candidate labels, not formal labels. The 37 new
targets are not candidate labels and are not smoke success. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.
