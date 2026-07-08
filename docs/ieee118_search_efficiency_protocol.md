# IEEE118 Search-Efficiency Protocol

This document defines the first IEEE118 search-efficiency smoke protocol for the `flow_scaled=8.00`, `min-rate-a=1.0` stress setting. It is a pipeline validation stage, not a final tuned GCN / PIO-GCN result.

Important correction: `GCN_smoke` is only a lightweight NumPy/logistic pipeline sanity check. It is not the original RTS-79 GCN and must not be reported as the main IEEE118 GCN result. Formal GCN results should reuse `PaperStyleRts79Gcn` from `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py` through `src/gcn_search/ieee118/train_ieee118_with_original_rts79_gcn.py` and should be named `RTS79_GCN_reused_on_IEEE118` or `RTS79_PIO_GCN_reused_on_IEEE118`.

## Ground Truth

- Case: IEEE118
- Thermal limit mode: `flow_scaled`
- Flow-limit scale: 8.00
- Minimum `RATE_A`: 1.0 MW
- Seed: 20260708
- Ordered N-2 search space: 34,410 paths
- Critical paths: 1,859
- Relay-cascade paths: 1,659

Local inputs:

```text
results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708/ieee118_fulltruth_summary.csv
results/gcn_search/ieee118_flow_scaled_800_step2_state/ieee118_step2_state_samples.csv
```

These large CSVs are local-only and are not committed.

## Ranking Methods

- `random`: random permutations of all ordered paths. Report mean and standard deviation over at least 10 random seeds.
- `line_order`: deterministic ordered path enumeration, e.g. `L001->L002`, `L001->L003`, ...
- `LODF_yP`: IEEE118 adaptation of the RTS-79 LODF physical vulnerability baseline. It ranks first-line candidates by yP, then ranks second-line candidates from `S1(first_line)` by yP.
- `GCN_smoke`: lightweight smoke scorer trained on Step2-State graph-derived scalar features. It excludes label/leakage columns, is not the original RTS-79 GCN, and must remain a pipeline sanity check only.
- `RTS79_PIO_GCN_reused_on_IEEE118`: formal reuse path that converts IEEE118 Step2-State samples to the original RTS-79 GCN tensor contract and calls the original `PaperStyleRts79Gcn` model class.

## Metrics

For each ranking and budget `K`, report:

- Recall@K for critical paths: critical hits in Top-K divided by 1,859.
- Recall@K for relay-cascade paths: relay-cascade hits in Top-K divided by 1,659.
- Precision@K: critical hits in Top-K divided by K.
- Critical hit count @K.
- Relay-cascade hit count @K.
- Captured total load shed MW.
- Captured relay-cascade load shed MW.
- Search budget ratio: K / 34,410.

Budgets include fixed and percentage K:

- Fixed: 50, 100, 200, 500, 1000, 2000, 5000.
- Percentage: 0.5%, 1%, 2%, 5%, 10% of 34,410.

Do not report only Recall@100: `100 / 34,410` is only about 0.29% of the IEEE118 ordered N-2 search space.

## Smoke Results

The first smoke run used the full local Step2-State CSV for the lightweight scorer and evaluated against the complete 34,410-path full truth.

Selected results:

| method | K | Recall critical | Recall relay | Precision@K | Critical hits | Relay hits | Captured shed MW |
|---|---:|---:|---:|---:|---:|---:|---:|
| random mean | 100 | 0.002797 | 0.002712 | 0.052000 | 5.2 | 4.5 | 168.922633 |
| line_order | 100 | 0.003228 | 0.003617 | 0.060000 | 6 | 6 | 179.807773 |
| LODF_yP | 100 | 0.008607 | 0.009644 | 0.160000 | 16 | 16 | 419.826021 |
| GCN_smoke | 100 | 0.019903 | 0.022303 | 0.370000 | 37 | 37 | 949.793722 |
| random mean | 500 | 0.013986 | 0.014165 | 0.052000 | 26.0 | 23.5 | 841.463365 |
| line_order | 500 | 0.012910 | 0.014467 | 0.048000 | 24 | 24 | 796.025684 |
| LODF_yP | 500 | 0.031737 | 0.035564 | 0.118000 | 59 | 59 | 1584.007081 |
| GCN_smoke | 500 | 0.084454 | 0.094635 | 0.314000 | 157 | 157 | 5263.582805 |
| random mean | 1000 | 0.029317 | 0.029656 | 0.054500 | 54.5 | 49.2 | 1775.420275 |
| line_order | 1000 | 0.030124 | 0.033755 | 0.056000 | 56 | 56 | 1820.987196 |
| LODF_yP | 1000 | 0.069392 | 0.068113 | 0.129000 | 129 | 113 | 3334.977056 |
| GCN_smoke | 1000 | 0.125874 | 0.136227 | 0.234000 | 234 | 226 | 9852.978109 |

These results only show that the evaluation chain is wired correctly and that learned Step2-State features are promising. They are not final IEEE118 GCN / PIO-GCN claims.

## Commands

Train smoke scorer:

```bash
python src/gcn_search/ieee118/train_ieee118_gcn_smoke.py \
  --step2-csv results/gcn_search/ieee118_flow_scaled_800_step2_state/ieee118_step2_state_samples.csv \
  --target label_critical \
  --epochs 8 \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_gcn_smoke
```

Evaluate:

```bash
python src/gcn_search/ieee118/evaluate_ieee118_search_efficiency.py \
  --fulltruth-csv results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708/ieee118_fulltruth_summary.csv \
  --gcn-predictions-csv results/gcn_search/ieee118_flow_scaled_800_gcn_smoke/gcn_smoke_predictions.csv \
  --include-lodf \
  --random-seeds 0 1 2 3 4 5 6 7 8 9 \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_gcn_smoke
```

## Scope

This stage does not train a final GCN or PIO-GCN model. It also does not perform final search-efficiency evaluation. Next steps should add stronger graph models, train/validation/test design, ablations, and comparison against `LODF_yP`, random, and `line_order` under this fixed protocol.
