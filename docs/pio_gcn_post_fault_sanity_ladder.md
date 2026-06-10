# Post-Fault Sanity Ladder

## Purpose

Round 20 proved that no-trip sanity passes. That is necessary, but it is not sufficient. Round 21 adds a post-fault sanity ladder so that single mild trip, low-risk ordered N-2, and random ordered N-2 controls also have reasonable behavior.

The goal is not to tune parameters to make learned Top20 look good. The goal is to make controls interpretable. If controls are all unstable, dynamic precision is not interpretable.

## Ladder

The ladder contains:

```text
no_trip
single_mild_trip
low_risk_ordered_n2
random_ordered_n2
learned_high_risk_n2
```

Pass rules:

```text
no_trip must be stable
single_mild_trip should be stable
low_risk_ordered_n2 should not be all unstable
random_ordered_n2 should not be all unstable
learned_high_risk_n2 can be higher stress, but it is not a formal performance conclusion
```

## Round 21 Result

With recommended post-fault options:

| case group | unstable fraction | passive trip fraction | mean stress | passed |
| --- | ---: | ---: | ---: | --- |
| no_trip | 0.00 | 0.00 | 0.0000 | true |
| single_mild_trip | 0.00 | 0.00 | 0.2423 | true |
| low_risk_ordered_n2 | 0.00 | 0.00 | 0.1137 | true |
| random_ordered_n2 | 0.00 | 0.00 | 0.0782 | true |
| learned_high_risk_n2 | 0.00 | 0.00 | 0.1137 | true |

This removes the all-unstable degeneracy in the sanity ladder. However, it also makes the current Top20 negative-control v3 groups all stable, so there is still no learned dynamic discrimination signal.

## Recommended Options

```text
damping_scale = 2
inertia_scale = 2
coupling_scale = 0.2
line_loading_scale = 0.002
relay_beta = 1.5
load_shed_step_fraction = 0.01
pm_update_mode = rebalance_to_current_pe
```

## Interpretability Gate

The gate output is:

```text
allowed_next_step = expand_top50_top100
default_dynamic_precision_interpretable = true
dynamic_discrimination_signal = false
```

This means Top50/Top100 can be expanded for diagnostic coverage, but current Top20 does not prove dynamic superiority.

If any required control level fails, the gate must output `continue_dynamic_calibration` instead of allowing expansion.

Round 22 performed this Top50/Top100 expansion. The result has `calibration_warning = true` because all learned, PIO-GCN, and LODF Top100 cases are dynamically stable under the recommended post-fault options.

Round 23 expanded the learned-reranker dataset to a medium non-smoke dataset. The non-smoke Top50/Top100 comparison is still all stable, so the updated gate now recommends:

```text
allowed_next_step = tune_post_fault_event_strength
```

This means the post-fault dynamic event strength should be tuned before making stronger dynamic-method claims.

## Limits

No dynamic recall is reported because no full dynamic truth exists.

This remains:

- not EMT;
- not full OPF;
- no renewable dynamic validation;
- no exciter, governor, or PSS;
- not an engineering-grade dynamic stability conclusion.
