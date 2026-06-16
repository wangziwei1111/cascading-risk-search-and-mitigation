# IEEE39 All-Remaining Bus-Fault Batch Readiness Dry-Run

This round is a batch readiness dry-run. It is not actual smoke, and no
simulation was run. It does not export labels, does not train GCN, does not
retrain the reranker, and does not run a GCN usefulness audit.

## Result

- total targets: `37`
- readiness checked: `37`
- ready for next-round actual smoke: `37`
- blocked before smoke: `0`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

Only readiness-passed buses can enter the next actual smoke round. The 37 new
targets are still not candidate labels and are still not smoke success. B16
special handling is preserved, and the old fault was not moved.

B39/B26 remain existing candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.
