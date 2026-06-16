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
| B26 | true | false | false | human-verified temporary injection point; dry-run readiness only, not smoke success |

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
- The v2-plus-B39 count remains `41`.
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
smoke success. B26 was later rechecked and now has a human-verified injection
point, but B26 is still not smoke success. The old formal gate remains `35 /
33 / 33`, and the v2-plus-B39 count remains `41`.

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

## Actual B39 Temporary Smoke

The actual B39 temporary smoke was run after the readiness gate. It used only
the ignored local temporary copy and wrote:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.md`

The smoke result is `simulation_success = true`,
`measurement_extraction_status = voltage_speed_angle`, and
`training_ready_candidate_smoke = true`. The signal source summary includes
`frequency=generator_speed_proxy`.

This remains a temporary smoke candidate only. `labels_exported = false`,
`gcn_trained = false`, `reranker_retrained = false`, the source `.slx` was not
modified, L12 was not touched, the old formal gate remains `35 / 33 / 33`, and the v2
candidate count remains `40`.

## B26 Manual Verification Preparation Follow-Up

After the B39 v2-plus-B39 preview interpretation, B26 is prepared as the next
manual GUI target. This round does not run Simulink, does not submit `.slx`,
does not train GCN, does not retrain the reranker, and does not export labels.

- B26 was still unverified before the later rename recheck.
- B26 is not smoke success.
- B26 candidate label has not been exported.
- `human_verified_injection_point = false`
- `safe_to_run_smoke_recommendation = false`
- old formal gate remains `35 / 33 / 33`
- v2-plus-B39 count remains `41`

Manual commands are available at:

`results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_gui_check_commands.md`

## B26 Manual Review Evidence Result

B26 manual review evidence was collected from the temporary local copy. This
round only performed structure inspection and Update Diagram; it did not run
smoke, did not export labels, did not train GCN, and did not retrain the
reranker.

The checked model contains an observed B26 parallel fault block,
`Grid/Fault (Three-Phase)1`, connected to `Grid/B25 to B26`, `Grid/Bus26_1`,
and `Grid/Bus26_2`. Update Diagram passed. However, the required named block
`Grid/Fault_B26_TEMP` was not found, so B26 remains unverified and is not safe
to run smoke in this round.

After the user renamed the temporary fault block, B26 was rechecked. The
temporary copy now contains `Grid/Fault_B26_TEMP`, connected in parallel to
`Grid/B25 to B26`, `Grid/Bus26_1`, and `Grid/Bus26_2`. Update Diagram passed.
B26 now has a human-verified injection point and can proceed to a separate
readiness gate in the next round. This is still not smoke success and not a
candidate label.

## B26 Human Readiness Dry-Run

B26 readiness was then checked in dry-run mode only. The dry-run wrote:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_dry_run_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_dry_run_readiness.md`

The dry-run status is `ready_for_next_round_temp_smoke`. It did not run actual
Simulink smoke, did not submit `.slx`, did not modify source `.slx`, did not
export labels, did not train GCN, and did not retrain the reranker. B26 is still
not smoke success and is still not a candidate label. B39 remains a candidate
label, not a formal label.

## Actual B26 Temporary Smoke

After the B26 readiness gate, one actual B26 temporary smoke was run using only
the ignored local temporary copy. It wrote B26-specific files and did not
overwrite the B39 smoke artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_report.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_report.md`

The smoke result is `simulation_success = true` and
`measurement_extraction_status = voltage_speed_angle`, with
`frequency=generator_speed_proxy` in the signal source summary. B26 is still
not a formal label and no B26 candidate label was exported in this round.

## B26 Smoke Quality Review

The already completed B26 temporary smoke was then reviewed in a quality-only
round. This review did not run Simulink, did not submit `.slx`, did not modify
source `.slx`, did not export labels, did not train GCN, and did not retrain
the reranker.

The B26 quality review records:

- `quality_review_passed_for_candidate_export = true`
- `simulation_success = true`
- `measurement_extraction_status = voltage_speed_angle`
- `signal_source_has_frequency_proxy = true`
- `labels_exported = false`
- `gcn_trained = false`
- `reranker_retrained = false`
- old formal gate remains `35 / 33 / 33`
- v2-plus-B39 count remains `41`

B26 remains temporary bus-fault evidence, not a formal label. B26 candidate
label export is left to a separate later round. B39 remains
`candidate_label_not_formal`. `phasor_RMS` is not EMT,
`generator_speed_proxy` is not direct frequency, and temporary bus-fault
injection is not engineering-grade protection.

Artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.md`

## All-Remaining Manual Wiring Package

A later preparation-only round creates an all-remaining manual wiring package.
It does not run Simulink, does not run smoke, does not export labels, does not
train GCN, and does not retrain the reranker.

The package covers normal targets `B1-B15`, `B17-B25`, and `B27-B38`, plus
special target `B16`. B39 and B26 are excluded because they already have
quality-reviewed candidate labels. Each new target must use its own ignored
temporary local copy and must pass manual evidence, readiness, smoke, quality,
export, composition review, and preview/no-leakage gates before any later GCN
usefulness audit.
