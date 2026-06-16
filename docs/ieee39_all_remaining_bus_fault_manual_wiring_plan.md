# IEEE39 All-Remaining Bus-Fault Manual Wiring Plan

This round prepares a manual GUI wiring package for all remaining IEEE39
bus-fault targets. It is only a preparation plan.

## What This Does

The user can open one ignored temporary local copy per target bus and manually
wire one new `Grid/Fault_<BUS>_TEMP` block in parallel at the chosen bus
injection point. B39 and B26 already have quality-reviewed candidate labels, so
they are excluded from this wiring batch.

## Targets

- existing completed bus faults: `B39`, `B26`
- normal new targets: `B1-B15`, `B17-B25`, `B27-B38`
- special target: `B16`
- total new target count: `37`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

Each target bus uses one independent ignored temporary local copy. Do not put
multiple target fault blocks into one `.slx` file.

## B16 Special Handling

B16 is marked special because the old `Grid/Fault (Three-Phase)` is near B16.
Do not rename or move the old fault. Create a separate
`Grid/Fault_B16_TEMP` only inside the B16 temporary local copy.

## Initial Status Of Every New Target

- human_verified_injection_point: `false`
- safe_to_run_smoke_recommendation: `false`
- smoke_success: `false`
- candidate_label_exported: `false`

## Boundaries

This round does not run Simulink, does not run smoke, does not export labels,
does not train GCN, does not retrain the reranker, and does not run a GCN
usefulness audit. B39 and B26 remain candidate labels, not formal labels. The
model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.

## Artifacts

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/ieee39_bus_fault_all_remaining_targets.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/ieee39_bus_fault_all_remaining_targets.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/all_remaining_manual_gui_wiring_commands.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_manual_connection_evidence_schema.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_gate_sequence.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/manual_bus_fault_injection_review_template_<BUS>.json`

## Manual Connection Evidence Follow-Up

After the user manually wired all 37 temporary local copies, the batch evidence
collection round found:

- temp models found: `37`
- fault blocks found: `37`
- Update Diagram success: `37`
- automated evidence check passed: `37`
- safe to run smoke recommendation: `37`

This is still not actual smoke and not label export. The next step is a
separate batch readiness dry-run for the passing targets.
