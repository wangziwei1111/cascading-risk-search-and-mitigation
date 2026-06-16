# IEEE39 GCN Usefulness Audit Dry-Run Validator

This round is the IEEE39 GCN audit dry-run validator.

It did not train GCN.
It did not run the formal GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.

## What The Dry-Run Validator Checked

- candidate dataset row count, bus-fault row count, and B1-B39 coverage
- duplicate `scenario_id` / `label_id_v2` risks
- forbidden feature exclusion from proposed GCN inputs
- strict holdout completeness
- baseline comparison completeness
- B1 special tracking
- NF06 sensitivity
- L12 exclusion
- RL diff cleanliness
- forbidden tracked artifact cleanliness

## Dry-Run Result

- validator_scope: `dry_run_only`
- dry_run_validator_passed: `true`
- total_candidate_rows: `79`
- num_total_bus_fault_candidates: `39`
- forbidden_features_detected_in_inputs: `[]`
- strict_holdouts_complete: `true`
- baseline_comparison_complete: `true`
- b1_special_tracking_enabled: `true`
- nf06_sensitivity_enabled: `true`
- l12_exclusion_check_enabled: `true`
- target_bus_memorization_risk_flagged: `true`

## Important Boundary Notes

- forbidden features are excluded from proposed primary GCN inputs
- strict holdouts are complete
- baseline comparison is complete
- B1 remains special-tracked
- NF06 sensitivity remains enabled
- L12 remains excluded
- target_bus encoding has memorization risk and must be compared against target-bus-only baseline
- even after dry-run pass, the next step cannot be blind training
- the next step can only be preparing formal GCN usefulness audit execution
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
