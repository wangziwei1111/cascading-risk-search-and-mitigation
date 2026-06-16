# IEEE39 V2 Plus All Bus-Fault No-Training Composition Review

This round is a no-training composition review of the latest 79-row IEEE39
v2-plus-all-bus-fault candidate dataset.

## Boundary

- This round did not run Simulink.
- This round did not run actual smoke.
- This round did not export labels.
- This round did not train GCN.
- This round did not retrain the reranker.
- This round did not run a GCN usefulness audit.
- This round did not run preview training.

## Result

- combined candidate count: `79`
- bus-fault candidate count: `39`
- all B1-B39 have bus-fault candidate: `True`
- missing bus-fault buses: `[]`
- duplicate scenario ids: `[]`
- duplicate label ids: `[]`
- unstable_flag false buses: `['B1']`
- old formal gate: `35 / 33 / 33`
- L12 excluded: `True`
- NF06 provenance warning preserved: `True`

All bus-fault labels remain candidate_not_formal_label entries, not formal
labels. B39/B26 remain existing candidate labels, not formal labels. B1 has
`unstable_flag=false`; this is a low-risk/stable compact marker, not a quality
failure.

The model remains phasor_RMS, not EMT. generator_speed_proxy is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.

Post-fault compact dynamic measurements must not be used as primary GCN inputs;
otherwise target-feature leakage risk remains. Future audit must use a
no-dynamic-measurement feature set, label-family holdout, bus-fault holdout,
and leave-one-bus-fault-out checks.

Recommended next step: `run v2-plus-all-bus-fault preview/no-leakage comparison in a separate round, not GCN training`.
