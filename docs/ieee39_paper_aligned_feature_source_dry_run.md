# IEEE39 Paper-Aligned Feature Source Dry-Run

This round is a paper-aligned feature source dry-run. It does not train GCN, does not rerun the formal audit, does not run Simulink, does not export labels, does not retrain the reranker, and does not save a production model.

The original paper input matrix is `X_GCN` with shape `L x 4`: `x_t` topology status, `x_p` relay ratio, `x_b` branch flow, and `x_l` endpoint load. In Chinese: `x_t` means current branch outage status, `x_p` means branch-flow-to-relay-threshold ratio, `x_b` means current-state branch flow, and `x_l` means the larger load at the two endpoint buses.

## Source Readiness

- `x_t` is available from the current outaged branch set.
- `x_p` still needs verified branch flow and relay threshold, or a documented line-limit proxy.
- `x_b` still needs verified current-state PF/OPF branch flow.
- `x_l` still needs verified current-state bus load.
- branch_line_graph_ready: `True`
- num_branch_nodes: `34`
- branch_flow_source_ready: `False`
- line_limit_source_ready: `False`
- relay_threshold_source_ready: `False`
- bus_load_source_ready: `False`
- can_build_required_paper_features: `False`
- can_build_l01_l34_feature_matrix: `False`

## No-Leakage Rule

Post-fault dynamic measurement cannot replace these paper inputs. `min_voltage_pu`, `max_voltage_pu`, frequency, rotor angle, speed deviation, `dynamic_stress_score`, `unstable_flag`, `phasor_RMS`, and `generator_speed_proxy` are not used as GCN inputs here. `dynamic_stress_score` and `unstable_flag` can only be labels or audit targets.

If only line limit is found but no relay threshold is found, the next step must explicitly decide whether a documented relay threshold proxy from verified line limit is allowed. This round does not make that decision.

L12 remains a special case and the old gate is unchanged.

## Blocker

`verified current-state branch flow, line limit or relay threshold, and endpoint bus load sources are incomplete`

## Next Step

`add or generate verified current-state PF/OPF branch flow, line limit, and bus load sources before label generator`

This is not deployment, not reranker retraining, and not a final engineering conclusion. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.
