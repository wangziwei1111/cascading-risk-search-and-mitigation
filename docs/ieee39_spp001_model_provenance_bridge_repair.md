# IEEE39 SPP001 Model Provenance Bridge Repair

This round is an SPP001 model provenance bridge repair. It does not train GCN, does not rerun formal audit, does not execute SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous SPP001 rerun failed because the L15 trip command path belongs to a clean-lab L15 model, while the execution wrapper loads the handwired breaker wrapper. This round only checks whether L15 and L04 can be controlled from the same wrapper. If same-wrapper provenance cannot be confirmed, the path is not fabricated and no SPP001 0/1 label is generated.

## Result

- repair_scope: `spp001_model_provenance_bridge_repair`
- pair_id: `SPP001`
- prior_outaged_branch: `L15`
- candidate_next_branch: `L04`
- l15_trip_command_model_source: `IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15`
- l04_trip_command_model_source: `IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker`
- loaded_execution_wrapper_source: `results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx`
- same_wrapper_trip_commands_available: `False`
- repaired_provenance_manifest_written: `True`
- can_rerun_spp001_after_manual_approval: `False`
- blocker_if_any: `L15 TripCommand path belongs to the clean-lab L15 model, not the loaded handwired breaker wrapper`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, or `slprj` artifacts are committed. The source `.slx` is not modified. Bus-fault labels are not used. L12 remains special/excluded. Pilot labels are not formal training labels. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`build or validate an SPP001-only same-wrapper bridge locally before any rerun`.
