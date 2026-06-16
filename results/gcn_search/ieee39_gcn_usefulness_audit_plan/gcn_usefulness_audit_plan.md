# IEEE39 GCN Usefulness Audit Plan

This round only prepares the IEEE39 v2-plus-all-bus-fault GCN usefulness audit
plan.

It did not train GCN.
It did not run the GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.

## Why No Training Yet

The previous preview/no-leakage comparison already showed that
`include_all_79_candidates` is a leaky upper-bound. So the next safe step is
not direct GCN training. The safe step is audit-plan preparation plus dry-run
validation.

## Core Plan Summary

- audit_scope: `plan_only`
- recommended_audit_type: `strict_no_leakage_gcn_usefulness_audit`
- total_candidate_rows: `79`
- num_total_bus_fault_candidates: `39`
- all_ieee39_buses_have_bus_fault_candidate: `true`
- old_formal_gate: `35 / 33 / 33`
- unstable_flag_false_buses: `['B1']`
- leakage_risk_confirmed_by_preview: `true`
- include_all_is_forbidden_for_gcn_audit: `true`
- no_dynamic_measurement_features_required: `true`

## Important Boundaries

- post-fault compact dynamic measurements cannot be used as GCN primary inputs
- B1 needs special handling because it is the only stable / low-risk bus-fault marker
- NF06 needs sensitivity checking because provenance warning is preserved
- L12 stays excluded
- all bus-fault labels remain candidate_not_formal_label, not formal labels
- phasor_RMS is not EMT
- generator_speed_proxy is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Next Step

`run audit dry-run validator before any GCN training`
