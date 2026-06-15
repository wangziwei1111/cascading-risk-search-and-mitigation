# IEEE39 Non-Line-Trip Fault Type Expansion

## Purpose

The current IEEE39 compact dynamic-label set is much stronger than before for
single-line trips: it has 35 training-ready labels, including 33 handwired
single-line trip labels. However, the fault type is still narrow. Most labels
come from line-trip behavior, so a dynamic-aware reranker may learn patterns
that work for that disturbance family but do not generalize to other physical
events.

This round prepares non-line-trip fault types. It does not create new training-ready labels and it does not retrain the dynamic-aware reranker.

## Current Capability Audit

The existing MATLAB scripts already support three useful pieces:

- `configure_ieee39_three_phase_fault_case.m` can configure the existing
  `Fault (Three-Phase)` block with `fault_start_s` and `fault_clear_s`.
- `run_ieee39_fault_test_suite.m` can run the existing
  `three_phase_fault_clear` case.
- `run_ieee39_fault_test_suite.m` can run the existing `relay_trip_test` basic
  relay proxy case.

The current scripts do not expose a generic target-bus selector for arbitrary
bus faults. Load-step, generator-trip / mechanical-power-step, and
bus-voltage-reference events are therefore marked `manual_required` or future
work until a safe Simulink/MATLAB injection point is verified.

## Generated Planning Artifacts

- taxonomy JSON:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_fault_taxonomy.json`
- taxonomy Markdown:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_fault_taxonomy.md`
- scenario manifest CSV:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_scenario_manifest.csv`
- scenario manifest JSON:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_scenario_manifest.json`
- feasibility report:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_feasibility_report.md`
- dry-run command plan:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_dry_run_commands.txt`

## Recommended First Batch

The recommended first smoke-test candidates are:

- `NF01`: baseline existing three-phase fault-clear case.
- `NF02`: existing fault block with 0.05 s clearing duration.
- `NF03`: existing fault block with 0.08 s clearing duration.
- `NF04`: existing fault block with 0.10 s clearing duration.
- `NF06`: existing basic relay proxy case.

The duration-sweep cases are intentionally marked as configuration-ready but
not final suite-grade labels. The current suite has a fixed
`three_phase_fault_clear` row, so a dedicated duration-aware smoke runner should
be used before exporting them as labels.

## Boundary Rules

- This round did not run Simulink.
- No `.slx` file was modified.
- No Simscape physical wiring was modified.
- L12 was not fixed and remains excluded.
- No dynamic-aware reranker retraining was run.
- The existing training-ready label count remains unchanged.
- These planning rows must not be merged into the dynamic-label CSV until each
  scenario passes the same compact measurement and quality gates.
- The model remains `phasor_RMS`, not EMT.
- Plain wording: phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker workflow is pilot breaker-like validation, not
  engineering-grade protection.
- Plain wording: pilot breaker-like validation, not engineering-grade protection.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, full timeseries, or large checkpoints.

## Why This Matters

The stricter dynamic-aware comparison showed that target-feature leakage is a
real risk: performance drops when compact dynamic measurement features are
removed. Adding non-line-trip faults is the next practical way to test whether
the ranking logic captures broader physical behavior rather than only
memorizing line-trip-specific signatures.

This is scenario expansion preparation and feasibility audit only. It is not a new dynamic stability conclusion and not a final dynamic performance conclusion.

## Smoke-Test Follow-Up

A small smoke-test round has now run `NF01`, `NF02`, `NF03`, `NF04`, and `NF06`.
All five produced compact `voltage_speed_angle` measurements and are recorded
only as smoke candidates. The formal dynamic label gate remains unchanged, L12
remains excluded, and the dynamic-aware reranker was not retrained.

Details are in:

`docs/ieee39_non_line_trip_fault_smoke_tests.md`

## Candidate Label Export Follow-Up

The successful smoke candidates have now been exported into a separate
non-line-trip candidate set. The export creates a v2 combined candidate schema
with `40` rows: the existing `35` formal training-ready rows plus `5`
non-line-trip candidate rows. It does not overwrite the original formal gate.

`NF01`, `NF04`, and `NF06` are flagged in the duplicate/provenance report.
`NF06` is specifically marked `provenance_check_required = true` because its
relay proxy measurements currently match the `0.10 s` fault group.

Details are in:

`docs/ieee39_non_line_trip_label_export.md`

## Bus-Fault Smoke Feasibility Follow-Up

A follow-up bus-fault smoke feasibility round now audits truly independent different-bus three-phase fault candidates. It prioritizes B16 and B39, with B21 and B26 as fallback buses.

The current result is conservative: the existing scripts can configure timing on the existing `Fault (Three-Phase)` block, but no safe target-bus selector was found. Therefore `BF01-BF04` are recorded as not runnable yet, no Simulink execution was forced, and no new labels were exported.

This follow-up does not return to the full GCN pipeline, does not train GCN, does not retrain the reranker, does not update the label gate, and does not modify or commit source `.slx`. L12 remains excluded. The model remains phasor_RMS, not EMT; `generator_speed_proxy` is not direct frequency; relay proxy / handwired breaker is not engineering-grade protection.
