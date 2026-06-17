# IEEE39 No-Leakage Proxy Feature Audit

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
  "generator_speed_proxy",
  "label-derived flags",
  "post-fault dynamic measurements"
]
```

## forbidden_features_detected_in_inputs
```json
[]
```

- `post_fault_dynamic_measurements_used_as_inputs`: False
- `static_or_prefault_sources_only`: True
- `dynamic_targets_only_used_as_labels`: True
- `proxy_not_engineering_relay_setting`: True
- `no_leakage_policy_passed`: True
