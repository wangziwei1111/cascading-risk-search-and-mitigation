# IEEE39 B26 Bus-Fault Candidate Export Summary

This export is candidate-only. It does not run Simulink, does not submit `.slx`,
does not modify source `.slx`, does not train GCN, and does not retrain the
reranker.

- target_bus: `B26`
- scenario_id: `BF_B26_TEMP_SMOKE`
- export_scope: `candidate_only`
- dynamic_stress_score: `0.5314759474846006`
- previous_v2_plus_b39_count: `41`
- num_new_b26_bus_fault_candidates: `1`
- num_v2_plus_b39_b26_candidate_labels: `42`
- old formal gate: `35 / 33 / 33`
- b39_status: `candidate_label_not_formal`
- L12 excluded: `true`
- NF06 provenance warning preserved: `true`
- should_train_now: `false`

B26 is a candidate label, not a formal label. B39 is also a candidate label, not
a formal label. `phasor_RMS` is not EMT, `generator_speed_proxy` is not direct
frequency, and temporary bus-fault injection is not engineering-grade
protection.

Recommended next step: run v2-plus-B39+B26 no-training composition review before
any training.
