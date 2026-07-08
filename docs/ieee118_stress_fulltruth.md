# IEEE118 Stress-Calibrated Full-Truth

This stage prepares OPA-style overload relay ground truth for IEEE118 using synthetic flow-scaled thermal limits. It does not train a GCN and does not evaluate search efficiency.

## Recommended Main Stress Setting

```text
limit-mode = flow_scaled
flow-limit-scale = 2.00
min-rate-a = 1.0
seed = 20260708
```

The synthetic limit rule is:

```text
RATE_A_i = max(flow_limit_scale * abs(PF0_i), min_rate_a)
```

`PF0_i` comes from the initial DCOPF for the seeded IEEE118 load scenario.

## Why Flow-Scaled 2.00

The original IEEE118 `RATE_A` values are uniformly 9900 MW, which produces very small initial loading ratios and almost no overload relay activity under `beta=1.2`. The 500-path calibration sweep showed that `flow_scaled` creates OPA-style relay cascades, while the original limits mostly produce island-only critical paths.

`flow_scaled=1.20` was useful as a severe proof-of-stress setting, but it is too tight for the preferred main experiment: the 500-path smoke produced 179 relay-cascade rows and up to 93 relay trips in a single path. That confirms the relay mechanism works, but the mechanism mix is dominated by very large passive outage chains.

A wider sweep with `min-rate-a=1.0` compared 1.50, 1.80, 2.00, 2.50, and 3.00. The recommended main setting is now `flow_scaled=2.00` because it keeps enough relay-cascade samples while reducing extreme relay trip chains and cut-load tails:

| scale | critical | relay_cascade | island_only | redispatch_shed | mixed | max_event_loading | total_relay_trips | max_relay_trips/path | mean shed MW | p95 shed MW | max shed MW |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.50 | 214 | 168 | 46 | 133 | 168 | 105.391542 | 5922 | 72 | 46.714035 | 200.154179 | 384.037454 |
| 1.80 | 239 | 215 | 24 | 183 | 215 | 73.521654 | 8202 | 73 | 38.736447 | 134.873145 | 294.578857 |
| 2.00 | 198 | 175 | 23 | 21 | 175 | 66.169489 | 6619 | 56 | 21.956773 | 85.079896 | 171.634517 |
| 2.50 | 142 | 124 | 18 | 46 | 124 | 52.935591 | 4450 | 41 | 9.536571 | 52.907481 | 126.015555 |
| 3.00 | 86 | 68 | 18 | 12 | 68 | 65.159776 | 3300 | 40 | 5.637229 | 40.354200 | 139.023702 |

The compact comparison files are under:

```text
results/gcn_search/ieee118_limit_calibration/
```

The older `flow_scaled=1.20` smoke result is retained as a tight stress reference:

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
  --flow-limit-scale 2.00 \
  --min-rate-a 1.0 \
  --max-paths 500 \
  --output-dir results/gcn_search/ieee118_flow_scaled_200_smoke500
```

Full seed:

```bash
python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py \
  --seeds 20260708 \
  --limit-mode flow_scaled \
  --flow-limit-scale 2.00 \
  --min-rate-a 1.0 \
  --output-dir results/gcn_search/ieee118_flow_scaled_200_fulltruth_seed20260708 \
  --resume \
  --checkpoint-every 500
```

Audit:

```bash
python src/gcn_search/ieee118/analyze_ieee118_fulltruth.py \
  --input-dir results/gcn_search/ieee118_flow_scaled_200_smoke500 \
  --output-dir results/gcn_search/ieee118_flow_scaled_200_smoke500
```

## Full Seed Status

The earlier tight `1.20` full seed run is checkpointed under:

```text
results/gcn_search/ieee118_flow_scaled_120_fulltruth_seed20260708/
```

Because this tight stress setting produces many passive relay trips, the full 34,410-row run is significantly slower than the original-rate case. The run uses `--resume` and `--checkpoint-every 500` so it can continue without restarting, but it is no longer the recommended main full-truth setting.

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
