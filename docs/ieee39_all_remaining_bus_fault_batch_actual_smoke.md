# IEEE39 All-Remaining Bus-Fault Batch Actual Smoke

This round is batch actual smoke for the 37 readiness-passed IEEE39 bus-fault
temporary local copies. Actual Simulink smoke was run, but this round did not
export labels, did not train GCN, did not retrain the reranker, and did not run
a GCN usefulness audit.

## Result

- total targets: `37`
- smoke attempted: `37`
- simulation success: `37`
- simulation failed: `0`
- timeout: `0`
- unstable_flag true count: `36`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

Even if a smoke run succeeded, it is only temporary smoke evidence. The 37 new
targets are still not candidate labels. The next required step is smoke quality
review for successful buses. Failed or timeout buses cannot enter quality
review before diagnosis.

B16 special handling is preserved, and the old B16 fault was not moved.
B39/B26 remain existing candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.

## Follow-Up Quality Review

A later review-only step checked the already generated smoke reports. That
quality review did not run Simulink, did not run actual smoke, did not export
labels, did not train GCN, did not retrain the reranker, and did not run a GCN
usefulness audit.

The review passed all 37 smoke reports for a later candidate-only export round.
This still does not make the 37 targets candidate labels in the current round.
The next safe action is candidate-only export in a separate round, without
training.

## Candidate-Only Export Follow-Up

A later candidate-only export round registered the 37 quality-passed bus-fault
smoke samples. It still did not run Simulink, did not run actual smoke, did
not train GCN, did not retrain the reranker, and did not run a GCN usefulness
audit. The combined candidate count is now 79, and all B1-B39 buses have
bus-fault candidates, but these labels are candidate_not_formal_label entries.
