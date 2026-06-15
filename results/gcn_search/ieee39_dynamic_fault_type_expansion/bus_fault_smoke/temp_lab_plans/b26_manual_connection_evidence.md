# B26 Manual Connection Evidence

This file records a B26 manual GUI review evidence pass. It does not run
Simulink smoke, does not export labels, does not train GCN, and does not retrain
the reranker.

## Checked Model

- target bus: `B26`
- temporary model:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B26_TEMP_LOCAL_ONLY.slx`
- expected temporary fault block: `Grid/Fault_B26_TEMP`
- candidate B26 busbars: `Grid/Bus26_1`, `Grid/Bus26_2`

## Structure Evidence

`Grid/Bus26_1` is a `SimscapeBlock` with mask type `Busbar`.

- `LConn1` connects to `Grid/B25 to B26`, `Grid/Fault (Three-Phase)1`, and
  `Grid/Bus26_2`.
- `LConn2` connects to `Grid/B27 to B26`.
- `RConn1` connects to `Grid/B26 to B28`.
- `RConn2` connects to `Grid/B26 to B29`.

`Grid/Bus26_2` is a `SimscapeBlock` with mask type `Busbar`.

- `LConn1` connects to `Grid/B25 to B26`, `Grid/Fault (Three-Phase)1`, and
  `Grid/Bus26_1`.
- `RConn1` connects to `Grid/Load26 BusLabel`.

The checked temporary model does not contain `Grid/Fault_B26_TEMP`. The
observed B26 parallel fault block is `Grid/Fault (Three-Phase)1`; it is a
`SimscapeBlock` with mask type `Fault (Three-Phase)` and connects in parallel
to `Grid/B25 to B26`, `Grid/Bus26_1`, and `Grid/Bus26_2`.

Fault parameters on the observed B26 parallel fault block are:

- `fault_start_time = 0.5 s`
- `fault_duration = 0.08 s`
- `fault_clear_s = 0.58`
- `R_pn_fault = 1e-3 Ohm`
- `R_ng_fault = 1e-3 Ohm`

The old `Grid/Fault (Three-Phase)` block remains near B16 and connects to
`Grid/Bus16_1` and `Grid/B16 to B17`.

## Update Diagram

- Update Diagram attempted: `true`
- Update Diagram success: `true`
- Update Diagram error: empty

## Review Result

B26 is not accepted as human verified in this round because the required named
block `Grid/Fault_B26_TEMP` was not found. The structure gives positive
evidence that a parallel B26 temporary fault exists, but it does not satisfy the
explicit template condition.

- `human_verified_injection_point = false`
- `safe_to_run_smoke_recommendation = false`
- `simulink_smoke_run = false`
- `smoke_success = false`
- `labels_exported = false`
- `gcn_trained = false`
- `reranker_retrained = false`
- old formal gate: `35 / 33 / 33`
- v2-plus-B39 count: `41`

Next action: confirm or rename the B26 temporary fault block as
`Grid/Fault_B26_TEMP` in the ignored GUI temporary copy, then rerun manual
evidence collection before any temporary smoke.
