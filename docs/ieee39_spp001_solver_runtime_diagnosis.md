# IEEE39 SPP001 Solver/Runtime Diagnosis

This round is an SPP001 solver/runtime diagnosis for `L15 -> L04` only. It does not train GCN, does not rerun formal audit, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous timeout was already localized to the `sim()` stage. This round checks solver/runtime evidence and model configuration only. It does not generate a 0/1 label. Timeout, failed, blocked, or unknown evidence cannot become a 0/1 label.

The compact evidence contains the MATLAB warning that the first solve for initial conditions failed to converge and that Simulink retried with high priorities relaxed to low. That points to an initialization or solver-runtime issue, not to GCN, not to selected 32, and not to formal label export.

## Result

- diagnosis_scope: `spp001_solver_runtime_diagnosis`
- pair_id: `SPP001`
- same_wrapper_confirmed: `True`
- previous_likely_timeout_stage: `phase_sim_start`
- previous_python_timeout_seconds: `600`
- previous_matlab_timeout_seconds: `540`
- initial_condition_convergence_warning_detected: `True`
- solver_runtime_diagnostic_only: `True`
- full_smoke_executed: `False`
- sim_run_attempted: `False`
- solver_type_if_available: `Fixed-step`
- solver_name_if_available: `FixedStepDiscrete`
- simulation_mode_if_available: `normal`
- powergui_or_phasor_mode_if_available: `unknown`
- likely_runtime_blocker: `initial_condition_convergence_at_sim_start`
- blocker_if_any: `None`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, production model, or local bridge `.slx` file is committed. The source `.slx` is not modified. Bus-fault labels are not used. Line-trip labels remain first priority. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`approve one short-stop SPP001 solver profiling run focused on initialization; do not export labels or train`.
