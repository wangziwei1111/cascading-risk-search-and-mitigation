# IEEE39 GCN Usefulness Audit Dry-Run Validator Summary

This round only runs the dry-run validator. It does not train GCN, does not run
the formal GCN usefulness audit, does not run Simulink, does not export labels,
and does not save any model.

## Validator Scope

- validator_scope: `dry_run_only`
- dry_run_validator_passed: `true`
- should_run_formal_gcn_audit_now: `false`
- should_train_gcn_now: `false`
- recommended_next_step: `prepare formal GCN usefulness audit execution in a separate round, still with no-leakage features and strict holdouts`

## Dataset Checks

- total_candidate_rows: `79`
- num_total_bus_fault_candidates: `39`
- all_ieee39_buses_have_bus_fault_candidate: `true`
- old_formal_gate: `35 / 33 / 33`
- l12_excluded: `true`
- nf06_provenance_warning_preserved: `true`
- b1_special_tracking_enabled: `true`

## Proposed No-Leakage Inputs

- `fault_type`
- `duration_s`
- `fault_start_s`
- `fault_clear_s`
- `trip_implementation`
- `line_id`
- `target_bus`
- `target_bus_or_component`
- `source_model_type`

## Required Strict Holdouts

- `random_candidate_split_baseline`
- `label_family_holdout`
- `bus_fault_holdout`
- `leave_one_bus_fault_out`
- `no_dynamic_measurement_leave_one_bus_fault_out`
- `existing_vs_new_bus_fault_holdout`
- `nf06_provenance_sensitivity`
- `l12_exclusion_check`

## Required Baselines

- `Ridge Regression`
- `Logistic Regression`
- `RandomForest or GradientBoosting`
- `simple ranking baseline`
- `topology-only baseline`
- `target-bus-only baseline`

## warning_checks

- target_bus / target_bus_or_component can cause target-bus memorization and must be compared against target-bus-only baseline.
- duration_s / fault_start_s / fault_clear_s are only intervention design variables, not free physical state features.
- phasor_RMS is not EMT.
- generator_speed_proxy is not direct frequency.
- temporary bus-fault injection is not engineering-grade protection.

## failed_checks

- none
