# IEEE39 SPP001 Same-Wrapper Bridge Smoke Rerun

This round uses the repaired local same-wrapper bridge for the one manually approved SPP001 path `L15 -> L04`. It does not train GCN, does not rerun formal audit, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The physical meaning is simple: first trip line L15, then trip line L04 inside the same local Simulink wrapper, and check whether compact dynamic evidence can be produced. If the run is blocked, failed, timeout, or unknown, the pilot label stays null. This pilot label, if available, is not a formal training label.

## Result

- execution_scope: `spp001_same_wrapper_bridge_smoke_rerun`
- pair_id: `SPP001`
- prior_outaged_branch: `L15`
- candidate_next_branch: `L04`
- planned_contingency_sequence: `L15;L04`
- same_wrapper_confirmed: `True`
- execution_attempted: `True`
- execution_status: `timeout`
- single_pair_executed: `False`
- simulink_run: `False`
- pilot_label_value: `None`
- pilot_label_status: `timeout`
- dynamic_stress_score_if_available: `None`
- unstable_flag_if_available: `None`
- blocker_if_any: `Python MATLAB wrapper timeout after 180s: IEEE39_SELECTED_PAIR_PHASE:phase_start_matlab_entrypoint:0.032 IEEE39_SELECTED_PAIR_PHASE:phase_manifest_loaded:1.213 IEEE39 Simulink file-generation folders: cache: C:\ieee39_codegen\cache codegen: C:\ieee39_codegen\codegen IEEE39_SELECTED_PAIR_PHASE:phase_file_generation_folder_configured:4.345 IEEE39_SELECTED_PAIR_PHASE:phase_model_load_start:4.349 IEEE39 Simulink file-generation folders: cache: C:\ieee39_codegen\cache codegen: C:\ieee39_codegen\codegen IEEE39_SELECTED_PAIR_PHASE:phase_model_load_done:6.842 IEEE39_SELECTED_PAIR_PHASE:phase_trip_command_set_start:6.848 IEEE39_SELECTED_PAIR_PHASE:phase_trip_command_set_done:6.892 IEEE39_SELECTED_PAIR_PHASE:phase_update_diagram_start:6.894 IEEE39 Simulink file-generation folders: cache: C:\ieee39_codegen\cache codegen: C:\ieee39_codegen\codegen IEEE39_SELECTED_PAIR_PHASE:phase_update_diagram_done:71.980 IEEE39_SELECTED_PAIR_PHASE:phase_sim_start:71.983 IEEE39 Simulink file-generation folders: cache: C:\ieee39_codegen\cache codegen: C:\ieee39_codegen\codegen`

## Boundaries

No raw trajectories, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, production model, or local bridge `.slx` file is committed. The source `.slx` is not modified. Bus-fault labels are not used. Line-trip labels remain first priority. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`inspect SPP001 bridge smoke failure and repair before any broader execution`.
