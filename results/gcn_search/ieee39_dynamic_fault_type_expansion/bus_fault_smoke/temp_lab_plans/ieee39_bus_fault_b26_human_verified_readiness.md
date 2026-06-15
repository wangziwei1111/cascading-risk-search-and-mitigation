# IEEE39 B26 Human-Verified Readiness

This artifact records the human Simulink GUI readiness gate for the B26
temporary bus-fault smoke candidate.

Plain wording: B26 now has a checked temporary fault injection point, but this
file still does not mean B26 smoke success. It does not modify or commit any
`.slx`, does not export labels, does not train GCN, and does not retrain the
reranker.

## Readiness

- target_bus: `B26`
- human_verified_injection_point: `true`
- safe_to_run_smoke_recommendation: `true`
- manual_review_recommendation: `manual_review_supports_next_round_inventory_update`
- selected_injection_block_path: `Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node`
- selected_fault_block_path: `Grid/Fault_B26_TEMP`
- selected_injection_port_description: `Grid/Fault_B26_TEMP` is connected in
  parallel to the B26 physical node shared by `Grid/B25 to B26`,
  `Grid/Bus26_1`, and `Grid/Bus26_2`. The original B26 connections to
  `Grid/B27 to B26`, `Grid/B26 to B28`, `Grid/B26 to B29`, and
  `Load26 BusLabel` remain present.
- fault_start_s: `0.5`
- fault_clear_s: `0.58`
- duration_s: `0.08`
- R_pn_fault: `1e-3 Ohm`
- R_ng_fault: `1e-3 Ohm`
- enable_temporal_fault: `true`
- update_diagram_success: `true`
- old_fault_still_near_b16: `true`

## Boundaries

- source_model_saved: `false`
- temporary_model_committed: `false`
- source_slx_modified: `false`
- temporary_slx_committed: `false`
- simulink_smoke_run: `false`
- smoke_success: `false`
- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`
- formal_label_gate: `35 / 33 / 33`
- v2_plus_b39_count: `41`
- b39_status: `candidate_label_not_formal`
- l12_touched: `false`

B26 can enter the next separate actual temporary smoke round. It is still not
smoke success and is not a candidate label. B39 remains a candidate label, not
a formal label. `phasor_RMS` is not EMT, and `generator_speed_proxy` is not
direct frequency.
