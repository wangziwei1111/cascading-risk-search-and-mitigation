# IEEE39 B26 Temp Smoke Dry-Run Readiness

This is a dry-run readiness report only. It does not run Simulink smoke,
does not modify or commit any `.slx`, does not export labels, does not
train GCN, and does not retrain the reranker.

- target_bus: `B26`
- dry_run: `True`
- readiness_status: `ready_for_next_round_temp_smoke`
- would_run_smoke_next_round: `True`
- actual_simulink_run: `False`
- selected_injection_block_path: `Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node`
- selected_fault_block_path: `Grid/Fault_B26_TEMP`
- fault window: `0.5` s to `0.58` s
- formal_label_gate: `35 / 33 / 33`
- v2_candidate_count: `40`
- v2_plus_b39_count: `41`

Boundary: B26 is ready for a separate next-round temporary smoke attempt,
but B26 is still not smoke success and is not a new candidate label.
