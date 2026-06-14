# IEEE39 Dynamic-Aware Stricter Independent-Test Comparison

## Purpose

This round uses the current 35 IEEE39 training-ready compact dynamic labels to
separate two ideas:

1. an optimistic preview using compact dynamic measurement features; and
2. stricter no-leakage / topology-only previews that avoid using the same
   measurement quantities that help synthesize `dynamic_stress_score`.

This is still a preview / sanity-check comparison. It is not a final dynamic
performance conclusion.

## Inputs And Outputs

- input expanded dataset:
  `results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_dataset.csv`
- line map:
  `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv`
- output directory:
  `results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/`

The dataset has 35 samples. `L12` is excluded because it remains
`simulation_timeout / suspected islanding` and is not training-ready.

## Feature Sets

`leaky_dynamic_measurement_features` includes compact dynamic measurements such
as voltage, generator-speed-proxy frequency, speed deviation, and rotor-angle
separation. Because `dynamic_stress_score` is synthesized from these compact
measurements, this setting is an optimistic preview upper bound.

`no_dynamic_measurement_features` removes those compact measurement columns and
uses categorical, line identity, and topology-derived features. It is less
leaky, but still preview-only.

`topology_only_features` uses line-map / topology / fault-setup information and
does not use compact measurement columns or line_id one-hot features. This is
the most conservative preview feature set in this round.

## Split Strategies

- `leave_one_out`: aligned with the expanded preview, but reported separately
  for each feature set.
- `grouped_line_range_holdout`: holds out L01-L10, L11-L20, L21-L34, and an
  auxiliary non-line fold. L12 remains excluded.
- `endpoint_bus_region_holdout`: groups line rows by average endpoint bus into
  low, mid, high, and auxiliary non-line folds.
- `random_kfold_baseline`: 5-fold shuffled baseline with `random_seed = 42`.
  This is a baseline only, not the most credible metric.

## Key Result

The best leaky result has RMSE about `0.030455`. The best no-leakage result has
RMSE about `0.107855`. The positive gap of about `0.077400` means that removing
dynamic measurement features makes the prediction task much harder.

This is expected and important. It shows why the earlier excellent expanded
preview metrics should be interpreted cautiously: they partly benefit from
features that are close to the proxy target construction.

## Boundaries

- No Simulink simulation was run in this round.
- No `.slx` file was modified.
- L12 was not fixed and was not added to training-ready labels.
- No Simscape physical wiring was modified.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade
  protection.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full
  timeseries.

## Next Step

For a more credible conclusion, add non-line-trip fault types and build a truly
independent test set across operating conditions, systems, or fault classes.
Also keep checking target-feature leakage before reporting performance.

## Non-Line-Trip Expansion Preparation

The follow-up preparation step adds a taxonomy and manifest for non-line-trip
fault types. It does not run Simulink, does not modify `.slx`, does not fix L12,
and does not retrain the dynamic-aware reranker.

The first recommended candidates are the existing three-phase fault-clear case,
a short fault-duration sweep on the existing fault block, and the basic relay
proxy case. Different-bus faults, load steps, generator-trip /
mechanical-power-step events, and bus-voltage-reference events remain
manual/future items until a safe injection point is verified.

This expansion is important because the stricter comparison showed
target-feature leakage risk. Non-line-trip faults are a necessary next check for
generalization reliability, but they are not yet new training-ready labels. It
is not a final dynamic performance conclusion.

## Smoke-Test Follow-Up

The non-line-trip smoke-test follow-up ran only `NF01`, `NF02`, `NF03`, `NF04`,
and `NF06`. All five completed as smoke candidates with compact
`voltage_speed_angle` measurements. This improves feasibility for a later
non-line-trip label export, but it does not change the formal label gate and it
does not retrain the dynamic-aware reranker.

The relay proxy remains a basic proxy, not engineering-grade protection.
`generator_speed_proxy` remains a proxy, not direct frequency, and the model is
still `phasor_RMS`, not EMT.
