# IEEE39 B39 Temp Smoke Dry-Run Readiness

This is a dry-run readiness report only. It does not run Simulink smoke,
does not modify or commit any `.slx`, does not export labels, does not
train GCN, and does not retrain the reranker.

- target_bus: `B39`
- dry_run: `True`
- readiness_status: `ready_for_next_round_temp_smoke`
- would_run_smoke_next_round: `True`
- actual_simulink_run: `False`
- selected_injection_block_path: `Grid/Bus39`
- selected_fault_block_path: `Grid/Fault_B39_TEMP`
- fault window: `0.5` s to `0.58` s
- formal_label_gate: `35 / 33 / 33`
- v2_candidate_count: `40`

Boundary: B39 is ready for a separate next-round temporary smoke attempt,
but B39 is still not smoke success.
