# IEEE39 Selected Single-Outage Pilot Pair Execution

This round is selected 32 single-outage pilot pair execution approval and evidence collection. It does not train GCN, does not rerun formal audit, does not export formal labels, does not retrain the reranker, and does not save or deploy a production model.

## Plain-Language Purpose

上一轮已经从 1056 个 `single_outage_state x next_branch` 候选里挑出 32 个 pilot pair。大白话说，这一步原本是想逐个检查“先断一条线后，再断下一条线会不会出现风险”。但当前仓库里没有可以安全调用的受控 Simulink 执行后端，所以本轮没有编造仿真结果，而是把 32 条全部记录为 `blocked`，`pilot_label_value` 保持 `null`。

## Boundary

- This is not full 1056 generation.
- If Simulink is run in a future round, it must be limited to the selected 32 pairs unless separately approved.
- Raw trajectories, full timeseries, and `.mat` files are not committed.
- Timeout, unknown, blocked, or failed cases are not converted to 0/1.
- `beta * RATE_A` is an audit-only proxy, not a real relay setting.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- NF06 warning is preserved.
- Pilot labels are not formal training labels.
- No deployment is claimed.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.

## Current Evidence Summary

- execution_scope: `selected_single_outage_pilot_pair_execution`
- selected_pair_count: `32`
- executed_pair_count: `0`
- succeeded_pair_count: `0`
- failed_pair_count: `0`
- timeout_pair_count: `0`
- unknown_pair_count: `32`
- pilot_label_available_count: `0`
- pilot_positive_count: `0`
- pilot_negative_count: `0`
- pilot_unknown_count: `32`
- pilot_blocked_count: `32`
- blocker_if_any: `controlled Simulink execution backend is not available in this audit runner; no pilot labels were generated`

## Next Step

`fix controlled execution environment or run selected pair execution locally, then rerun evidence collection`. If future execution succeeds and produces both positive and negative pilot examples, the next round should request pilot label export approval separately; do not train yet.

## Follow-Up: Backend Diagnosis

A later controlled execution backend diagnosis confirms that the selected pair
execution was blocked by a missing safe callable controlled Simulink execution
backend. It does not train GCN, does not rerun formal audit, does not execute
selected 32 pairs, does not run full 1056 generation, does not export formal
labels, and does not retrain the reranker.

The diagnosis found that the IEEE39 wrapper model and selected-pair branch
mapping are available, but the backend is still incomplete because the approved
two-step line-trip sequence injection, selected-32-only batch runner, and
selected-pair result parser contract are missing.

The same boundaries remain active: `beta * RATE_A` is an audit-only proxy, not a
real relay setting; bus-fault labels are not used; L12 remains
special/excluded; NF06 warning is preserved; `phasor_RMS` is not EMT;
`generator_speed_proxy` is not direct frequency; temporary bus-fault injection
is not engineering-grade protection; no deployment is claimed.
