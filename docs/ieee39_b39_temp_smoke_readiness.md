# IEEE39 B39 Temporary Smoke Readiness

This document records the B39 readiness / inventory update after the human
Simulink GUI review. It does not report a Simulink smoke result.

## What changed

B39 now has a separate human-verified readiness artifact:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.md`

The readiness artifact records:

- target_bus: `B39`
- selected_injection_block_path: `Grid/Bus39`
- selected_fault_block_path: `Grid/Fault_B39_TEMP`
- fault_start_s: `0.5`
- fault_clear_s: `0.58`
- duration_s: `0.08`
- human_verified_injection_point: `true`
- safe_to_run_smoke_recommendation: `true`
- manual_review_recommendation: `manual_review_supports_next_round_inventory_update`

This human readiness layer does not overwrite
`matlab_bus_fault_injection_inventory_B39.json`. The MATLAB automatic inventory
remains conservative because it did not verify a safe automatic physical wiring
rule.

## Dry-run readiness check

The temp-lab smoke runner was run only in dry-run mode with the human readiness
artifact. It produced:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.md`

The dry-run status is:

- dry_run: `true`
- readiness_status: `ready_for_next_round_temp_smoke`
- would_run_smoke_next_round: `true`
- actual_simulink_run: `false`
- smoke_success: `false`
- labels_exported: `false`
- gcn_trained: `false`
- reranker_retrained: `false`

## Boundaries

- This round only updates B39 readiness / inventory artifacts.
- No Simulink smoke was run.
- No full simulation was run.
- No `.slx` was submitted.
- The source `.slx` was not modified.
- No labels were exported.
- GCN was not trained.
- The reranker was not retrained.
- B39 can enter the next separate temporary smoke round.
- B39 is still not smoke success.
- B26 remains unverified.
- The old formal gate remains `35 / 33 / 33`.
- The v2 candidate count remains `40`.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- The temporary bus-fault injection is not engineering-grade protection.

Recommended next step: run the actual B39 temporary smoke in a separate round,
still without exporting labels or training until the smoke output is reviewed.

## Actual Smoke Follow-Up

The actual B39 temporary smoke was run in the follow-up round using only the
ignored local temporary `.slx` copy. The run succeeded as a temporary smoke
candidate:

- scenario_id: `BF_B39_TEMP_SMOKE`
- simulation_success: `true`
- measurement_extraction_status: `voltage_speed_angle`
- training_ready_candidate_smoke: `true`
- signal_source_summary includes `frequency=generator_speed_proxy`

This still does not export labels, train GCN, retrain the reranker, update the
formal label gate, or update the v2 candidate count. See
`docs/ieee39_b39_temporary_bus_fault_smoke.md`.
