# IEEE39 B39 Bus-Fault Manual Review Result

## Scope

This document records a human Simulink GUI review result for the temporary B39
bus-fault injection point. This round does not run Simulink smoke, does not run
a full simulation, does not modify the source `.slx`, does not commit any
temporary `.slx`, does not export labels, does not train GCN, and does not
retrain the dynamic-aware reranker.

## Bus39 Evidence

The reviewed temporary local copy is:

`IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B39_TEMP_LOCAL_ONLY`

The B39 bus block is a real physical busbar block:

- block path:
  `IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B39_TEMP_LOCAL_ONLY/Grid/Bus39`
- `BlockType = SimscapeBlock`
- `MaskType = Busbar`
- current maximum observed `n_nodes = four`

The four original Bus39 physical connections remain present:

- `B9 to B39`
- `Gen1 BusLabel`
- `B39 to B1`
- `Load39 BusLabel`

## Existing Fault Block Boundary

The existing `Fault (Three-Phase)` block is still near B16:

- old fault path: `Grid/Fault (Three-Phase)`
- old fault is connected to `Grid/Bus16_1`
- old fault is connected to `Grid/B16 to B17`

This old fault block is not treated as the B39 fault, and this review does not
claim that the old fault block was moved.

## Temporary B39 Fault Evidence

A temporary copied fault block was manually added in the ignored temporary local
copy:

- selected fault block path: `Grid/Fault_B39_TEMP`
- selected injection block path: `Grid/Bus39`
- `Fault_B39_TEMP` is connected in parallel at the Bus39 Port 1 / `B9 to B39`
  physical node.
- Bus39 Port 1 now connects to both `Grid/B9 to B39` and
  `Grid/Fault_B39_TEMP`.
- `Fault_B39_TEMP` connectivity shows connection to both `Grid/B9 to B39` and
  `Grid/Bus39`.
- the original Bus39 connections remain intact.
- Update Diagram passed without error.

## Fault Parameters

The manually checked `Fault_B39_TEMP` parameters are:

- `R_pn_fault = 1e-3 Ohm`
- `R_ng_fault = 1e-3 Ohm`
- `fault_start_time = 0.5 s`
- `fault_duration = 0.08 s`
- equivalent `fault_clear_s = 0.58 s`

## Consolidation Meaning

This evidence supports `human_verified_injection_point = true` and
`safe_to_run_smoke_recommendation = true` for B39 manual review consolidation.

It is still not smoke success. It only means the next round may prepare a
temporary B39 smoke run, while preserving the boundary that the old formal gate
remains `35 / 33 / 33` and the v2 candidate count remains `40`.

## Limitations

- B26 remains unverified.
- The model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- Relay proxy / handwired breaker / temporary bus fault injection behavior is
  not engineering-grade protection.

## Readiness Update

The follow-up readiness / inventory update records this human review as a
separate readiness gate:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.md`

The temp-lab runner was then executed only as a dry-run readiness check, not as
a Simulink smoke run:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.md`

The dry-run status is `ready_for_next_round_temp_smoke`. This means B39 may
enter the next separate temporary smoke round. It does not export labels, does
not train GCN, does not retrain the reranker, and still does not change the
formal label gate or v2 candidate count.
