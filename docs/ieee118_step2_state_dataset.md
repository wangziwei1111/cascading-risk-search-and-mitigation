# IEEE118 Step2-State Dataset

This stage builds IEEE118 Step2-State graph samples from the `flow_scaled=8.00`, `min-rate-a=1.0` ordered N-2 full-truth table. It prepares data for later IEEE118 GCN / PIO-GCN search-efficiency evaluation, but it does not train a GCN and does not evaluate search efficiency.

## Source Full Truth

The source full-truth table is local-only:

```text
results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708/ieee118_fulltruth_summary.csv
```

It is not committed to git. The compact audit for this full truth reports:

- Total ordered N-2 paths: 34,410.
- Converged paths: 34,410.
- Error rows: 0.
- Critical rows: 1,859.
- Critical ratio: 0.054025.
- Relay-cascade rows: 1,659.
- Relay-cascade ratio: 0.048213.

## Dataset Definition

Each sample corresponds to one second-step candidate in an ordered N-2 path:

1. Apply the first active outage and simulate protection, island handling, and redispatch to obtain `S1(first_line)`.
2. Construct bus and branch graph features from `S1(first_line)`.
3. Mark the candidate `second_line`.
4. Attach labels from the full-truth row for `first_line->second_line`.

Labels are copied from full truth. The Step2-State builder does not redefine `critical`.

The script caches `S1(first_line)` so the full dataset computes 186 first-line states and reuses them for 34,410 samples.

## Command

```bash
python src/gcn_search/ieee118/build_ieee118_step2_state_dataset.py \
  --fulltruth-csv results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708/ieee118_fulltruth_summary.csv \
  --limit-mode flow_scaled \
  --flow-limit-scale 8.00 \
  --min-rate-a 1.0 \
  --seed 20260708 \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_step2_state
```

Smoke command:

```bash
python src/gcn_search/ieee118/build_ieee118_step2_state_dataset.py \
  --fulltruth-csv results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708/ieee118_fulltruth_summary.csv \
  --limit-mode flow_scaled \
  --flow-limit-scale 8.00 \
  --min-rate-a 1.0 \
  --seed 20260708 \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_step2_state_smoke \
  --max-first-lines 2 \
  --max-samples 10
```

## Full Dataset Status

The full local run produced:

- Samples: 34,410.
- Unique first lines: 186.
- Critical samples: 1,859.
- Critical ratio: 0.054025.
- Relay-cascade samples: 1,659.
- Relay-cascade ratio: 0.048213.
- First-state cache misses: 186.
- First-state cache hits: 34,224.

The full `ieee118_step2_state_samples.csv` is large and remains local-only. This PR commits only the script, tests, documentation, smoke artifact, schema, and metadata.

## Outputs

Full local output directory:

```text
results/gcn_search/ieee118_flow_scaled_800_step2_state/
```

Expected files:

- `ieee118_step2_state_samples.csv`
- `ieee118_step2_state_metadata.json`
- `ieee118_step2_state_feature_schema.json`
- `ieee118_step2_state_readme.md`

Each sample includes path labels and JSON-encoded node, edge, and path features. The schema file documents the feature names.

## Scope

`original_rate_a` remains the MATPOWER fidelity baseline. `flow_scaled=8.00`, `min-rate-a=1.0` is the IEEE118 OPA-style overload relay stress-test ground-truth setting used here. The next stage is to convert or consume this Step2-State data for IEEE118 GCN / PIO-GCN training and compare GCN, `LODF_yP`, random, and `line_order` search efficiency under the same protocol.
