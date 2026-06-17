# IEEE39 Relay Threshold Proxy Approval

This round is relay threshold proxy approval only. It did not train GCN, did not rerun formal audit, did not run Simulink, did not export labels, did not retrain the reranker, and did not save a production model.

## Approved Audit-Only Proxy

`beta * RATE_A` is approved as an audit-only paper-aligned prototype proxy for IEEE39 paper-style branch GCN feature preparation.

- proxy_formula: `beta * RATE_A`
- beta_value: `1.2`
- beta_value_source: `project default beta = 1.2`
- line_limit_source: `pypower.case39 branch RATE_A`
- relay_threshold_proxy_approved: `True`
- relay_threshold_proxy_allowed_for_audit_only_prototype: `True`
- relay_threshold_proxy_allowed_for_production: `False`

This proxy is not a real relay protection setting, not an engineering-grade relay threshold, and not allowed for production. If a future real protection threshold source is obtained, this proxy should be replaced. Any GCN audit that uses this proxy must be marked proxy-based.

## Feature Readiness

Branch flow, line limit, and bus load come from the `pypower.case39` static/pre-fault source. With this approved audit-only proxy, the L01-L34 L x 4 paper feature source matrix can now be built with proxy.

- branch_flow_source_ready: `True`
- line_limit_source_ready: `True`
- bus_load_source_ready: `True`
- can_build_required_paper_features_without_proxy: `False`
- can_build_required_paper_features_with_approved_proxy: `True`
- can_build_l01_l34_paper_feature_matrix_with_proxy: `True`

There are still no branch vulnerability labels in this approval round. The next step is a paper-style branch vulnerability label generator dry-run for line-trip labels.

## No-Leakage Policy

Post-fault dynamic measurements are not used as inputs. `dynamic_stress_score` and `unstable_flag` can only be labels or audit targets. Label-derived flags are not allowed as inputs.

- forbidden_features_detected_in_inputs: `[]`
- no_leakage_policy_passed: `True`
- l12_special_case_preserved: `True`

## Boundaries

This is not deployment, not reranker retraining, and not a final engineering conclusion. It provides no GCN usefulness conclusion. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Label Generator Dry-Run Follow-Up

A later paper-style branch vulnerability label generator dry-run uses this
approved proxy only for feature generation. It does not export formal labels
and does not train GCN.

The dry-run plans a `num_states x num_branches` label structure for line-trip
labels. It keeps bus-fault labels outside the directly paper-aligned branch
vulnerability vector, preserves the L12 special case, and keeps NF06 warnings.

- `label_shape_target = num_states x num_branches`
- `num_states_planned = 35`
- `num_state_branch_pairs_planned = 1156`
- `can_generate_full_state_branch_label_matrix_now = false`
- `recommended_next_step = implement controlled line-trip label generation loop for paper-style branch vulnerability labels`

## Base-State Label Pilot Follow-Up

A later base-state branch vulnerability label pilot continues to use
`beta * RATE_A` only as an audit-only feature-generation proxy. It does not
make the proxy a real relay setting, does not train GCN, does not rerun formal
audit, does not run Simulink, does not export formal labels, and does not
retrain the reranker.

The pilot covers only `base_state x L01-L34`, reuses existing training-ready
handwired line-trip artifacts first, keeps bus-fault labels out of the branch
vulnerability vector, and preserves L12 as a special/excluded
islanding-timeout case. Pilot labels are not formal training labels.

- `pilot_scope = base_state_branch_vulnerability_label_pilot`
- `num_label_slots = 34`
- `num_labels_available = 33`
- `num_labels_excluded = 1`
- `bus_fault_labels_used = false`
- `pilot_labels_are_formal_training_labels = false`
