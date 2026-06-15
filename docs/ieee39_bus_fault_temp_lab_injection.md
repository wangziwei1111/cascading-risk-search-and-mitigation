# IEEE39 Bus-Fault Temporary Lab Injection

## Purpose

This round prepares a temporary-lab workflow for different-bus three-phase
fault injection on the IEEE39 graphical dynamic model. The priority bus is
`B39`; `B26` is the fallback target.

Plain wording: this is only a safe-injection-point check on a copied local
model. It does not turn the result into labels, does not train a model, and
does not change the source Simulink model.

## Workflow

1. Build a temporary plan for the target bus.
2. Optionally copy the source `.slx` into an ignored local lab directory.
3. Use MATLAB to load the temporary copy and inventory candidate blocks around
   the target bus.
4. Refuse smoke simulation unless the inventory reports
   `safe_to_run_smoke = true`.

The current MATLAB helper loads and updates the temporary copy, records nearby
candidate blocks, and closes the model without saving. It does not insert a
three-phase fault block and does not wire physical ports automatically.

## Outputs

- B39 plan:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B39_plan.json`
- B39 inventory:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/matlab_bus_fault_injection_inventory_B39.json`
- B26 fallback plan:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B26_plan.json`
- B26 fallback inventory:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/matlab_bus_fault_injection_inventory_B26.json`
- feasibility summary:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_feasibility_summary.json`
- conservative smoke report:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.json`

## Current Result

| target bus | injection point found | safe to run smoke | smoke executed | reason |
| --- | ---: | ---: | ---: | --- |
| B39 | false | false | false | candidate blocks inventoried, but no verified safe physical bus terminal wiring rule |
| B26 | false | false | false | candidate blocks inventoried, but no verified safe physical bus terminal wiring rule |

The smoke runner was called only in dry-run mode for B39. It refused execution
because `safe_to_run_smoke = false`.

## Boundaries

- The source `.slx` was not modified and is not committed.
- The temporary `.slx` copies are local-only, ignored, and not committed.
- L12 was not touched or fixed.
- No GCN was trained.
- The dynamic-aware reranker was not retrained.
- No labels were exported.
- The old formal label gate remains `35 / 33 / 33`.
- The v2 candidate count remains `40`.
- This does not return to the full GCN pipeline.
- The model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- Relay proxy / handwired breaker behavior is not engineering-grade
  protection.
- Relay proxy / handwired breaker behavior is not engineering-grade protection.

## Next Step

Manual Simulink review is needed to identify a verified physical bus injection
point for B39 or B26. If a later temporary lab smoke succeeds with voltage,
speed, and angle extraction, bus-fault candidate labels can be exported in a
separate round. Until then, do not train GCN or the dynamic-aware reranker from
these bus-fault candidates.

## GUI Manual Checklist Follow-Up

A follow-up adds only manual GUI review material:

- `docs/ieee39_bus_fault_gui_manual_checklist.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B39.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B26.json`
- `scripts/gcn_search/collect_ieee39_bus_fault_manual_review.py`

This follow-up does not run Simulink, does not modify `.slx`, does not commit
temporary `.slx`, does not fix L12, does not train GCN, does not retrain the
reranker, and does not export labels. The first default template consolidation
was conservative; after human GUI review, B39 now records
`human_verified_injection_point = true` and
`safe_to_run_smoke_recommendation = true`.

B39 now has a human-verified temporary injection point, but B39 is still not
smoke success. B26 remains unverified. The old formal gate remains `35 / 33 /
33`, and the v2 candidate count remains `40`.

The B39 manual evidence is recorded in
`docs/ieee39_bus_fault_b39_manual_review_result.md`. The consolidation
recommendation is `manual_review_supports_next_round_inventory_update`, which
means the next round may prepare temporary B39 smoke. It does not mean this
round ran smoke or exported labels.

## B39 Human Readiness Gate

The next inventory/readiness step adds a separate human-readiness layer for
B39:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.md`

This layer is based on the human GUI review and does not overwrite the
conservative MATLAB automatic inventory. The MATLAB inventory may still keep
`safe_to_run_smoke = false` because automatic physical wiring was not proven.

The temp-lab smoke runner was called only in dry-run readiness mode with this
human-readiness file. It wrote:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.md`

The dry-run result is `ready_for_next_round_temp_smoke`, with
`actual_simulink_run = false`, `smoke_success = false`,
`labels_exported = false`, `gcn_trained = false`, and
`reranker_retrained = false`. The old formal gate remains `35 / 33 / 33`, and
the v2 candidate count remains `40`.
