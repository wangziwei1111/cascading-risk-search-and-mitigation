# IEEE39 Strict No-Leakage GCN Usefulness Audit Execution

This document describes the existing formal audit execution artifacts. It must
stay consistent with:

`results/gcn_search/ieee39_gcn_usefulness_audit_execution/gcn_usefulness_audit_execution_summary.json`

The execution summary is still a baseline-only audit because the GCN dependency
was blocked when that audit was produced.

## Core Summary

- audit_scope: `formal_gcn_usefulness_audit_execution`
- audit_only: `true`
- production_model_saved: `false`
- gcn_trained_for_audit: `false`
- gcn_dependency_available: `false`
- gcn_dependency_status: `blocked_by_missing_gcn_dependency`
- GCN metrics: unavailable / `null`
- total_candidate_rows: `79`
- num_total_bus_fault_candidates: `39`
- no_leakage_feature_policy_passed: `true`
- forbidden_features_detected_in_inputs: `[]`
- target_bus_memorization_risk_flagged: `true`
- strict_holdouts_executed: `["random_candidate_split_baseline", "label_family_holdout", "bus_fault_holdout", "leave_one_bus_fault_out", "no_dynamic_measurement_leave_one_bus_fault_out", "existing_vs_new_bus_fault_holdout"]`
- baseline_comparison_executed: `true`
- audit_level_conclusion: `formal GCN audit blocked by missing dependency; baseline-only audit completed`
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

## Dependency Repair Follow-Up

A later dependency repair commit fixed the local Python environment:

- local `torch` import is available
- local `torch_geometric` import is available
- `dependency_blocker_resolved = true`

That repair did not rerun the formal strict no-leakage GCN audit. Therefore the
audit execution summary remains baseline-only, GCN metrics remain unavailable,
and this document must not make an early GCN usefulness conclusion.

## Next Step

Rerun the strict no-leakage GCN audit in a separate round using the repaired
environment. Until that rerun is completed, do not deploy a model and do not
retrain the reranker.
