# PIO-GCN Hard Negative Analysis

## Purpose

This analysis checks why the learned path reranker still makes mistakes after improving Top-100 and Top-200 recall.

Output:

```text
results/gcn_search/path_reranker_hard_negative_mining/
```

## Main Findings

The learned MLP reranker leaves very few critical paths outside Top-200 in the 5-seed preliminary result. Its remaining hard negatives are mostly paths with high physical stress features: they look dangerous by loading, relay margin, or LODF-style indicators, but the full cascade does not produce load shedding.

## Diagnosis

- Missed critical paths are no longer mainly a PIO-GCN ranking problem; the learned model has already pulled most positives forward.
- Hard negatives tend to be physically stressful but survivable paths.
- More topology-aware features may help distinguish “high stress but recoverable” from “high stress and load shedding.”
- Useful next features include topology distance, islanding risk, island boundary indicators, and richer first-outage stress descriptors.
- More seeds are needed before treating the learned reranker result as robust.

## Next Step

The next research step should not simply add more hand-written weights. It should expand the path-level dataset, add topology/islanding features, and test whether the learned reranker generalizes to more RTS-79 operating scenarios and synthetic renewable perturbations.
