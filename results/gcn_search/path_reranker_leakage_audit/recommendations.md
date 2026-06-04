# Path Reranker Leakage Audit

## Leakage Finding

No direct forbidden input feature was found.

The high learned-reranker recall is flagged as suspiciously high, so strict held-out evaluation is required.

## Highest Feature Correlations

- lodf_score: abs(correlation) = 0.5183
- rank_in_lodf: abs(correlation) = 0.3175
- second_line_loading_ratio: abs(correlation) = 0.3078
- ensemble_score_alpha_0_75: abs(correlation) = 0.2596
- pio_score: abs(correlation) = 0.2535

## Recommendation

Report the learned reranker only together with strict held-out seed results. Current evidence can be shown to an advisor as preliminary, but not as final evidence.
