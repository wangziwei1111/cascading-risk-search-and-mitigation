# IEEE39 Single-Outage Label Loop Dry-Run

This is a controlled single-outage state label loop dry-run. It does not train GCN, does not rerun formal audit, does not run new Simulink, does not export formal labels, does not retrain the reranker, and does not save a production model.

There is no deployment in this round.

## Plain-Language Purpose

The previous base-state pilot only asked: from the original grid, what happens if one line is tripped? All 33 available non-L12 labels were negative. That means the base-state pilot alone cannot train a useful classifier because it has no positive branch-risk samples. This round therefore only prepares the next task list: after line `i` has already been outaged, evaluate a future candidate line `k`.

## Planned Loop

- dry_run_scope: `single_outage_label_loop_dry_run`
- paper_graph_node_type: `branch`
- paper_graph_edge_rule: `shared_endpoint_bus`
- num_single_outage_states_planned: `34`
- num_state_branch_pairs_planned: `1122`
- num_pairs_excluded_due_to_same_branch: `34`
- num_pairs_excluded_due_to_l12_special: `66`
- num_pairs_planned_for_future_generation: `1056`
- num_pairs_available_from_existing_artifacts: `0`

The pair label means: `y_state_i[k] = 1` if, after branch `i` is already outaged, disconnecting branch `k` causes critical risk or an unacceptable dynamic proxy. `0` means no critical risk. Unknown, timeout, not simulated, or special cases remain null/excluded. This dry-run does not fabricate 0/1 labels.

## Base-State Review

- base_state_num_label_slots: `34`
- base_state_num_labels_available: `33`
- base_state_num_positive_labels: `0`
- base_state_num_negative_labels: `33`
- base_state_num_excluded_labels: `1`
- base_state_all_available_labels_negative: `True`
- training_risk_if_using_base_state_only: `True`
- recommendation: `do not train on base-state labels only; extend to single-outage state labels first`

## Boundaries

The `beta * RATE_A` threshold is an audit-only proxy. It is not a real relay setting and not an engineering-grade protection threshold. Bus-fault labels are unused. Line-trip labels remain first priority. L12 stays special/excluded. NF06 warning is preserved.

No post-fault dynamic measurement features are used as inputs. Dynamic outputs can only be future labels or targets. Label-derived flags are not inputs. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Status

- can_generate_single_outage_labels_now: `False`
- can_export_formal_single_outage_labels_now: `False`
- no_leakage_policy_passed: `True`
- final_engineering_conclusion: `False`
- should_train_gcn_now: `False`
- should_rerun_formal_audit_now: `False`
- should_export_formal_labels_now: `False`
- should_retrain_reranker_now: `False`
- should_deploy_model: `False`
- blocker_if_any: `no approved reusable single_outage_state x next_branch label artifacts are available; this round only prepares the controlled loop dry-run plan`

## Recommended Next Step

`implement controlled generation runner for selected single-outage pilot pairs in a separate round`

## Follow-Up: Selected Pilot Pair Runner Dry-Run

The selected pilot pair runner dry-run chooses a 32-row subset from the 1056 planned `single_outage_state x next_branch` candidates. It is a planning artifact only: it does not run all 1056 pairs, does not run Simulink, and leaves all future label values as null.

## Follow-Up: Selected Pair Execution Approval

The selected pair execution approval round approved the 32-row pilot scope but did not execute it because the safe controlled backend was not available. Blocked, timeout, failed, or unknown cases were not converted into 0/1 labels.

## Follow-Up: Backend Repair Skeleton

The backend repair follow-up adds the selected-32-only controlled runner and supporting contracts needed for a later manually approved execution round. It still does not train GCN, does not export formal labels, and does not rerun any audit.
