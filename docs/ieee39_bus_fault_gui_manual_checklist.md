# IEEE39 Bus-Fault GUI Manual Checklist

## Purpose

This checklist guides a human Simulink GUI review for IEEE39 different-bus
three-phase fault injection. The priority target is `B39`; the fallback target
is `B26`.

Plain wording: this document is a manual inspection checklist only. B39 now has
a human-verified injection point, and B26 now has a human-verified injection
point after the rename recheck. This does not
mean B39 or B26 has passed smoke, does not train GCN, does not retrain the
reranker, and does not export labels.

## Model Opening Rule

- Open only the ignored local temporary copy under
  `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/`.
- Do not open and save the source generated model.
- The source model is read-only reference material.
- Temporary `.slx` files must not be committed.

## B39 Priority Candidate Blocks

- `Grid/Bus39`
- `Grid/B39 to B1`
- `Grid/B9 to B39`
- `Generators/Gen1@Bus39`
- `Grid/GB39B1F`
- `Grid/GB39B1T`
- `Grid/GB9B39F`
- `Grid/GB9B39T`

## B26 Fallback Candidate Blocks

- `Grid/Bus26_1`
- `Grid/Bus26_2`
- `Grid/B25 to B26`
- `Grid/B26 to B28`
- `Grid/B26 to B29`
- `Grid/B27 to B26`
- `Grid/GB25B26F`
- `Grid/GB25B26T`
- `Grid/GB26B28F`
- `Grid/GB26B28T`
- `Grid/GB26B29F`
- `Grid/GB26B29T`
- `Grid/GB27B26F`
- `Grid/GB27B26T`

## Manual GUI Steps

- [ ] Open the temporary copy in Simulink GUI.
- [ ] Find the target bus candidate blocks.
- [ ] Record each block type, mask type, and port type.
- [ ] Check whether the target bus exposes three-phase Simscape conserving
  ports.
- [ ] Check whether `Fault (Three-Phase)` can be connected in parallel to the
  target bus.
- [ ] Check that the original network connection is preserved after injection.
- [ ] Check whether any extra ground or electrical reference is required.
- [ ] Check that no floating ports are created.
- [ ] Check that no unintended bypass is created.
- [ ] Check that no unintended islanding or unreasonable topology is created.
- [ ] Click Update Diagram only after the structure is visually checked.
- [ ] If Update Diagram fails, record the error and do not continue to
  simulation.
- [ ] If the connection appears safe, record only
  `human_verified_injection_point = true` in the review template.
- [ ] Do not change `safe_to_run_smoke` in the MATLAB inventory during this
  round.

## Safety Conditions Before Any Future Smoke

All of the following must be true before a later round may update the inventory
and run temporary smoke:

- [ ] source `.slx` was not modified.
- [ ] temporary copy is openable.
- [ ] target bus physical terminal is clear.
- [ ] `Fault (Three-Phase)` can be connected in parallel to the target bus.
- [ ] original line or bus network connection is preserved.
- [ ] no unintended bypass is created.
- [ ] no floating ports are created.
- [ ] no unintended islanding is created.
- [ ] Update Diagram succeeds.
- [ ] `fault_start_s` and `fault_clear_s` are configurable.
- [ ] measurement signals are expected to remain available.
- [ ] human screenshot or manual evidence is recorded.

Only if every item above passes should the next round consider a temporary smoke
run. This checklist itself is not smoke success.

## Explicitly Forbidden

- Do not save the source model.
- Do not commit temporary `.slx` files.
- Do not modify the formal generated model directly.
- Do not write manual review as smoke success.
- Do not export labels.
- Do not train GCN.
- Do not retrain the reranker.
- Do not update the old formal label gate.
- Do not update the v2 candidate count.
- Do not fix or touch L12.

## Current Boundary Notes

- The old formal gate remains `35 / 33 / 33`.
- The v2-plus-B39 count remains `41`.
- B39 has a human-verified injection point.
- B39 is not smoke success.
- B26 has a human-verified injection point after the rename recheck.
- B26 is not smoke success.
- B26 is not a candidate label.
- The model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- Relay proxy / handwired breaker behavior is not engineering-grade protection.

## B26 Priority Follow-Up

After the v2-plus-B39 preview interpretation, B26 becomes the next priority
manual GUI target because B39 holdout showed weak bus-fault / fault-family
generalization. This is preparation only:

- B26 was still unverified before the later rename recheck.
- B26 is not smoke success.
- B26 candidate label has not been exported.
- Codex should not run Simulink in this preparation round.
- Codex should not train GCN or retrain the reranker in this preparation round.

The B26-specific plan is in
`docs/ieee39_b26_manual_bus_fault_verification_plan.md`.

## B26 Manual Review Evidence Result

B26 manual review evidence has been re-collected after the temporary fault
block was renamed. Update Diagram passed for the checked temporary copy, and
`Grid/Fault_B26_TEMP` is connected in parallel to the B26 physical node shared
by `Grid/B25 to B26`, `Grid/Bus26_1`, and `Grid/Bus26_2`.

- B26 is not smoke success.
- B26 candidate label has not been exported.
- GCN was not trained.
- The reranker was not retrained.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.

The next step is a separate B26 readiness gate before any temporary smoke. See
`docs/ieee39_b26_manual_bus_fault_review_result.md`.

## B26 Readiness Dry-Run

B26 now has a separate readiness dry-run result:

- `docs/ieee39_b26_temp_smoke_readiness.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_dry_run_readiness.json`

The status is `ready_for_next_round_temp_smoke`. This is not actual Simulink
smoke success and is not a candidate label export.

## Actual B26 Temporary Smoke Follow-Up

The actual B26 temporary smoke was later run from the ignored temporary local
copy. It produced B26-specific smoke outputs and did not overwrite the B39
smoke artifacts. The smoke succeeded as a temporary smoke candidate, but B26 is
still not a formal label and no B26 candidate label was exported in that round.
