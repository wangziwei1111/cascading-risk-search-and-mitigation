# IEEE39 No-Leakage Static Feature Audit

## forbidden_features_checked
```json
[
  "min_voltage_pu",
  "max_voltage_pu",
  "frequency",
  "rotor angle",
  "speed deviation",
  "dynamic_stress_score",
  "unstable_flag",
  "phasor_RMS",
  "generator_speed_proxy"
]
```

## forbidden_features_detected_in_inputs
```json
[]
```

- `post_fault_dynamic_measurements_used_as_inputs`: False
- `dynamic_targets_only_used_as_labels`: True
- `static_or_prefault_sources_only`: True
- `no_leakage_static_feature_policy_passed`: True
