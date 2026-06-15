# IEEE39 Bus-Fault Smoke Feasibility

## Purpose

This round is the first step toward truly independent non-line-trip fault
types. It focuses only on different-bus three-phase fault smoke candidates:

- `BF01`: B16 three-phase bus fault candidate.
- `BF02`: B39 three-phase bus fault candidate.
- `BF03`: B21 fallback bus fault candidate.
- `BF04`: B26 fallback bus fault candidate.

This round does not return to the full GCN pipeline, does not train GCN, does
not retrain the dynamic-aware reranker, does not update the label gate, and does
not export new labels.

Plain boundary wording: this round does not retrain and does not export labels.

## Feasibility Result

The audit found that existing scripts can configure timing on the existing
`Fault (Three-Phase)` block, but no safe target-bus selector is currently
available for moving that fault to B16, B39, B21, or B26.

Therefore:

- `scenario_ids_requested = BF01, BF02, BF03, BF04`
- `scenario_ids_runnable = none`
- `scenario_ids_successful = none`
- `scenario_ids_failed = BF01, BF02, BF03, BF04`
- `scenario_ids_timeout = none`

These rows are skipped smoke candidates, not failed physical simulations.

## Outputs

- feasibility report:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_injection_feasibility.json`
- feasibility markdown:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_injection_feasibility.md`
- manifest:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_scenario_manifest.csv`
- smoke summary:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_test_summary.csv`
- smoke report:
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_test_report.json`

## Boundaries

- No Simulink simulation was executed because no bus-specific scenario was
  currently runnable.
- No source `.slx` file was modified or committed.
- L12 remains excluded.
- The old formal gate remains `35 / 33 / 33`.
- The v2 candidate count remains `40`.
- Bus-fault smoke candidates are not formal labels.
- The model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- relay proxy / handwired breaker is not engineering-grade protection.

## Next Step

Verify a safe bus-fault injection point on a temporary lab copy. If a bus fault
smoke case then succeeds with `measurement_extraction_status =
voltage_speed_angle` and `frequency=generator_speed_proxy`, export bus-fault
candidate labels in a separate round. If it does not succeed, do not force
training.

## Temporary Lab Follow-Up

A follow-up temporary-lab workflow now prioritizes `B39` and uses `B26` as the
fallback target. The workflow copies the source `.slx` only into an ignored
local lab directory, inventories nearby target-bus blocks, and refuses smoke
simulation unless a verified safe physical bus terminal wiring rule is found.

Current result:

- `B39`: candidate blocks were inventoried, but no safe injection point was
  verified; `safe_to_run_smoke = false`.
- `B26`: candidate blocks were inventoried, but no safe injection point was
  verified; `safe_to_run_smoke = false`.

No source `.slx` was modified or committed, no temporary `.slx` was committed,
no labels were exported, no GCN was trained, and the dynamic-aware reranker was
not retrained.

## GUI Manual Checklist Follow-Up

The next step is a human GUI review checklist, not a Simulink run. The checklist
records B39/B26 candidate blocks and requires a human reviewer to fill the
manual review template before any later temporary smoke attempt.

B39 now has a human-verified temporary injection point, and B26 remains
unverified. B39 is not smoke success. The updated consolidation recommendation
is `manual_review_supports_next_round_inventory_update`, meaning the next round
may prepare a temporary B39 smoke run. No `.slx` was modified, no temporary
`.slx` was committed, no labels were exported, no GCN was trained, and the
dynamic-aware reranker was not retrained. The old formal gate remains `35 / 33
/ 33`, and the v2 candidate count remains `40`.
