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
