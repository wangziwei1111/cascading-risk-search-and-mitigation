# IEEE39 All-Remaining Bus-Fault Batch Smoke Quality Review

This round is a batch smoke quality review for the 37 IEEE39 bus-fault
temporary smoke outputs from the previous actual-smoke round.

## Boundary

- This round did not run Simulink.
- This round did not run actual smoke.
- This round did not export labels.
- This round did not train GCN.
- This round did not retrain the reranker.
- This round did not run a GCN usefulness audit.
- The 37 new targets are still not candidate labels.
- Quality pass only means a bus can enter candidate-only export in a separate
  later round.
- B16 special handling is preserved, and the old B16 fault was not moved.
- B39/B26 remain existing candidate labels, not formal labels.
- Current candidate count remains 42.
- Old formal gate remains 35 / 33 / 33.

## Quality Review Result

- total smoke reports reviewed: `37`
- quality review passed: `37`
- quality review failed: `0`
- candidate export eligible next round: `B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15, B17, B18, B19, B20, B21, B22, B23, B24, B25, B27, B28, B29, B30, B31, B32, B33, B34, B35, B36, B37, B38, B16`
- blocked buses: `none`
- unstable_flag true count: `36`
- unstable_flag false buses: `B1`
- B16 quality review passed: `True`

`unstable_flag` is a compact smoke threshold marker, not a final stability
conclusion. `unstable_flag=false` does not mean the smoke quality failed; it
only means the compact threshold marker was lower for that bus.

The model is phasor_RMS, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.
Post-fault compact dynamic measurements cannot be used as main GCN inputs,
otherwise there is target-feature leakage risk.

## Next Step

If the project continues, the next round should do candidate-only export for
quality-passed buses, without training GCN and without retraining the reranker.
