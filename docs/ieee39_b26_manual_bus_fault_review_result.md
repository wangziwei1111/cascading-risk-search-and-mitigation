# IEEE39 B26 Manual Bus-Fault Review Result

This round re-collects B26 manual evidence after the temporary fault block was
renamed to `Grid/Fault_B26_TEMP` in the ignored local copy.

Plain wording: we checked whether the renamed B26 temporary fault block is now
connected to the right B26 physical bus node. We did not run a Simulink smoke
simulation and did not turn B26 into a candidate label.

## Scope

- Simulink smoke run: no
- full simulation run: no
- Update Diagram / compile check only: yes
- `.slx` committed: no
- source `.slx` modified: no
- labels exported: no
- GCN trained: no
- reranker retrained: no

## Evidence Summary

The checked temporary copy is:

`results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B26_TEMP_LOCAL_ONLY.slx`

The structure recheck found:

- `Grid/Fault_B26_TEMP` exists.
- `Grid/Fault_B26_TEMP` is a `SimscapeBlock` with mask type
  `Fault (Three-Phase)`.
- `Grid/Fault_B26_TEMP` connects in parallel to `Grid/B25 to B26`,
  `Grid/Bus26_1`, and `Grid/Bus26_2`.
- `Grid/Bus26_1` keeps its original connections to `Grid/B27 to B26`,
  `Grid/B26 to B28`, and `Grid/B26 to B29`.
- `Grid/Bus26_2` keeps its original connection to `Grid/Load26 BusLabel`.
- `Grid/Fault_B26_TEMP` has `fault_start_time = 0.5 s` and
  `fault_duration = 0.08 s`.
- Update Diagram passed.
- The old `Grid/Fault (Three-Phase)` remains near B16 and connects to
  `Grid/Bus16_1` and `Grid/B16 to B17`.

## Review Decision

B26 is accepted as a human-verified injection point for the next readiness gate.

Therefore:

- `human_verified_injection_point = true`
- `safe_to_run_smoke_recommendation = true`
- `selected_injection_block_path = Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node`
- `selected_fault_block_path = Grid/Fault_B26_TEMP`
- `update_diagram_success = true`

This still does not mean B26 smoke success.

## Boundary Notes

- B26 is not smoke success.
- B26 is not a candidate label.
- B39 remains a candidate label, not a formal label.
- old formal gate remains `35 / 33 / 33`.
- v2-plus-B39 count remains `41`.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.

## Artifacts

- manual evidence JSON:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.json`
- manual evidence Markdown:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.md`
- B26 consolidation summary:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.json`
- B26 consolidation Markdown:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.md`

## Next Step

Round 59 prepared B26 readiness in dry-run mode only. The dry-run status is
`ready_for_next_round_temp_smoke`, so the next separate round can run actual
B26 temporary smoke. Do not export labels, train GCN, or retrain the reranker
until the actual smoke output is reviewed.

Round 60 then ran the actual B26 temporary smoke. The result is
`simulation_success = true` with `measurement_extraction_status =
voltage_speed_angle`, but B26 is still only a temporary smoke candidate. See
`docs/ieee39_b26_temporary_bus_fault_smoke.md`.
