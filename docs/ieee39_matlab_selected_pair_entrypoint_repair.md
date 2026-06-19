# IEEE39 MATLAB Selected-Pair Entrypoint Repair

This round is MATLAB selected-pair entrypoint repair. It does not train GCN, does not rerun formal audit, does not execute selected 32 pairs, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous selected-32 evidence round produced 32 blocked rows because the MATLAB entrypoint was still a skeleton. This round adds single-pair smoke execution mode so a future separately approved round can try at most one selected pair.

## Current Status

- repair_scope: `matlab_selected_pair_entrypoint_repair`
- matlab_entrypoint_updated: `True`
- python_runner_updated: `True`
- parser_contract_updated: `True`
- single_pair_smoke_mode_added: `True`
- batch_32_execution_allowed_now: `False`
- full_1056_execution_allowed_now: `False`
- can_attempt_single_pair_smoke_after_manual_approval: `True`

## Smoke Candidate

- pair_id: `SPP001`
- prior_outaged_branch: `L15`
- candidate_next_branch: `L04`
- selection_bucket: `high_relay_ratio_pairs`
- approved_for_execution_now: `False`

## Boundaries

The next round may approve at most one selected pair smoke execution. This round does not commit raw trajectory, full timeseries, or `.mat` files and does not modify the source `.slx`. `beta * RATE_A` is an audit-only proxy, not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. Pilot labels are not formal training labels. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`approve one selected pair smoke execution in a separate round`.

## Follow-Up Provenance Guard

The SPP001 model provenance bridge repair adds a same-wrapper provenance guard to the MATLAB selected-pair entrypoint. Before setting trip command times, the entrypoint checks that prior and next trip command paths belong to the loaded wrapper model. If the L15 and L04 command paths do not share the same wrapper, the entrypoint must return compact failed evidence and keep `pilot_label_value = null`. This does not execute SPP001 smoke, does not export formal labels, does not train GCN, and does not modify the source `.slx`.
