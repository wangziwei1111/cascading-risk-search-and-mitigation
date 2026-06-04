# Path Pattern Memorization Risk

## Purpose

The learned path reranker performs very well, so it must be checked for memorization risk. The key question is whether the model is learning physical path-risk patterns or simply remembering repeated RTS-79 line-pair patterns.

## Analysis Output

```text
results/gcn_search/path_reranker_memorization_analysis/
```

Key files:

```text
repeated_path_pattern_summary.csv
line_pair_frequency_summary.csv
memorization_risk_summary.csv
recommendations.md
```

## Current Findings

| Check | Result | Interpretation |
|---|---:|---|
| Top-10 path-pattern concentration | 0.177 | The ten most frequent critical line pairs cover about 17.7% of critical labels; this is not extreme. |
| Repeated positive patterns | 54 | Some line pairs are repeatedly critical across at least three seeds. |
| Overall memorization risk | medium | No direct leakage was found, but fixed RTS-79 topology can still permit path-pattern learning. |

## What This Means

The current evidence is better than a direct leakage problem: forbidden label features were not found, and external unseen-seed validation remains strong. However, because every sample still belongs to the same RTS-79 network, the model may partly learn stable topology-specific path templates.

Therefore, the learned reranker should be reported as a strong RTS-79 preliminary result, not as final generalization evidence.

## Recommended Next Step

- Add more load and renewable scenarios.
- Test on a second benchmark grid before making stronger claims.
- Compare feature groups that remove topology identity if future datasets include explicit line-identity features.
- Keep full-truth detail files local and track only compact summaries.
