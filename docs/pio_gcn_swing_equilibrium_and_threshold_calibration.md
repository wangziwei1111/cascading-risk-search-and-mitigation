# Swing Equilibrium and Threshold Calibration

## Purpose

Round 19 showed that calibrated learned Top20, low-score Top20, random Top20, and line-order Top20 were all 20/20 dynamically unstable. That means dynamic precision@20 is not interpretable yet.

Round 20 therefore checks the dynamic layer before using it for method comparison. In plain terms: if the no-trip sanity case is unstable, the swing model itself is not balanced enough, so learned Top-K dynamic validation should not be interpreted.

## What Changed

Round 20 adds:

```text
matlab/simulink_rts79/initialize_swing_equilibrium.m
matlab/simulink_rts79/run_swing_equilibrium_sanity_demo.m
src/gcn_search/legacy_rts79/analyze_swing_equilibrium_diagnostics.py
src/gcn_search/legacy_rts79/analyze_dynamic_threshold_sensitivity.py
src/gcn_search/legacy_rts79/summarize_dynamic_negative_controls_v2.py
```

## No-Trip Sanity

The no-trip sanity case has no active line trip. It should remain close to 50 Hz and should not show large COI-relative rotor angle separation.

Current pass criteria:

```text
frequency_nadir_hz >= 49.8
frequency_zenith_hz <= 50.2
max_rotor_angle_separation_coi_deg <= 60
initial_pm_pe_max_abs_residual is small
```

If no-trip sanity fails, dynamic validation results are treated as a model-calibration warning, not as method performance.

## COI Reference

The COI reference removes common center-of-inertia angle drift in the simplified multi-machine swing model. The dynamic instability criterion now uses COI-relative rotor angle separation by default, while raw angle separation is still recorded for diagnostics.

This is only a simplified reference-frame correction. It is not a detailed transient-stability model.

## Pm/Pe Equilibrium

`initialize_swing_equilibrium.m` initializes:

```text
delta0
omega0
Pm0
Pe0
Bred0
equilibriumResidual
```

The goal is to reduce artificial initial active-power mismatch. The diagnostics record `initial_pm_pe_residual_norm` and `initial_pm_pe_max_abs_residual`.

After approximate security load shedding, `update_swing_power_after_load_shed.m` records the selected `pm_update_mode`. This is still not AGC and not full OPF.

## Threshold Sensitivity

Threshold sensitivity scans frequency and COI-angle thresholds to see whether learned paths separate from controls under reasonable thresholds.

This is not parameter tuning for a nicer result. A sensitivity result is only diagnostic. It must not be reported as a formal dynamic conclusion.

No dynamic recall is reported because no full dynamic truth set exists.

## Current Limits

- not EMT;
- not full OPF;
- no renewable dynamic validation;
- no exciter, governor, or PSS;
- not an engineering-grade dynamic stability conclusion.

Only when low-risk/random controls are no longer all unstable does dynamic precision become interpretable.

## Round 20 Preliminary Result

No-trip sanity passed:

```text
no_trip_dynamic_unstable = false
no_trip_frequency_nadir_hz = 50.0
no_trip_frequency_zenith_hz = 50.0
no_trip_max_rotor_angle_separation_coi_deg = 18.6714
initial_pm_pe_max_abs_residual = 0.0
sanity_passed = true
```

This means the basic no-trip equilibrium is now usable as a sanity baseline.

However, the low-risk cases are still too sensitive:

```text
single_mild_trip_dynamic_unstable = true
low_risk_n2_dynamic_unstable = true
```

The updated negative-control Top20 comparison still has default-threshold degeneracy:

| group | default unstable fraction | relaxed-threshold unstable fraction | passive trip fraction | mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 1.00 | 1.00 | 1.00 | 26.1084 |
| low_score_top20 | 1.00 | 0.70 | 0.75 | 11.7528 |
| random_top20 | 1.00 | 0.90 | 0.90 | 16.1437 |
| line_order_top20 | 1.00 | 0.40 | 0.60 | 9.1307 |

Threshold sensitivity shows a diagnostic separation signal, but the default result is still globally degenerate. This should be reported only as a calibration clue, not as a formal dynamic validation result.

## Round 21 Link

Round 21 adds the post-fault sanity ladder. The recommended post-fault options make no-trip, single mild trip, low-risk N-2, and random N-2 controls stable. This removes the all-unstable degeneracy, but the current Top20 v3 groups are also all stable, so there is still no learned dynamic discrimination signal.
