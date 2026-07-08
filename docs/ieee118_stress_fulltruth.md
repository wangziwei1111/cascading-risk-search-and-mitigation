# IEEE118 Stress-Calibrated Full-Truth

This stage prepares OPA-style overload relay ground truth for IEEE118 using synthetic flow-scaled thermal limits. It does not train a GCN and does not evaluate search efficiency.

## Main Stress Setting

```text
limit-mode = flow_scaled
flow-limit-scale = 1.20
min-rate-a = 1.0
seed = 20260708
```

The synthetic limit rule is:

```text
RATE_A_i = max(flow_limit_scale * abs(PF0_i), min_rate_a)
```

`PF0_i` comes from the initial DCOPF for the seeded IEEE118 load scenario.

## Why Flow-Scaled 1.20

The original IEEE118 `RATE_A` values are uniformly 9900 MW, which produces very small initial loading ratios and almost no overload relay activity under `beta=1.2`. The 500-path calibration sweep showed that `flow_scaled` creates OPA-style relay cascades, while the original limits mostly produce island-only critical paths.

`flow_scaled=1.20` is selected as the first main stress setting because its 500-path smoke generated strong relay activity without relying on full-network synthetic dynamics:

- 500 paths
- 500 converged
- 206 critical
- 179 relay-cascade paths
- 27 island-only paths
- 120 redispatch-shed paths
- 179 mixed paths
- maximum load shed path: `L001->L093`
- maximum load shed: 797.693811 MW
- maximum relay trips per path: 93

## Commands

Smoke:

```bash
python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py \
  --seeds 20260708 \
  --limit-mode flow_scaled \
  --flow-limit-scale 1.20 \
  --min-rate-a 1.0 \
  --max-paths 500 \
  --output-dir results/gcn_search/ieee118_flow_scaled_120_smoke500
```

Full seed:

```bash
python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py \
  --seeds 20260708 \
  --limit-mode flow_scaled \
  --flow-limit-scale 1.20 \
  --min-rate-a 1.0 \
  --output-dir results/gcn_search/ieee118_flow_scaled_120_fulltruth_seed20260708 \
  --resume \
  --checkpoint-every 500
```

Audit:

```bash
python src/gcn_search/ieee118/analyze_ieee118_fulltruth.py \
  --input-dir results/gcn_search/ieee118_flow_scaled_120_smoke500 \
  --output-dir results/gcn_search/ieee118_flow_scaled_120_smoke500
```

## Full Seed Status

The full seed run is checkpointed under:

```text
results/gcn_search/ieee118_flow_scaled_120_fulltruth_seed20260708/
```

Because this stress setting produces many passive relay trips, the full 34,410-row run is significantly slower than the original-rate case. The run uses `--resume` and `--checkpoint-every 500` so it can continue without restarting.

Current checkpoint from this branch:

- Rows generated: 9,500 / 34,410.
- Converged rows: 9,500.
- Error rows: 0.
- Critical rows: 3,017.
- Relay-cascade rows: 2,228.
- Island-only rows: 789.
- Redispatch-shed rows: 1,083.
- Mixed rows: 2,228.
- Maximum load shed path so far: `L019->L093`.
- Maximum load shed so far: 797.693811 MW.
- Maximum relay trips in one path so far: 97.

The run was stopped at this checkpoint for review-time practicality. It can continue with the same full-seed command because `--resume` is enabled.

The complete 34,410-row CSV should remain local and should not be committed. Commit only compact audit outputs after the full run is complete.

## Original vs Stress-Calibrated

- `original_rate_a`: MATPOWER-fidelity baseline; weak overload relay stress because branch limits are uniformly 9900 MW.
- `flow_scaled`: OPA-style overload relay stress setting; intended to produce relay cascade ground truth for later search experiments.

Future GCN efficiency validation should compare original and stress-calibrated regimes separately. The stress-calibrated full-truth table is a prerequisite for Step2-State generation and later comparison among GCN, `LODF_yP`, random, and `line_order`.

## Not GCN Evaluation

This work is still full-truth data preparation. No IEEE118 GCN has been trained here, and no GCN search-efficiency claim should be made from this stage alone.
