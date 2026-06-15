# B26 Manual Connection Evidence

This file records the B26 manual evidence recheck after the temporary fault
block was renamed in the ignored local copy. This round does not run Simulink
smoke, does not export labels, does not train GCN, and does not retrain the
reranker.

## Checked Model

- target bus: `B26`
- temporary model:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B26_TEMP_LOCAL_ONLY.slx`
- temporary fault block: `Grid/Fault_B26_TEMP`
- candidate B26 busbars: `Grid/Bus26_1`, `Grid/Bus26_2`

## Structure Evidence

`Grid/Fault_B26_TEMP` exists. It is a `SimscapeBlock` with mask type
`Fault (Three-Phase)`.

`Grid/Fault_B26_TEMP` port connectivity:

- `LConn1` connects to `Grid/B25 to B26`, `Grid/Bus26_1`, and `Grid/Bus26_2`.

`Grid/Bus26_1` is a `SimscapeBlock` with mask type `Busbar`.

- `LConn1` connects to `Grid/B25 to B26`, `Grid/Fault_B26_TEMP`, and
  `Grid/Bus26_2`.
- `LConn2` connects to `Grid/B27 to B26`.
- `RConn1` connects to `Grid/B26 to B28`.
- `RConn2` connects to `Grid/B26 to B29`.

`Grid/Bus26_2` is a `SimscapeBlock` with mask type `Busbar`.

- `LConn1` connects to `Grid/B25 to B26`, `Grid/Fault_B26_TEMP`, and
  `Grid/Bus26_1`.
- `RConn1` connects to `Grid/Load26 BusLabel`.

Fault parameters on `Grid/Fault_B26_TEMP` are:

- `fault_start_time = 0.5 s`
- `fault_duration = 0.08 s`
- `fault_clear_s = 0.58`
- `R_pn_fault = 1e-3 Ohm`
- `R_ng_fault = 1e-3 Ohm`
- `enable_temporal_fault = true`

The old `Grid/Fault (Three-Phase)` block remains near B16 and connects to
`Grid/Bus16_1` and `Grid/B16 to B17`.

## Update Diagram

- Update Diagram attempted: `true`
- Update Diagram success: `true`
- Update Diagram error: empty

## Review Result

B26 is accepted as a human-verified injection point for the next readiness
gate.

- `human_verified_injection_point = true`
- `safe_to_run_smoke_recommendation = true`
- `selected_injection_block_path = Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node`
- `selected_fault_block_path = Grid/Fault_B26_TEMP`
- `simulink_smoke_run = false`
- `smoke_success = false`
- `labels_exported = false`
- `gcn_trained = false`
- `reranker_retrained = false`
- old formal gate: `35 / 33 / 33`
- v2-plus-B39 count: `41`

Next action: prepare B26 readiness in a separate round before any temporary
smoke. Do not jump directly from this evidence file to smoke execution.
