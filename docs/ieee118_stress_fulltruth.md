# IEEE118 Stress-Calibrated Full-Truth

This stage prepares OPA-style overload relay ground truth for IEEE118 using synthetic flow-scaled thermal limits. It does not train a GCN and does not evaluate search efficiency.

## Recommended Main Stress Setting

```text
limit-mode = flow_scaled
flow-limit-scale = 8.00
min-rate-a = 1.0
seed = 20260708
```

The synthetic limit rule is:

```text
RATE_A_i = max(flow_limit_scale * abs(PF0_i), min_rate_a)
```

`PF0_i` comes from the initial DCOPF for the seeded IEEE118 load scenario.

## Why Flow-Scaled 8.00

The original IEEE118 `RATE_A` values are uniformly 9900 MW, which produces very small initial loading ratios and almost no overload relay activity under `beta=1.2`. The 500-path calibration sweep showed that `flow_scaled` creates OPA-style relay cascades, while the original limits mostly produce island-only critical paths.

`flow_scaled=1.20` was useful as a severe proof-of-stress setting, but it is too tight for the preferred main experiment: the 500-path smoke produced 179 relay-cascade rows and up to 93 relay trips in a single path. That confirms the relay mechanism works, but the mechanism mix is dominated by very large passive outage chains.

A wider ordered-prefix sweep with `min-rate-a=1.0` compared 1.50, 1.80, 2.00, 2.50, and 3.00. That sweep showed that `2.00` was less severe than 1.20 but still had a high critical ratio in the first 500 ordered paths:

| scale | critical | relay_cascade | island_only | redispatch_shed | mixed | max_event_loading | total_relay_trips | max_relay_trips/path | mean shed MW | p95 shed MW | max shed MW |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.50 | 214 | 168 | 46 | 133 | 168 | 105.391542 | 5922 | 72 | 46.714035 | 200.154179 | 384.037454 |
| 1.80 | 239 | 215 | 24 | 183 | 215 | 73.521654 | 8202 | 73 | 38.736447 | 134.873145 | 294.578857 |
| 2.00 | 198 | 175 | 23 | 21 | 175 | 66.169489 | 6619 | 56 | 21.956773 | 85.079896 | 171.634517 |
| 2.50 | 142 | 124 | 18 | 46 | 124 | 52.935591 | 4450 | 41 | 9.536571 | 52.907481 | 126.015555 |
| 3.00 | 86 | 68 | 18 | 12 | 68 | 65.159776 | 3300 | 40 | 5.637229 | 40.354200 | 139.023702 |

However, `--max-paths 500` with the default `sample-mode=first` is an ordered-prefix smoke test, not an unbiased estimate of full-system risk. It starts from paths such as `L001->L002`, `L001->L003`, and can overrepresent early line-label structure. Critical ratios for full-system calibration should come from random samples or full-truth enumeration.

RTS-79 has a sparse critical-path ratio of about `40 / 1406 = 2.8%`. The IEEE118 stress setting should remain comparably sparse enough for later GCN search-efficiency validation to be meaningful. A random 1000-path sweep used `sample-mode=random`, `sample-seed=20260708`, and produced:

| scale | critical | critical ratio | relay_cascade | relay ratio | island_only | redispatch_shed | mixed | max_event_loading | total_relay_trips | max_relay_trips/path | mean shed MW | p95 shed MW | max shed MW |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.00 | 380 | 0.380 | 328 | 0.328 | 52 | 36 | 328 | 70.685209 | 11382 | 54 | 20.762054 | 83.107849 | 254.202616 |
| 3.00 | 190 | 0.190 | 153 | 0.153 | 37 | 28 | 153 | 44.120788 | 7629 | 48 | 7.076575 | 41.108813 | 253.846112 |
| 4.00 | 156 | 0.156 | 141 | 0.141 | 15 | 13 | 141 | 37.693219 | 4774 | 36 | 5.447985 | 36.769920 | 132.198213 |
| 5.00 | 110 | 0.110 | 88 | 0.088 | 22 | 33 | 88 | 29.585148 | 3281 | 32 | 2.433584 | 21.691311 | 81.359226 |
| 6.00 | 74 | 0.074 | 52 | 0.052 | 22 | 19 | 52 | 32.341323 | 2688 | 20 | 1.724182 | 7.272189 | 81.359226 |
| 8.00 | 52 | 0.052 | 47 | 0.047 | 5 | 0 | 47 | 29.113411 | 1988 | 18 | 1.607836 | 7.272189 | 81.359226 |
| 10.00 | 48 | 0.048 | 47 | 0.047 | 1 | 0 | 47 | 23.701469 | 1313 | 15 | 1.500888 | 0.000000 | 81.359226 |

The recommended main setting is now `flow_scaled=8.00`, `min-rate-a=1.0`: it reaches a `5.2%` critical ratio and `4.7%` relay-cascade ratio, close to the target sparse range while retaining enough overload relay events. `10.00` is a more conservative sensitivity point.

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
  --flow-limit-scale 8.00 \
  --min-rate-a 1.0 \
  --sample-mode random \
  --sample-size 1000 \
  --sample-seed 20260708 \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_random1000
```

Full seed:

```bash
python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py \
  --seeds 20260708 \
  --limit-mode flow_scaled \
  --flow-limit-scale 8.00 \
  --min-rate-a 1.0 \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708 \
  --resume \
  --checkpoint-every 500
```

Audit:

```bash
python src/gcn_search/ieee118/analyze_ieee118_fulltruth.py \
  --input-dir results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708 \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708
```

## Full Seed Status

The `flow_scaled=8.00`, `min-rate-a=1.0` full seed is complete under:

```text
results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708/
```

Full-seed audit:

- Rows generated: 34,410 / 34,410.
- Converged rows: 34,410.
- Error rows: 0.
- Critical rows: 1,859.
- Critical ratio: 0.054025.
- Relay-cascade rows: 1,659.
- Relay-cascade ratio: 0.048213.
- Island-only rows: 200.
- Redispatch-shed rows: 2.
- Mixed rows: 1,659.
- Maximum load shed path: `L121->L125`.
- Maximum load shed: 111.760638 MW.
- Maximum relay trips in one path: 20.

The full 34,410-row raw CSV is intentionally local-only and should not be committed. This PR commits only compact audit outputs, renamed with the `ieee118_flow_scaled_800_*` prefix for review.

The earlier tight `1.20` full seed run remains a local checkpoint reference under `results/gcn_search/ieee118_flow_scaled_120_fulltruth_seed20260708/`, but it is no longer the recommended main full-truth setting.

## Original vs Stress-Calibrated

- `original_rate_a`: MATPOWER-fidelity baseline; weak overload relay stress because branch limits are uniformly 9900 MW.
- `flow_scaled`: OPA-style overload relay stress setting; intended to produce relay cascade ground truth for later search experiments.

Future GCN efficiency validation should compare original and stress-calibrated regimes separately. The stress-calibrated full-truth table is a prerequisite for Step2-State generation and later comparison among GCN, `LODF_yP`, random, and `line_order`.

## Not GCN Evaluation

This work is still full-truth data preparation. No IEEE118 GCN has been trained here, and no GCN search-efficiency claim should be made from this stage alone.
