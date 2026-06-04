# Hard Negative Mining Recommendations

## Missed Critical Paths

Missed critical paths outside Top-100 have mean PIO score 0.5691, mean paper score 0.5039, and mean max loading ratio 0.8394.

## Hard Negatives

Hard negatives concentrate around first lines L05, L27, L07, L21, L04. Their mean max loading ratio is 0.9045.

## Diagnosis

- The learned reranker greatly reduces missed critical paths compared with rule-based rerank.
- Remaining hard negatives are mostly physically stressful paths that look dangerous by loading and relay-risk features but do not lead to load shedding in the full cascade.
- Additional features that may help are topology distance, explicit islanding risk, and more detailed first-outage stress descriptors.
- More training seeds are still needed before treating this as a final result.
- A path-level GNN may be useful later, but the current compact learned reranker already shows that path-level supervision is a strong direction.
