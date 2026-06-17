# IEEE39 GCN Audit Evidence Diagnosis

This round is evidence diagnosis only.

It does not train GCN.
It does not rerun the formal audit.
It does not run Simulink.
It does not export labels.
It does not retrain the reranker.
It does not save a production model.

## Core Finding

The current audit evidence does not support GCN usefulness over simpler
baselines yet. This is not a final proof against GCN.

## GCN vs Baseline Gap

- bus_fault_holdout GCN-baseline RMSE gap: `0.5811123249978067`
- LOBO GCN-baseline RMSE gap: `0.023432265101873434`
- no-dynamic LOBO GCN-baseline RMSE gap: `0.023432265101873434`

## B1 Diagnosis

B1 true stress is `0.19602585950733364`. GCN predicted
`0.5078984498977661` with error
`0.31187259039043247` and unstable probability
`1.0`. This is an overconfident stable-marker
failure case.

## NF06 Sensitivity

NF06 changes GCN RMSE but does not change the conclusion:

- include NF06 GCN-baseline gap: `0.5811123249978067`
- exclude NF06 GCN-baseline gap: `0.358279246002721`

## Graph Construction Diagnosis

The current GCN uses candidate rows as graph nodes. Its dense adjacency is built
from equality of categorical fields, not from physical bus-branch electrical
topology. Message passing is therefore real, but may mostly propagate tabular
category information. `target_bus` enters as one-hot input and also contributes
to graph edges.

## Likely Root Causes

- dataset too small for current GCN parameterization
- graph construction may not expose useful topology variation
- no-leakage input features may be too weak for GCN
- bus_fault_holdout is distribution shift
- target_bus encoding memorization risk remains
- B1 stable marker is hard / overconfident classification
- NF06 sensitivity changes GCN RMSE but not conclusion
- baseline is stronger under current feature set

## Recommended Improvement Plan

- simplify GCN architecture / reduce parameters
- add topology-aware no-leakage features
- build true contingency graph representation
- add electrical static pre-fault features if available
- separate regression and classification heads more carefully
- add calibration / class imbalance handling for unstable_flag
- add leave-one-bus diagnostics before rerun
- compare GCN against target-bus-only and topology-only more explicitly
- consider non-GCN graph baselines such as GraphSAGE/GAT only after feature construction is fixed
- do not rerun reranker until GCN audit evidence improves

## Measurement Boundary

- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
- `final_engineering_conclusion = false`
- `should_deploy_model = false`
- `should_retrain_reranker_now = false`
