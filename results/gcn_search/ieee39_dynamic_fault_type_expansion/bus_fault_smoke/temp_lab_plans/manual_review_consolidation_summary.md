# Manual Bus-Fault Review Consolidation

- target_bus: `B39`
- recommendation: `do_not_run_smoke`
- human_verified_injection_point: `false`
- safe_to_run_smoke_recommendation: `false`
- simulink_run: `false`
- inventory_modified: `false`
- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`
- formal_label_gate: `35 / 33 / 33`
- v2_candidate_count: `40`

## Failed Checks

- source_model_opened_read_only=not_true
- fault_block_connected_in_parallel=not_true
- original_network_connection_preserved=not_true
- no_unintended_bypass=not_true
- no_floating_ports=not_true
- no_unintended_islanding=not_true
- update_diagram_attempted=not_true
- update_diagram_success=not_true
- measurement_signals_expected_available=not_true
- human_verified_injection_point=not_true
- safe_to_run_smoke_recommendation=not_true
- selected_injection_block_path=empty
- selected_injection_port_description=empty
- selected_fault_block_path=empty
- screenshots_or_manual_evidence_paths=empty

This consolidation does not run Simulink, does not modify `.slx`, does not export labels, and does not train.
