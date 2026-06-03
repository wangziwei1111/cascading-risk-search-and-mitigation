# IEEE14 GCN-RL Integration

This integration is deliberately same-system only. The new GCN path uses PYPOWER IEEE14 scenario IDs, branch IDs, and RL evaluation outputs. It does not map legacy RTS79, IEEE39, or other-system GCN branches into the IEEE14 RL environment.

## Module Boundary

- `src/gcn_search/legacy_rts79/`: legacy reproduction code for RTS79-style GCN/path search experiments. It remains unchanged and is not used as an IEEE14 RL input.
- `src/rl_mitigation/`: current IEEE14 mitigation environment and policy evaluation stack.
- `src/gcn_search/ieee14/`: new same-system IEEE14 branch-graph risk identification module.

## Data Flow

1. `scripts/gcn_search/ieee14/generate_ieee14_risk_dataset.py`
   reads `results/rl_mitigation/ieee14/action_value_scan/{train,val,test}_action_value_scan.csv`.
2. It builds a 20-node branch graph from `rl_mitigation.cases.make_ieee14_case()`.
3. Branch-graph edges connect IEEE14 branches that share a bus.
4. GCN features contain branch metadata, initial outage masks, outage order, and load/gen scale.
5. Labels are based on the same scenario's do-nothing negative return and are assigned to the initially outaged branch nodes.
6. `scripts/gcn_search/ieee14/train_ieee14_branch_gcn.py` trains a small branch GCN and writes `results/gcn_search/ieee14/eval/test_risk_ranking.csv`.
7. `scripts/gcn_search/ieee14/evaluate_ieee14_gcn_to_rl.py` takes the GCN-ranked IEEE14 test scenarios and summarizes RL policy performance on the GCN top-K subset.

## Current Smoke Result

The selected validation checkpoint gives the following test ranking metrics:

- Spearman: 0.4717
- Pairwise order accuracy: 0.6789
- Top-10 recall: 0.4

For the GCN top-20 test subset, do-nothing mean negative return is 100.6739 versus 75.1851 on all test scenarios, showing that the IEEE14 GCN module identifies a higher-risk evaluation subset.

## RL Bridge Result

The bridge evaluates existing IEEE14 policies on the same GCN-selected test subset:

- do-nothing: mean negative return 100.6739 on GCN top-20
- safe oracle BC full: mean negative return 98.8216 on GCN top-20
- one-step oracle: mean negative return 80.0900 on GCN top-20

These are diagnostic bridge results. The GCN module ranks same-system risk scenarios; it does not yet choose RL actions or replace the policy.

## Reproduce

```powershell
E:\Scripts\python.exe -m scripts.gcn_search.ieee14.generate_ieee14_risk_dataset --config configs/gcn_search/ieee14/ieee14_gcn.yaml
E:\Scripts\python.exe -m scripts.gcn_search.ieee14.train_ieee14_branch_gcn --config configs/gcn_search/ieee14/ieee14_gcn.yaml
E:\Scripts\python.exe -m scripts.gcn_search.ieee14.evaluate_ieee14_gcn_to_rl --config configs/gcn_search/ieee14/ieee14_gcn.yaml
```

