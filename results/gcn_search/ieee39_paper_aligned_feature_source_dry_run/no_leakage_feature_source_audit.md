# IEEE39 No-Leakage Feature Source Audit

## forbidden_features_checked
- `min_voltage_pu`
- `max_voltage_pu`
- `frequency`
- `rotor angle`
- `speed deviation`
- `dynamic_stress_score`
- `unstable_flag`
- `phasor_RMS`
- `generator_speed_proxy`

## forbidden_features_detected_in_inputs
- []

- `post_fault_dynamic_measurements_used_as_inputs`: False
- `dynamic_targets_only_used_as_labels`: True
- `bus_fault_labels_not_used_as_paper_inputs`: True
## source_leakage_risk_summary
```json
{
  "post_fault_sources_detected_in_repository": true,
  "post_fault_sources_used_for_paper_inputs": false,
  "risk_level": "controlled_by_not_using_dynamic_sources"
}
```

- `no_leakage_feature_source_policy_passed`: True
