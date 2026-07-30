# IEEE118 Simulation-Efficient GCN: Phase 1

## Scope

This directory contains compact audit and retrospective hidden-label replay
results. It does not contain exhaustive labels, model predictions, or local
checkpoints.

The model remains the RTS-79 `PaperStyleRts79Gcn`. Phase 1 changes how
expensive labels are selected and how candidates are routed to exact physical
verification. It does not replace the cascade simulator or claim that a
surrogate alone is safe for operation.

## Oracle-cost audit

- graph states: 8,000
- lines: 186
- active high-fidelity target labels: 1,398,103
- active high-fidelity training labels: 1,239,452
- positive target labels: 22,045 (1.5768%)
- estimated source-builder N-2 oracle calls: 1,455,583
- separately estimated N-1 S0 oracle calls: 14,880

## Same-budget smoke

The smoke subset contains 120 training, 80 validation, and 80 test states.
Each method queried 300 of 20,823 available training labels (1.4407%).

| Method | Queried positives | Final validation AP | Final test AP |
|---|---:|---:|---:|
| random | 3 | 0.0185 | 0.0117 |
| entropy | 3 | 0.0150 | 0.0106 |
| physics-k-center | 5 | 0.1969 | 0.0799 |
| PMF-BAL | 9 | 0.1969 | 0.0799 |

PMF-BAL found more rare positives at the same label budget. Its incremental
training did not improve the retained first-round validation checkpoint. The
experiment is too small and too lightly trained to establish final
superiority.

The PMF-BAL RCSV smoke selected 80.1799% of test candidates for exact
verification and captured only 81.6216% of test positives. This is not
reliable enough and does not reduce online physical verification enough for a
deployment claim.

## Five-seed paired smoke

| Method | Queried positives | Validation AP | Test AP |
|---|---:|---:|---:|
| random | 3.8 +/- 2.3 | 0.0321 +/- 0.0157 | 0.0251 +/- 0.0155 |
| entropy | 12.8 +/- 12.3 | 0.0535 +/- 0.0463 | 0.0361 +/- 0.0277 |
| physics-k-center | 5.2 +/- 0.4 | 0.1108 +/- 0.0493 | 0.0540 +/- 0.0137 |
| PMF-BAL | 11.2 +/- 4.0 | 0.1223 +/- 0.0397 | 0.0582 +/- 0.0126 |

PMF-BAL has the strongest mean AP in this small paired pilot, but its margin
over physics-k-center is not yet conclusive. Its risk-controlled selector
still verifies 81.3050% of test candidates on average while capturing only
90.5946% of positives.

## Reproduction

```powershell
python src/gcn_search/ieee118/audit_ieee118_gcn_oracle_cost.py `
  --dataset-npz results/gcn_search/ieee118_n1_residual_scaleup/paper_8000_residual/ieee118_residual_reachable_gcn_dataset.npz `
  --output-dir results/gcn_search/ieee118_simulation_efficient_gcn

python src/gcn_search/ieee118/run_ieee118_active_label_replay.py `
  --dataset-npz results/gcn_search/ieee118_n1_residual_scaleup/paper_8000_residual/ieee118_residual_reachable_gcn_dataset.npz `
  --acquisition-mode pmf_bal `
  --initial-labels 200 `
  --query-batch-size 100 `
  --rounds 2 `
  --epochs-per-round 2 `
  --ensemble-members 2 `
  --max-train-states 120 `
  --max-validation-states 80 `
  --max-test-states 80 `
  --output-dir results/gcn_search/ieee118_simulation_efficient_gcn/pmf_bal_smoke
```

The replay reveals labels that already exist in the local exhaustive dataset.
A prospective experiment must call the cascade oracle on demand and count
every exact simulation.
