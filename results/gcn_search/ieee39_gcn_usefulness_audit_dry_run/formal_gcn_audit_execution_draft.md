# Formal GCN Audit Execution Draft

- draft_scope: `execution_draft_only`
- execute_this_round: `false`
- suggested_next_round_title: `Run IEEE39 strict no-leakage GCN usefulness audit`
- must_compare_against_baselines: `true`
- must_report_B1: `true`
- must_report_NF06_sensitivity: `true`
- must_report_L12_exclusion: `true`
- must_not_claim_final_engineering_conclusion: `true`

## Required Inputs

- `results\gcn_search\ieee39_dynamic_fault_type_expansion\bus_fault_smoke\batch_bus_fault_expansion_all_remaining\candidate_label_export\ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv`
- `results\gcn_search\ieee39_gcn_usefulness_audit_plan\gcn_usefulness_audit_plan.json`
- `results\gcn_search\ieee39_gcn_usefulness_audit_plan\no_leakage_feature_policy.json`
- `results\gcn_search\ieee39_gcn_usefulness_audit_plan\strict_holdout_split_manifest.json`
- `results\gcn_search\ieee39_gcn_usefulness_audit_plan\baseline_comparison_plan.json`
- `results\gcn_search\ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview\v2_plus_all_bus_fault_preview_comparison.json`
- `results\gcn_search\ieee39_dynamic_fault_type_expansion\bus_fault_smoke\batch_bus_fault_expansion_all_remaining\candidate_label_export\batch_candidate_label_export_summary.json`

## Required Splits

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

## Required Outputs

- strict holdout metrics
- per-bus leave-one-bus-fault-out report
- B1 special tracking report
- NF06 include/exclude sensitivity comparison
- L12 exclusion confirmation
- baseline comparison summary

## Required Boundary Flags

- `must_use_no_leakage_features`: `True`
- `must_keep_l12_excluded`: `True`
- `must_preserve_nf06_warning`: `True`
- `must_preserve_old_formal_gate`: `35 / 33 / 33`
- `must_not_use_post_fault_compact_measurements_as_main_inputs`: `True`

## Stopping Conditions

- forbidden feature enters proposed GCN inputs
- strict holdout split is incomplete
- baseline comparison plan is incomplete
- B1 special tracking is missing
- NF06 sensitivity is missing
- L12 exclusion is not preserved
- RL mitigation diff is non-empty
