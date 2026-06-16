# IEEE39 Strict No-Leakage GCN Usefulness Audit Execution

This round is formal GCN usefulness audit execution.
It is audit-only, not production training.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not modify RL mitigation.

## Core Summary

- audit_scope: `formal_gcn_usefulness_audit_execution`
- audit_only: `true`
- gcn_trained_for_audit: `false`
- gcn_dependency_status: `blocked_by_missing_gcn_dependency`
- total_candidate_rows: `79`
- num_total_bus_fault_candidates: `39`
- no_leakage_feature_policy_passed: `true`
- forbidden_features_detected_in_inputs: `[]`
- target_bus_memorization_risk_flagged: `true`
- strict_holdouts_executed: `["random_candidate_split_baseline", "label_family_holdout", "bus_fault_holdout", "leave_one_bus_fault_out", "no_dynamic_measurement_leave_one_bus_fault_out", "existing_vs_new_bus_fault_holdout"]`
- baseline_comparison_executed: `true`
- final_engineering_conclusion: `false`
- should_retrain_reranker_now: `false`
- should_deploy_model: `false`

## Important Boundary Notes

- no-leakage features only
- forbidden features did not enter inputs
- target_bus memorization risk still exists, so target-bus-only baseline must be reported
- bus_fault_holdout and leave-one-bus-fault-out are mandatory
- B1 is reported explicitly
- NF06 sensitivity is reported explicitly
- L12 exclusion is confirmed explicitly
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
- this is not a final engineering conclusion

## Audit-Level Conclusion

formal GCN audit blocked by missing dependency; baseline-only audit completed

## Next Step

repair the local GCN dependency environment and rerun the strict no-leakage audit; still do not deploy and do not retrain the reranker
