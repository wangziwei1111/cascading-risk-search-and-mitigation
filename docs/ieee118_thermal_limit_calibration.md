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

| mode | scale | critical | relay_cascade | island_only | max_event_loading | total_relay_trips | max_relay_trips/path | mean shed MW | p95 shed MW | max shed MW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| original_rate_a | - | 5 | 0 | 5 | 0.075249 | 0 | 0 | 0.453378 | 0.000000 | 81.359226 |
| flow_scaled | 1.30 | 189 | 161 | 28 | 10.529771 | 5374 | 76 | 83.044933 | 436.938804 | 692.492930 |
| flow_scaled | 1.20 | 203 | 170 | 33 | 17.300365 | 5926 | 92 | 90.706241 | 437.019230 | 621.369512 |
| flow_scaled | 1.10 | 185 | 156 | 29 | 12.970661 | 6527 | 90 | 110.166535 | 533.427593 | 766.264207 |
| flow_scaled | 1.05 | 102 | 68 | 34 | 5.350277 | 400 | 20 | 9.663311 | 70.590348 | 214.130373 |

## Recommendation

Use two tracks in the next IEEE118 stage:

- `original_rate_a`: MATPOWER-fidelity baseline, weak overload relay stress.
- `flow_scaled`: OPA-style overload relay stress test, with scale values swept rather than assumed.

Do not train IEEE118 GCNs or claim search efficiency from this calibration alone. The next step is to pick a limit policy, regenerate full-truth/Step2-State data under that policy, then compare GCN, `LODF_yP`, random, and `line_order` with the same evaluation protocol.
