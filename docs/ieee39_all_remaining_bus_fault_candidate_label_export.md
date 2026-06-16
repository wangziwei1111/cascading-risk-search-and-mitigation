# IEEE39 All-Remaining Bus-Fault Candidate Label Export

This round is candidate-only export for the 37 IEEE39 all-remaining bus-fault
temporary smoke samples that passed batch smoke quality review.

## Boundary

- This round did not run Simulink.
- This round did not run actual smoke.
- This round exported candidate labels only.
- This round did not train GCN.
- This round did not retrain the reranker.
- This round did not run a GCN usefulness audit.
- The 37 quality-passed buses were exported as candidate labels.
- All bus-fault candidates remain candidate_not_formal_label, not formal labels.
- Old formal gate remains 35 / 33 / 33.
- L12 remains excluded.
- NF06 provenance warning is preserved.

## Result

- previous candidate count: `42`
- new all-remaining bus-fault candidates: `37`
- combined candidate count: `79`
- total bus-fault candidates: `39`
- all IEEE39 buses have bus-fault candidate: `True`
- unstable_flag false buses: `['B1']`
- new candidate buses: `B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, B12, B13, B14, B15, B17, B18, B19, B20, B21, B22, B23, B24, B25, B27, B28, B29, B30, B31, B32, B33, B34, B35, B36, B37, B38, B16`

B1 has `unstable_flag=false`, but it still passed quality review. The
`unstable_flag` value is a compact smoke threshold marker, not an export
quality criterion.

The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct
frequency. In plain text: generator_speed_proxy is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.
Post-fault compact dynamic measurements should not be used as main GCN inputs,
otherwise target-feature leakage risk remains.

## Next Step

Run v2-plus-all-bus-fault no-training composition review before any training.
Do not train GCN and do not retrain the reranker in the next check step.
