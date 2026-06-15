# IEEE39 Bus-Fault Temporary Lab Plan B26

This is a temporary lab-copy injection plan only. It does not train GCN, does not retrain the reranker, does not export labels, and does not update label gates.

- target_bus: `B26`
- source_model_path: `results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx`
- temporary_model_path: `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B26_TEMP_LOCAL_ONLY.slx`
- temporary_model_is_ignored: `True`
- source_slx_modified: `False`
- source_slx_committed: `False`
- temporary_slx_committed: `False`
- fault_start_s: `0.5`
- fault_clear_s: `0.58`
- duration_s: `0.07999999999999996`
- manual_review_required: `True`

The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct frequency. relay proxy / handwired breaker is not engineering-grade protection.
