# IEEE39 GCN Usefulness Audit Plan

This round only prepares the GCN usefulness audit plan.

It did not train GCN.
It did not run the GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.

## Why We Still Cannot Train Directly

The preview/no-leakage comparison already showed that `include_all_79` is a
leaky upper-bound. That means direct GCN training now would mix audit design
with potentially leaky inputs. So this round only prepares the audit boundary
and dry-run validator.

## Why include_all_79 Is Forbidden

`include_all_79` contains post-fault compact dynamic measurement features such
as `min_voltage_pu`, `max_frequency_hz`, `max_speed_deviation`, and
`max_rotor_angle_separation_deg`. Those measurements are downstream response
proxies and they should not be used as main GCN inputs in a usefulness audit.

## Why Future Audit Must Use No-Dynamic-Measurement Features

The no-dynamic-measurement feature set is the leakage-reduced baseline. Future
GCN usefulness audit must start from that boundary, then test whether GCN still
adds value under strict holdouts.

## Why bus_fault_holdout and leave_one_bus_fault_out Are Mandatory

Random split is too easy and can hide memorization. `bus_fault_holdout` checks
whether the model generalizes from non-bus-fault rows to bus-fault rows.
`leave_one_bus_fault_out` checks whether the model stays stable across B1-B39
one bus at a time.

## Why B1 Needs Special Handling

B1 is the only stable / low-risk bus-fault marker with `unstable_flag=false`.
Future audit must track B1 explicitly and must not silently misclassify it
without explanation.

## Why NF06 Needs Sensitivity

NF06 still carries preserved provenance warning. Future audit should run both
include-NF06 and exclude-NF06 variants to see whether conclusions are sensitive
to that row.

## Current Fixed Boundaries

- L12 stays excluded
- old formal gate stays `35 / 33 / 33`
- all bus-fault labels remain `candidate_not_formal_label`, not formal labels
- phasor_RMS is not EMT
- generator_speed_proxy is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Plan Outcome

- audit_scope: `plan_only`
- should_run_audit_now: `false`
- should_train_now: `false`
- feature_policy_passed: `true`
- required_strict_holdouts: `['random_candidate_split_baseline', 'label_family_holdout', 'bus_fault_holdout', 'leave_one_bus_fault_out', 'no_dynamic_measurement_leave_one_bus_fault_out', 'existing_vs_new_bus_fault_holdout', 'nf06_provenance_sensitivity', 'l12_exclusion_check']`
- baseline_count: `6`
- failed_checks: `[]`

## Next Step

Only run the audit dry-run validator next.
Still do not directly train GCN.
Still do not retrain the reranker.
