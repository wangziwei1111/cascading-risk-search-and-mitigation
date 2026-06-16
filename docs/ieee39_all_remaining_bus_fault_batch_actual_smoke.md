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
