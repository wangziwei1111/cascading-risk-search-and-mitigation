# IEEE39 Controlled Execution Backend Repair

This round is controlled execution backend repair. It does not train GCN, does not rerun formal audit, does not execute selected 32 pairs, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not save a production model.

## What Was Added

- selected-32-only Python runner
- MATLAB two-step line-trip entrypoint skeleton
- result parser contract
- evidence-only output writer
- local/manual execution instruction pack
- selected-32-only guard
- no full 1056 generation guard
- no formal label export guard
- no training guard
- no raw trajectory / full timeseries / `.mat` commit guard

## Current Status

- repair_scope: `controlled_execution_backend_repair`
- selected_pair_count: `32`
- can_execute_selected_32_pairs_after_manual_approval: `True`
- can_execute_selected_32_pairs_now: `False`
- blocker_if_any: `execution intentionally not run in repair round; manual approval and explicit --execute are required`

## Boundaries

Execution of selected 32 pairs still requires the next round of manual approval. This round does not commit raw trajectory, full timeseries, or `.mat` files. `beta * RATE_A` is an audit-only proxy, not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection. There is no deployment and no GCN usefulness conclusion.

## Next Step

`approve execution of selected 32 pairs using the repaired backend in a separate round`.

## Follow-Up: Selected 32 Evidence Collection

The follow-up selected-32 evidence round used the repaired Python runner with
explicit `--execute` approval, but the MATLAB entrypoint remains a guarded
skeleton. Therefore all 32 selected pairs were recorded as blocked/null compact
evidence. No selected-pair 0/1 labels were fabricated, and no formal labels were
exported.

This follow-up still does not train GCN, does not rerun formal audit, does not
run full 1056 generation, does not retrain the reranker, and does not commit raw
trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, or `slprj` artifacts.
