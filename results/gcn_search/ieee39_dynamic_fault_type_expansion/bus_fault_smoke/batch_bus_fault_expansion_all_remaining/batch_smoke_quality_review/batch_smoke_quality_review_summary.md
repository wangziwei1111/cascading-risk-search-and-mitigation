# IEEE39 All-Remaining Bus-Fault Batch Smoke Quality Review

This round is batch smoke quality review. It did not run Simulink, did not run
actual smoke, did not export labels, did not train GCN, did not retrain the
reranker, and did not run a GCN usefulness audit.

## Result

- total smoke reports reviewed: `37`
- quality review passed: `37`
- quality review failed: `0`
- candidate export eligible next round: `B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15, B17, B18, B19, B20, B21, B22, B23, B24, B25, B27, B28, B29, B30, B31, B32, B33, B34, B35, B36, B37, B38, B16`
- blocked buses: `none`
- unstable_flag true count: `36`
- unstable_flag false buses: `B1`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

Quality pass only means the bus can enter a later candidate-only export round.
The 37 new targets are still not candidate labels in this round. B39/B26 remain
existing candidate labels, not formal labels.

The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.
Post-fault compact dynamic measurements should not be used as main GCN inputs,
otherwise target-feature leakage can occur.

Recommended next step: `export candidate labels for quality-passed buses in a separate round, without training`.
