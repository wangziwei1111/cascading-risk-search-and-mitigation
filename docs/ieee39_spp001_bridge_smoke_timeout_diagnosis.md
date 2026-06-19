# IEEE39 SPP001 Bridge Smoke Timeout Diagnosis

This round is SPP001 bridge smoke timeout diagnosis only. It does not train GCN, does not rerun formal audit, does not execute full SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous round confirmed the same-wrapper bridge for `L15 -> L04`, but the execution hit a 180 second timeout. This round only localizes the timeout stage. It adds compact phase timing hooks for a future diagnostic-only retry and reads the old timeout evidence. The old timeout cannot become a 0/1 label.

## Diagnosis

- diagnosis_scope: `spp001_bridge_smoke_timeout_diagnosis`
- pair_id: `SPP001`
- previous_execution_status: `timeout`
- previous_timeout_seconds: `180`
- previous_same_wrapper_confirmed: `True`
- diagnostic_only: `True`
- sim_run_attempted: `False`
- phase_timing_added_to_matlab_entrypoint: `True`
- phase_timing_added_to_python_runner: `True`
- last_seen_phase_if_available: `phase_sim_start`
- repeated_codegen_folder_messages_detected: `True`
- likely_timeout_stage: `phase_sim_start`
- timeout_root_cause_hypothesis: `Previous evidence contains a phase marker; timeout likely occurred at or after phase_sim_start.`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, local bridge `.slx`, venv, wheel, DLL, or production model files are committed. The source `.slx` is not modified. Bus-fault labels are not used. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`approve one SPP001 diagnostic retry with phase timing focused on that stage; do not export labels or train`.
