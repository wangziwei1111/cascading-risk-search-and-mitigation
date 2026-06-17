# Next GCN Improvement Plan

```json
{
  "analysis_scope": "next_gcn_improvement_plan",
  "training_triggered": false,
  "reranker_retraining_triggered": false,
  "deployment_triggered": false,
  "recommended_options": [
    "simplify GCN architecture / reduce parameters",
    "add topology-aware no-leakage features",
    "build true contingency graph representation",
    "add electrical static pre-fault features if available",
    "separate regression and classification heads more carefully",
    "add calibration / class imbalance handling for unstable_flag",
    "add leave-one-bus diagnostics before rerun",
    "compare GCN against target-bus-only and topology-only more explicitly",
    "consider non-GCN graph baselines such as GraphSAGE/GAT only after feature construction is fixed",
    "do not rerun reranker until GCN audit evidence improves"
  ],
  "priority_order": [
    "fix no-leakage graph construction",
    "reduce model complexity for 79-row audit data",
    "add static electrical features that are available before fault outcomes",
    "rerun strict audit only after feature/graph changes are reviewed"
  ]
}
```
