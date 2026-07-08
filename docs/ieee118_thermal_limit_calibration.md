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

The wider sweep below uses `seed=20260708`, `max-paths=500`, `min-rate-a=1.0`, and the same ordered N-2 generator. Compact outputs are written under:

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

Recommended main stress scale: `flow_scaled=2.00`, `min-rate-a=1.0`.

Rationale: `2.00` keeps a substantial relay-cascade sample (`175/500`) while reducing the largest relay trip chain relative to `1.20`, `1.50`, and `1.80`. It also lowers the cut-load tail compared with the tighter scales. `2.50` is a useful more conservative sensitivity point, but `2.00` better preserves overload-relay diversity for the next full-truth run.

## Recommendation

Use two tracks in the next IEEE118 stage:

- `original_rate_a`: MATPOWER-fidelity baseline, weak overload relay stress.
- `flow_scaled=2.00`, `min-rate-a=1.0`: recommended main OPA-style overload relay stress setting.
- `flow_scaled=2.50`, `min-rate-a=1.0`: optional more conservative sensitivity setting.

Do not train IEEE118 GCNs or claim search efficiency from this calibration alone. The next step is to pick a limit policy, regenerate full-truth/Step2-State data under that policy, then compare GCN, `LODF_yP`, random, and `line_order` with the same evaluation protocol.
