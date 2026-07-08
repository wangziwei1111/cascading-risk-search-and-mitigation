# IEEE118 Original RTS-79 GCN Results

This stage uses the IEEE118 `flow_scaled=8.00`, `min_rate_a=1.0`, seed `20260708` full-truth and Step2-State dataset. It corrects the earlier smoke-stage naming: PR #7 `GCN_smoke` is only a NumPy/logistic sanity check and is not a formal GCN result.

## Torch Environment

Default Python failed to import `torch`:

- executable: `E:\Scripts\python.exe`
- issue: `sys.exec_prefix` is `E:`, which makes PyTorch attempt a malformed DLL path such as `E:bin`
- diagnosis: environment/configuration problem, not a model-code problem

The run used the repository-adjacent virtual environment:

- executable: `C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe`
- torch: `2.11.0+cpu`
- CUDA: unavailable

The environment diagnosis is saved in:

- `results/gcn_search/ieee118_flow_scaled_800_original_rts79_gcn_eval/torch_environment_diagnosis.json`

## Data Conversion

Converter:

```bash
C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe \
  src/gcn_search/ieee118/convert_ieee118_step2_to_rts79_gcn_format.py \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_original_rts79_gcn_eval
```

Converted dataset checks:

- state samples: 186 first-line states
- line labels: 186
- ordered path samples: 34,410
- critical labels: 1,859
- relay-cascade labels: 1,659
- label leakage fields excluded from input features

## Formal Training

Training command:

```bash
C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe \
  src/gcn_search/ieee118/train_ieee118_with_original_rts79_gcn.py \
  --dataset-npz results/gcn_search/ieee118_flow_scaled_800_original_rts79_gcn_eval/ieee118_rts79_gcn_dataset.npz \
  --path-index-csv results/gcn_search/ieee118_flow_scaled_800_original_rts79_gcn_eval/ieee118_rts79_gcn_path_index.csv \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_original_rts79_gcn_eval \
  --epochs 20 \
  --seed 20260708
```

Formal model source:

- `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`
- `PaperStyleRts79Gcn`

No new GCN model structure was introduced.

Validation at epoch 20:

- validation accuracy: 0.7386
- precision/hit rate: 0.1604
- recall/cover rate: 0.8786
- F1: 0.2713

## Search Efficiency

Evaluation command:

```bash
C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe \
  src/gcn_search/ieee118/evaluate_ieee118_search_efficiency.py \
  --fulltruth-csv results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708/ieee118_fulltruth_summary.csv \
  --gcn-predictions-csv results/gcn_search/ieee118_flow_scaled_800_original_rts79_gcn_eval/original_rts79_gcn_ieee118_predictions.csv \
  --gcn-method-name RTS79_GCN_reused_on_IEEE118 \
  --include-lodf \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_original_rts79_gcn_eval
```

Selected results:

| Method | K | Critical hits | Critical recall | Relay hits | Relay recall | Precision@K |
|---|---:|---:|---:|---:|---:|---:|
| random mean | 1000 | 54.5 | 0.0293 | 49.2 | 0.0297 | 0.0545 |
| line_order | 1000 | 56 | 0.0301 | 56 | 0.0338 | 0.0560 |
| LODF_yP | 1000 | 129 | 0.0694 | 113 | 0.0681 | 0.1290 |
| RTS79_GCN_reused_on_IEEE118 | 1000 | 210 | 0.1130 | 196 | 0.1181 | 0.2100 |
| LODF_yP | 5000 | 497 | 0.2673 | 453 | 0.2731 | 0.0994 |
| RTS79_GCN_reused_on_IEEE118 | 5000 | 1059 | 0.5697 | 1001 | 0.6034 | 0.2118 |

The reused original RTS-79 GCN is stronger than random, line_order, and LODF_yP in this IEEE118 smoke-to-full evaluation. It is not directly claimed to be "close to RTS-79" because topology, stress calibration, and data regime differ; this result should be reported as an IEEE118 first full formal reuse run.

## PIO-GCN Status

`RTS79_PIO_GCN_reused_on_IEEE118` is not completed in this stage. The current completed formal method is:

- `RTS79_GCN_reused_on_IEEE118`

PIO-GCN should be added only if the original RTS-79 PIO flow, including its physics losses and candidate masking protocol, is reused without replacing the model structure.

## Committed Artifacts

Compact artifacts only:

- `original_rts79_gcn_ieee118_metrics.json`
- `original_rts79_gcn_ieee118_training_log.csv`
- `original_rts79_gcn_ieee118_search_efficiency_summary.csv`
- `original_rts79_gcn_ieee118_search_efficiency_summary.json`
- `original_rts79_gcn_ieee118_curve_points.csv`
- `original_rts79_gcn_ieee118_topk_paths.csv`
- `original_rts79_gcn_ieee118_readme.md`
- `torch_environment_diagnosis.json`

Not committed:

- full raw IEEE118 full-truth CSV
- 2.7GB Step2-State CSV
- full predictions CSV
- model checkpoint
- Simulink/MATLAB artifacts
