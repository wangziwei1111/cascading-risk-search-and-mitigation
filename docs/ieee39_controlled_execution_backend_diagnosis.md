# IEEE39 Controlled Execution Backend Diagnosis

This round is controlled execution backend diagnosis only. It does not train GCN, does not rerun formal audit, does not execute selected 32 pairs, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not save a production model.

## Plain-Language Purpose

上一轮 selected pair execution 被 `blocked`，原因是没有安全可调用的 controlled Simulink execution backend。大白话说：我们有 32 个要检查的故障对，也有部分线路映射和 wrapper 线索，但还缺一个可靠的“两步断线、批量运行、超时保护、只输出 evidence summary”的后端。

## Diagnosis Result

- diagnosis_scope: `controlled_execution_backend_diagnosis`
- selected_pair_count: `32`
- matlab_available: `True`
- simulink_available: `unknown`
- ieee39_wrapper_model_found: `True`
- selected_pair_mapping_found: `True`
- two_step_line_trip_injection_supported: `False`
- batch_runner_found: `False`
- timeout_policy_found: `True`
- result_parser_found: `False`
- evidence_writer_found: `True`
- safe_no_raw_artifact_policy_found: `True`
- can_execute_selected_32_pairs_now: `False`
- can_execute_without_full_1056: `True`
- graceful_blocked_mode_available: `True`
- blocker_if_any: `selected-pair controlled execution backend is incomplete: missing approved two-step line-trip sequence injection, selected-pair batch runner, and selected-pair result parser contract`

## Boundaries

This round does not commit raw trajectory, full timeseries, or `.mat` files. `beta * RATE_A` is an audit-only proxy, not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection. There is no deployment and no GCN usefulness conclusion.

## Next Step

`add a selected-32-only controlled execution backend or write local manual execution instructions before rerunning evidence collection`.

## Follow-Up: Backend Repair Skeleton

The follow-up repair round added a guarded selected-32-only controlled execution backend skeleton. It adds the Python runner, MATLAB line-trip sequence entrypoint skeleton, compact evidence parser contract, evidence-only output writer, and local manual execution instruction pack.

This follow-up still does not execute the selected 32 pairs. It also does not train GCN, does not rerun strict no-leakage/formal audit, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not save a production model.

The repaired backend is intentionally conservative: execution remains blocked in this repair round and would require a separately approved local/manual execution round. Unknown, timeout, blocked, or failed pair outcomes remain null and must not be converted into 0/1 labels.

## Follow-Up: Selected 32 Evidence Collection

The selected-32 evidence follow-up used the repaired backend with explicit approval, but the MATLAB entrypoint was still a guarded skeleton. The evidence output therefore records 32 blocked/null pilot rows and does not fabricate formal labels.

## Follow-Up: MATLAB Selected-Pair Entrypoint Repair

The MATLAB selected-pair entrypoint repair follow-up adds single-pair smoke mode. It still does not execute selected 32 pairs, does not run full 1056 generation, and does not export formal labels.
