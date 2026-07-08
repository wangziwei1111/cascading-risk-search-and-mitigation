# IEEE118 Thermal Limit Calibration

This branch keeps the original IEEE118 `RATE_A` mode and adds a `flow_scaled` synthetic thermal-limit mode for OPA-style overload relay stress tests.

## Why Calibration Is Needed

PYPOWER `case118` uses uniformly large branch limits:

- Branch count: 186
- `RATE_A <= 0`: 0
- `RATE_A` min / mean / median / max: 9900 / 9900 / 9900 / 9900 MW
- Initial DCOPF loading ratio max: about 0.044

With `beta=1.2`, these original limits are too loose to meaningfully exercise overload relay tripping. They are still useful as a MATPOWER-fidelity baseline, but they should not be the only setting for cascading-risk search experiments.

## Modes

Original mode:

```text
--limit-mode original_rate_a
```

Synthetic flow-scaled mode:

```text
--limit-mode flow_scaled
RATE_A_i = max(flow_limit_scale * abs(PF0_i), min_rate_a)
```

`PF0_i` is taken from the initial DCOPF for the seeded IEEE118 load scenario. `min_rate_a` prevents near-zero-flow lines from receiving unusably small limits.

## Smoke Commands

```bash
python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py --seeds 20260708 --max-paths 500 --limit-mode original_rate_a --output-dir results/gcn_search/ieee118_thermal_limit_calibration/original_rate_a_max500 --checkpoint-every 100

python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py --seeds 20260708 --max-paths 500 --limit-mode flow_scaled --flow-limit-scale 1.30 --min-rate-a 25 --output-dir results/gcn_search/ieee118_thermal_limit_calibration/flow_scaled_1_30_max500 --checkpoint-every 100

python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py --seeds 20260708 --max-paths 500 --limit-mode flow_scaled --flow-limit-scale 1.20 --min-rate-a 25 --output-dir results/gcn_search/ieee118_thermal_limit_calibration/flow_scaled_1_20_max500 --checkpoint-every 100

python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py --seeds 20260708 --max-paths 500 --limit-mode flow_scaled --flow-limit-scale 1.10 --min-rate-a 25 --output-dir results/gcn_search/ieee118_thermal_limit_calibration/flow_scaled_1_10_max500 --checkpoint-every 100

python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py --seeds 20260708 --max-paths 500 --limit-mode flow_scaled --flow-limit-scale 1.05 --min-rate-a 25 --output-dir results/gcn_search/ieee118_thermal_limit_calibration/flow_scaled_1_05_max500 --checkpoint-every 100
```

## 500-Path Smoke Summary

Initial calibration used `min-rate-a=25` and showed that synthetic limits can activate OPA-style relay cascades:

| mode | scale | critical | relay_cascade | island_only | max_event_loading | total_relay_trips | max_relay_trips/path | mean shed MW | p95 shed MW | max shed MW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| original_rate_a | - | 5 | 0 | 5 | 0.075249 | 0 | 0 | 0.453378 | 0.000000 | 81.359226 |
| flow_scaled | 1.30 | 189 | 161 | 28 | 10.529771 | 5374 | 76 | 83.044933 | 436.938804 | 692.492930 |
| flow_scaled | 1.20 | 203 | 170 | 33 | 17.300365 | 5926 | 92 | 90.706241 | 437.019230 | 621.369512 |
| flow_scaled | 1.10 | 185 | 156 | 29 | 12.970661 | 6527 | 90 | 110.166535 | 533.427593 | 766.264207 |
| flow_scaled | 1.05 | 102 | 68 | 34 | 5.350277 | 400 | 20 | 9.663311 | 70.590348 | 214.130373 |

## Wide-Scale Sweep

After the first stress full-truth attempt, `flow_scaled=1.20` with `min-rate-a=1.0` was found to be too tight for a main experiment: the 500-path smoke generated 179 relay-cascade rows and up to 93 relay trips in a single path. This is useful as a severe stress case, but it can dominate the mechanism mix with very large passive outage chains.

The ordered-prefix sweep below uses `seed=20260708`, `max-paths=500`, `min-rate-a=1.0`, and the same ordered N-2 generator. Compact outputs are written under:

```text
results/gcn_search/ieee118_limit_calibration/
```

| scale | total | converged | errors | critical | relay_cascade | island_only | redispatch_shed | mixed | max_event_loading | max_pre_redispatch_loading | total_relay_trips | max_relay_trips/path | mean shed MW | p95 shed MW | max shed MW |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.50 | 500 | 500 | 0 | 214 | 168 | 46 | 133 | 168 | 105.391542 | 105.391542 | 5922 | 72 | 46.714035 | 200.154179 | 384.037454 |
| 1.80 | 500 | 500 | 0 | 239 | 215 | 24 | 183 | 215 | 73.521654 | 73.521654 | 8202 | 73 | 38.736447 | 134.873145 | 294.578857 |
| 2.00 | 500 | 500 | 0 | 198 | 175 | 23 | 21 | 175 | 66.169489 | 66.169489 | 6619 | 56 | 21.956773 | 85.079896 | 171.634517 |
| 2.50 | 500 | 500 | 0 | 142 | 124 | 18 | 46 | 124 | 52.935591 | 52.935591 | 4450 | 41 | 9.536571 | 52.907481 | 126.015555 |
| 3.00 | 500 | 500 | 0 | 86 | 68 | 18 | 12 | 68 | 65.159776 | 65.159776 | 3300 | 40 | 5.637229 | 40.354200 | 139.023702 |

This ordered-prefix sweep is useful for smoke testing only. Because `--max-paths` takes the first ordered paths (`L001->L002`, `L001->L003`, ...), it can overrepresent local structure around early line labels. It should not be used to estimate the global IEEE118 critical-path ratio.

## Random 1000-Path Sweep

RTS-79 has a sparse critical-path ratio of about `40 / 1406 = 2.8%`. For IEEE118 GCN search evaluation to be meaningful, the stress setting should also keep critical paths relatively sparse. The target range for this calibration is roughly 2% to 8% critical paths, with nonzero relay-cascade samples.

The random sweep uses:

```bash
python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py \
  --seeds 20260708 \
  --limit-mode flow_scaled \
  --flow-limit-scale <SCALE> \
  --min-rate-a 1.0 \
  --sample-mode random \
  --sample-size 1000 \
  --sample-seed 20260708 \
  --output-dir results/gcn_search/ieee118_flow_scaled_<TAG>_random1000
```

Compact outputs are:

```text
results/gcn_search/ieee118_limit_calibration/ieee118_flow_scaled_random1000_wide_scale_sweep.csv
results/gcn_search/ieee118_limit_calibration/ieee118_flow_scaled_random1000_wide_scale_sweep.json
```

| scale | total | converged | errors | critical | critical ratio | relay_cascade | relay ratio | island_only | redispatch_shed | mixed | max_event_loading | total_relay_trips | max_relay_trips/path | mean shed MW | p95 shed MW | max shed MW |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.00 | 1000 | 1000 | 0 | 380 | 0.380 | 328 | 0.328 | 52 | 36 | 328 | 70.685209 | 11382 | 54 | 20.762054 | 83.107849 | 254.202616 |
| 3.00 | 1000 | 1000 | 0 | 190 | 0.190 | 153 | 0.153 | 37 | 28 | 153 | 44.120788 | 7629 | 48 | 7.076575 | 41.108813 | 253.846112 |
| 4.00 | 1000 | 1000 | 0 | 156 | 0.156 | 141 | 0.141 | 15 | 13 | 141 | 37.693219 | 4774 | 36 | 5.447985 | 36.769920 | 132.198213 |
| 5.00 | 1000 | 1000 | 0 | 110 | 0.110 | 88 | 0.088 | 22 | 33 | 88 | 29.585148 | 3281 | 32 | 2.433584 | 21.691311 | 81.359226 |
| 6.00 | 1000 | 1000 | 0 | 74 | 0.074 | 52 | 0.052 | 22 | 19 | 52 | 32.341323 | 2688 | 20 | 1.724182 | 7.272189 | 81.359226 |
| 8.00 | 1000 | 1000 | 0 | 52 | 0.052 | 47 | 0.047 | 5 | 0 | 47 | 29.113411 | 1988 | 18 | 1.607836 | 7.272189 | 81.359226 |
| 10.00 | 1000 | 1000 | 0 | 48 | 0.048 | 47 | 0.047 | 1 | 0 | 47 | 23.701469 | 1313 | 15 | 1.500888 | 0.000000 | 81.359226 |

Recommended main stress scale: `flow_scaled=8.00`, `min-rate-a=1.0`.

Rationale: random sampling shows that `2.00` remains too tight (`38.0%` critical), and even `3.00` to `5.00` exceed the target sparse range. `8.00` has a `5.2%` critical ratio and a `4.7%` relay-cascade ratio, close to the desired sparsity while preserving enough relay events. `10.00` is a more conservative sensitivity point with slightly lower relay-trip severity.

## Recommendation

Use two tracks in the next IEEE118 stage:

- `original_rate_a`: MATPOWER-fidelity baseline, weak overload relay stress.
- `flow_scaled=8.00`, `min-rate-a=1.0`: recommended main OPA-style overload relay stress setting.
- `flow_scaled=10.00`, `min-rate-a=1.0`: optional more conservative sensitivity setting.

Do not train IEEE118 GCNs or claim search efficiency from this calibration alone. The next step is to pick a limit policy, regenerate full-truth/Step2-State data under that policy, then compare GCN, `LODF_yP`, random, and `line_order` with the same evaluation protocol.
