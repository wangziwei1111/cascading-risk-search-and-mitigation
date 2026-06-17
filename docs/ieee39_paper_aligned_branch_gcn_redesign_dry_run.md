# IEEE39 Paper-Aligned Branch GCN Redesign Dry-Run

This round is a paper-aligned branch GCN redesign dry-run. It does not train GCN, does not rerun the formal audit, does not run Simulink, does not export labels, does not retrain the reranker, and does not save a production model.

The paper method is not a candidate-row graph. It maps each power-system branch or line to one GCN node, and two branch nodes are connected when the original branches share one bus.

The paper input is a four-column branch feature matrix: topology status, relay ratio, branch flow, and endpoint load. The paper output is a branch vulnerability vector. The kth value means whether disconnecting branch k from the current state causes load shedding.

Our previous IEEE39 audit used a candidate similarity graph, where candidate rows were graph nodes. That design is deprecated for the next paper-aligned prototype because it is not the physical branch-as-node graph described by the paper.

Current scenario-level bus-fault labels are not directly equivalent to paper branch vulnerability labels. Line-trip labels should be the first priority for a paper-aligned prototype; bus-fault labels are a later extension and should not be forced into the original branch vulnerability structure.

Post-fault dynamic measurements cannot be used as GCN inputs. Dynamic_stress_score and unstable_flag can only be labels or audit targets, not inputs.

Phasor_RMS is not EMT. Generator_speed_proxy is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Dry-Run Status

- dry_run_scope: paper_aligned_branch_gcn_redesign_dry_run
- paper_graph_node_type: branch
- paper_graph_edge_rule: shared_endpoint_bus
- previous_repo_graph_type: candidate_similarity_graph
- proposed_graph_type: branch_as_node_physical_line_graph
- can_build_branch_line_graph: True
- can_build_required_paper_features: False
- can_build_paper_labels_from_existing_data: False
- bus_fault_labels_directly_paper_aligned: False
- line_trip_labels_first_priority: True
- forbidden_features_detected_in_inputs: []
- final_engineering_conclusion: False

## Branch Graph

- num_branch_nodes: 34
- num_graph_edges: 57
- adjacency_density: 0.101604
- graph_is_candidate_similarity_graph: False
- graph_uses_physical_branch_connectivity: True

## Feature Readiness

- available_required_paper_features: ['topology_status_feature from current outaged branch set']
- missing_required_paper_features: ['relay_ratio_feature: verified current-state branch flow and relay threshold source', 'branch_flow_feature: verified OPF/PF/current-state branch flow source', 'endpoint_load_feature: verified current-state bus load source']
- no_leakage_feature_policy_passed: True

## Label Readiness

- paper_label_type: branch_vulnerability_binary_vector
- label_shape: num_states x num_branches
- can_build_paper_labels_from_existing_data: False

## Blocker And Next Step

- blocker_if_any: verified pre-fault/current-state branch flow, line limit, and bus load sources are incomplete; paper-style branch vulnerability label generator is not available yet
- recommended_next_step: add verified pre-fault/current-state branch flow, line limit, and bus load sources first

This is preparation for a future audit-only paper-aligned branch-as-node GCN prototype. It is not deployment and not reranker retraining.

## Consistency Follow-Up

A later consistency check aligned the strict no-leakage audit execution document
with the post-repair audit summary. The current execution summary records
`gcn_trained_for_audit = true`,
`gcn_dependency_status = torch_and_torch_geometric_available`, and the
audit-level conclusion that current evidence does not support GCN usefulness
over simpler baselines yet.

This does not change the paper-aligned dry-run status above: the branch-as-node
graph can be built, but the required paper features and paper-style branch
vulnerability labels are still not ready.

## Feature Source Dry-Run Follow-Up

A later feature-source dry-run inventories the static/pre-fault/current-state
sources needed for the paper input matrix `X_GCN = L x 4`. The result keeps the
same method direction: branch nodes with shared endpoint bus edges are ready,
but the verified inputs for `x_p`, `x_b`, and `x_l` are still incomplete.

- `branch_line_graph_ready = true`
- `num_branch_nodes = 34`
- `branch_flow_source_ready = false`
- `line_limit_source_ready = false`
- `relay_threshold_source_ready = false`
- `bus_load_source_ready = false`
- `can_build_required_paper_features = false`
- `can_build_l01_l34_feature_matrix = false`

This follow-up also keeps the no-leakage rule: post-fault dynamic measurements
cannot replace branch flow, relay threshold, or endpoint load inputs.

## Static Operating Point Feature Source Follow-Up

A later static operating point dry-run selected `pypower.case39` as a standard
installed static case loader and ran DC PF without Simulink. This gives
L01-L34 static branch flow, `RATE_A` line limit, and endpoint bus load sources.
However, the relay threshold is still not a verified source; only a
`beta * RATE_A` proxy is proposed.

- `dc_pf_run_this_round = true`
- `branch_flow_source_ready = true`
- `line_limit_source_ready = true`
- `bus_load_source_ready = true`
- `relay_threshold_source_ready = false`
- `relay_threshold_proxy_proposed = true`
- `relay_threshold_proxy_allowed_for_training_now = false`

Therefore the paper-aligned feature source is closer, but still not approved
for training until the relay-threshold proxy is documented and approved.
