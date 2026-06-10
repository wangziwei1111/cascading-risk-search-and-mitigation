# Dynamic Event Strength Calibration

## Purpose

Round 24 fixes non-smoke TopK coverage and calibrates post-fault event strength so the simplified dynamic layer is no longer all-stable or all-unstable.

This is a preliminary diagnostic calibration. The goal is not to make learned ranking look better. The goal is to make learned, PIO-GCN, and LODF dynamic diagnostics interpretable.

## TopK Coverage

The Round 23 shortfall came from duplicate ordered N-2 paths in the input ranking. The input table had enough rows, but duplicate paths were removed during case export.

Round 24 fixes this by:

- sorting each method by its own score;
- dropping duplicate paths before TopK selection;
- filtering invalid or same-line paths;
- filling from deeper rank positions until Top50/Top100 have enough unique valid paths.

Coverage after the fix:

| method | Top50 coverage | Top100 coverage |
| --- | ---: | ---: |
| learned_mlp | 1.0000 | 1.0000 |
| pio_gcn | 1.0000 | 1.0000 |
| lodf | 1.0000 | 1.0000 |

No coverage warning is active after the fix.

## Recommended Event Strength Options

The calibration scans dynamic-threshold sensitivity over the non-smoke Top100 subset and selects a nondegenerate setting:

```text
frequency_unstable_threshold_hz = 49.3
rotor_angle_unstable_threshold_deg = 180.0
damping_scale = 2.0
inertia_scale = 2.0
coupling_scale = 0.2
line_loading_scale = 0.002
relay_beta = 1.5
load_shed_step_fraction = 0.01
```

The selected options are stored in:

```text
results/gcn_search/simulink_dynamic_event_strength_calibration/recommended_event_strength_options.json
```

## Event-Strength Dynamic Comparison

| method | Top50 precision | Top100 precision | Top50 mean stress | Top100 mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_mlp | 0.3000 | 0.2700 | 0.0985 | 0.0871 |
| pio_gcn | 0.3400 | 0.3600 | 0.0997 | 0.1029 |
| lodf | 0.2800 | 0.3000 | 0.0887 | 0.0900 |

The calibrated dynamic layer is not all-stable and not all-unstable:

```text
nondegenerate_dynamic_layer = true
calibration_warning = false
dynamic_discrimination_signal = false
```

PIO-GCN has higher Top100 dynamic precision and mean stress than learned MLP in this preliminary diagnostic. Therefore there is no learned dynamic advantage observed in this round.

Round 25 adds robustness and bootstrap checks. Across 9 nondegenerate event-strength settings, learned is not the best Top100 precision method; PIO-GCN is best in the available envelope. Bootstrap confidence intervals also do not support learned being robustly above PIO-GCN or LODF. The report conclusion is `no_dynamic_advantage_observed_preliminary`.

## OPA / Dynamic Alignment

The event-strength calibrated alignment remains mixed:

| method | TopK | corr(stress, OPA shed) | corr(dynamic_unstable, OPA critical) |
| --- | ---: | ---: | ---: |
| learned_mlp | 50 | 0.1616 | 0.1905 |
| learned_mlp | 100 | 0.1211 | 0.1461 |
| pio_gcn | 50 | -0.0533 | -0.0462 |
| pio_gcn | 100 | -0.0685 | -0.0817 |
| lodf | 50 | 0.0305 | 0.0300 |
| lodf | 100 | -0.0315 | -0.0322 |

The learned group has mildly positive OPA/dynamic alignment, but not enough to claim method superiority because its dynamic precision is lower than PIO-GCN.

## Gate Decision

The updated interpretability gate outputs:

```text
topk_coverage_passed = true
event_strength_calibrated = true
nondegenerate_dynamic_layer = true
preliminary_dynamic_discrimination_signal = false
allowed_next_step = report_no_dynamic_advantage_preliminary
```

## Limits

No dynamic recall is reported because no full dynamic truth exists.

This remains:

- simplified swing-equation prototype;
- not EMT;
- not full OPF;
- no renewable dynamic validation;
- no exciter, governor, or PSS;
- not an engineering-grade dynamic stability conclusion.
