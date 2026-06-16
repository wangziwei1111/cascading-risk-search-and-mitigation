# IEEE39 Batch Bus-Fault Gate Sequence

This gate sequence applies independently to each target bus. Batch wiring is
allowed, but every bus must still pass its own evidence and quality checks.

## Required Sequence

1. manual connection evidence
2. manual evidence consolidation
3. readiness dry-run
4. actual temporary smoke
5. smoke quality review
6. candidate label export
7. no-training composition review
8. preview/no-leakage comparison
9. consider GCN usefulness audit only after the above gates

## Rules

- A failed bus must not block unrelated buses.
- A failed bus must not be mixed into candidate labels.
- A not-verified bus must not be marked safe_to_run_smoke.
- Quality review must not be skipped before export.
- This round does not run Simulink, does not export labels, does not train GCN,
  and does not run a GCN usefulness audit.
