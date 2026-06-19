# IEEE39 SPP001 Sim-Stage Diagnostic Retry

This round is an SPP001 sim-stage diagnostic retry for `L15 -> L04` only. It does not train GCN, does not rerun formal audit, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous round reached `phase_sim_start`, which means MATLAB startup, manifest read, local bridge model load, TripCommand setting, and update diagram had already completed. This round only checks the `sim()` stage with a longer guarded Python timeout. Timeout, failed, blocked, or unknown evidence cannot become a 0/1 label. Even if a pilot label appears, it is not a formal training label.

## Result

- diagnosis_scope: `spp001_sim_stage_diagnostic_retry`
- pair_id: `SPP001`
- previous_likely_timeout_stage: `phase_sim_start`
- sim_stage_diagnostic_attempted: `True`
- execution_status: `timeout`
- single_pair_executed: `False`
- simulink_run: `True`
- phase_sim_start_seen: `True`
- phase_sim_done_seen: `False`
- last_seen_phase_if_available: `phase_sim_start`
- python_timeout_seconds: `600`
- matlab_timeout_seconds_if_available: `540`
- pilot_label_value: `None`
- pilot_label_status: `timeout`
- blocker_if_any: `Python MATLAB wrapper timeout after 600s: IEEE39_SELECTED_PAIR_PHASE:phase_start_matlab_entrypoint:0.044 IEEE39_SELECTED_PAIR_PHASE:phase_manifest_loaded:1.176 IEEE39 Simulink file-generation folders: cache: C:\ieee39_codegen\cache codegen: C:\ieee39_codegen\codegen IEEE39_SELECTED_PAIR_PHASE:phase_file_generation_folder_configured:4.115 IEEE39_SELECTED_PAIR_PHASE:phase_model_load_start:4.118 IEEE39 Simulink file-generation folders: cache: C:\ieee39_codegen\cache codegen: C:\ieee39_codegen\codegen IEEE39_SELECTED_PAIR_PHASE:phase_model_load_done:6.383 IEEE39_SELECTED_PAIR_PHASE:phase_trip_command_set_start:6.388 IEEE39_SELECTED_PAIR_PHASE:phase_trip_command_set_done:6.411 IEEE39_SELECTED_PAIR_PHASE:phase_update_diagram_start:6.412 IEEE39 Simulink file-generation folders: cache: C:\ieee39_codegen\cache codegen: C:\ieee39_codegen\codegen IEEE39_SELECTED_PAIR_PHASE:phase_update_diagram_done:70.143 IEEE39_SELECTED_PAIR_PHASE:phase_sim_start:70.146 IEEE39 Simulink file-generation folders: cache: C:\ieee39_codegen\cache codegen: C:\ieee39_codegen\codegen [����: First solve for initial conditions failed to converge. Trying again with all high priorities relaxed to low.] [> λ�ã�run_ieee39_selected_pair_line_trip_sequence>exe...`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, production model, or local bridge `.slx` file is committed. The source `.slx` is not modified. Bus-fault labels are not used. Line-trip labels remain first priority. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`inspect Simulink solver/runtime settings for SPP001 bridge before any broader execution`.
