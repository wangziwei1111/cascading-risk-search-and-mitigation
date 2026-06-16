# V2 Plus All Bus-Fault Composition Review

- review scope: `no_training_composition_review`
- total candidate rows: `79`
- row count check passed: `True`
- total bus-fault candidates: `39`
- all B1-B39 have bus-fault candidate: `True`
- missing bus-fault buses: `[]`
- duplicate scenario ids: `[]`
- duplicate label ids: `[]`
- unstable_flag false buses: `['B1']`
- composition review passed: `True`

This review did not run Simulink, did not export labels, did not train GCN, did
not retrain the reranker, and did not run a GCN usefulness audit.
