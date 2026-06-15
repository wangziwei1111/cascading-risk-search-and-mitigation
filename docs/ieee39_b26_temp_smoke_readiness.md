# IEEE39 B26 Temporary Smoke Readiness

This round records B26 readiness and dry-run readiness only.

Plain wording: the B26 temporary fault block has a human-verified injection
point, and the dry-run gate says it is ready for a later actual temporary smoke
attempt. No actual Simulink smoke was run in this round.

## Readiness Result

- target_bus: `B26`
- human_verified_injection_point: `true`
- safe_to_run_smoke_recommendation: `true`
- dry_run_readiness_status: `ready_for_next_round_temp_smoke`
- selected_fault_block_path: `Grid/Fault_B26_TEMP`
- selected_injection_block_path: `Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node`
- fault_start_s: `0.5`
- fault_clear_s: `0.58`
- duration_s: `0.08`
- formal_label_gate: `35 / 33 / 33`
- v2_plus_b39_count: `41`
- b39_status: `candidate_label_not_formal`

## Boundaries

- actual Simulink smoke run: `false`
- source `.slx` modified: `false`
- `.slx` submitted: `false`
- temporary `.slx` committed: `false`
- labels exported: `false`
- GCN trained: `false`
- reranker retrained: `false`
- L12 touched: `false`
- B26 smoke success: `false`
- B26 candidate label exported: `false`

B39 remains a candidate label, not a formal label. The old formal gate remains
`35 / 33 / 33`, and the v2-plus-B39 count remains `41`.

`phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. The
temporary bus-fault injection is not engineering-grade protection.

## Artifacts

- Human readiness JSON:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.json`
- Human readiness Markdown:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.md`
- Dry-run readiness JSON:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_dry_run_readiness.json`
- Dry-run readiness Markdown:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_dry_run_readiness.md`

## Recommended Next Step

Run actual B26 temporary smoke in a separate next round. That next round should
still avoid exporting labels or training models until the smoke output is
reviewed.
