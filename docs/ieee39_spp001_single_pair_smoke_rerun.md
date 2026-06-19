# IEEE39 SPP001 Single-Pair Smoke Rerun

This round reruns the one approved pair after the L15 readiness repair. It does not train GCN, does not rerun formal audit, does not execute the selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The approved pilot path is `L15 -> L04`. The run only checks whether the repaired MATLAB/Simulink single-pair execution path can produce compact evidence. Any failed, blocked, timeout, or unknown result remains null and is not converted into a 0/1 training label.

## Result

- execution_scope: `spp001_single_pair_smoke_rerun`
- pair_id: `SPP001`
- prior_outaged_branch: `L15`
- candidate_next_branch: `L04`
- execution_attempted: `True`
- execution_status: `failed`
- pilot_label_value: `None`
- pilot_label_status: `failed`
- dynamic_stress_score_if_available: `None`
- unstable_flag_if_available: `None`
- blocker_if_any: `SPP001 provenance manifest does not confirm same-wrapper commands: L15 TripCommand path belongs to the clean-lab L15 model, not the loaded handwired breaker wrapper`

## Boundaries

No raw trajectories, full timeseries, `.mat`, `.slx`, `.slxc`, or `slprj` artifacts are committed. The source `.slx` is not modified. Bus-fault labels are not used. Line-trip labels remain first priority. L12 remains special/excluded. Pilot labels are not formal training labels. This is not a final project conclusion.

## Next Step

`inspect timeout/failure evidence and rerun one-pair smoke after repair`.
