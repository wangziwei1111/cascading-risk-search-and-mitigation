# IEEE39 Selected 32 Pair Controlled Execution Evidence

This round is selected 32 pair controlled execution evidence. It does not train GCN, does not rerun formal audit, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The approved command was allowed to try only the selected 32 line-trip pilot pairs. The current MATLAB entrypoint is still a guarded skeleton, so this run writes compact blocked evidence instead of fabricating simulation results.

## Current Counts

- execution_scope: `selected_32_controlled_execution_evidence`
- selected_pair_count: `32`
- executed_pair_count: `0`
- succeeded_pair_count: `0`
- failed_pair_count: `0`
- timeout_pair_count: `0`
- blocked_pair_count: `32`
- pilot_label_available_count: `0`
- pilot_positive_count: `0`
- pilot_negative_count: `0`
- pilot_unknown_count: `32`

## Boundaries

Only selected 32 pairs are in scope. Raw trajectories, full timeseries, `.mat`, `.slx`, `.slxc`, and `slprj` artifacts are not committed. Timeout, failed, blocked, and unknown results are not converted to 0/1. `beta * RATE_A` is an audit-only proxy and not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. Pilot labels are not formal training labels. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`inspect local MATLAB/Simulink execution logs and repair execution entrypoint before rerunning selected 32 evidence collection`.

## Follow-Up: MATLAB Selected-Pair Entrypoint Repair

The follow-up repair round updates the MATLAB selected-pair entrypoint from a
guarded skeleton to a single-pair smoke-ready backend. It still does not execute
the selected 32 pairs, does not run full 1056 generation, and does not export
formal labels.

The next approved action should be at most one selected pair smoke execution,
using compact evidence only.
