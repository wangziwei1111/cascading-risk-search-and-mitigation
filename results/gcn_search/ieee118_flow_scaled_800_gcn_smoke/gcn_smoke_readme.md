# IEEE118 Flow-Scaled 8.00 GCN Smoke Evaluation

This directory contains compact smoke outputs for the IEEE118 search-efficiency evaluation chain. It uses the local `flow_scaled=8.00`, `min-rate-a=1.0` full-truth and Step2-State datasets.

## Scope

- This is a smoke evaluation.
- It is not a final tuned GCN or PIO-GCN result.
- It does not include Simulink/MATLAB content.
- The complete full-truth CSV and 2.7GB Step2-State CSV remain local-only.

## Inputs

```text
results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708/ieee118_fulltruth_summary.csv
results/gcn_search/ieee118_flow_scaled_800_step2_state/ieee118_step2_state_samples.csv
```

## Methods

- `random`: 10 random seeds, reported as mean/std.
- `line_order`: deterministic ordered path order.
- `LODF_yP`: IEEE118 LODF physical baseline adapted from RTS-79.
- `GCN_smoke`: lightweight NumPy logistic smoke scorer over non-leaking Step2-State scalar features.

## Selected Results

| method | K | Recall critical | Recall relay | Precision@K | Critical hits |
|---|---:|---:|---:|---:|---:|
| random mean | 100 | 0.002797 | 0.002712 | 0.052000 | 5.2 |
| line_order | 100 | 0.003228 | 0.003617 | 0.060000 | 6 |
| LODF_yP | 100 | 0.008607 | 0.009644 | 0.160000 | 16 |
| GCN_smoke | 100 | 0.019903 | 0.022303 | 0.370000 | 37 |
| random mean | 1000 | 0.029317 | 0.029656 | 0.054500 | 54.5 |
| line_order | 1000 | 0.030124 | 0.033755 | 0.056000 | 56 |
| LODF_yP | 1000 | 0.069392 | 0.068113 | 0.129000 | 129 |
| GCN_smoke | 1000 | 0.125874 | 0.136227 | 0.234000 | 234 |

The smoke scorer excludes label fields including `critical`, `critical_mechanism`, `total_load_shed_mw`, `num_relay_trips`, and `max_event_loading_ratio`.
