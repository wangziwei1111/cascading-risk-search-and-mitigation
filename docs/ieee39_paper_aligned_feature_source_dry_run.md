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

## Static Operating Point Follow-Up

A later static operating point dry-run found a local standard case loader:
`pypower.case39`. Using that static/pre-fault case, the dry-run successfully ran
DC PF without Simulink and mapped L01-L34 to static branch flow, `RATE_A` line
limit, and endpoint bus load sources.

- `selected_case_source = pypower.case39`
- `dc_pf_run_this_round = true`
- `branch_flow_source_ready = true`
- `line_limit_source_ready = true`
- `bus_load_source_ready = true`
- `relay_threshold_source_ready = false`
- `relay_threshold_proxy_proposed = true`
- `relay_threshold_proxy_allowed_for_training_now = false`

The result improves the source situation but still does not authorize training:
the relay threshold exists only as a proposed `beta * RATE_A` proxy and needs
explicit approval before it can be used in a paper-aligned GCN input.

## Relay Threshold Proxy Approval Follow-Up

A later approval round approved `beta * RATE_A` as an audit-only
paper-aligned prototype proxy. `beta = 1.2` comes from the project default, and
`RATE_A` comes from the `pypower.case39` branch line-limit field.

This approval means the L01-L34 `L x 4` paper feature source matrix can be
built with proxy, but only for proxy-based audit preparation. It is not a real
relay protection setting, not an engineering-grade threshold, not allowed for
production, and not a GCN usefulness conclusion.

- `relay_threshold_proxy_approved = true`
- `relay_threshold_proxy_allowed_for_audit_only_prototype = true`
- `relay_threshold_proxy_allowed_for_production = false`
- `can_build_required_paper_features_with_approved_proxy = true`
- `can_build_l01_l34_paper_feature_matrix_with_proxy = true`

Branch vulnerability labels are still not generated in this approval round.
The next step is a paper-style branch vulnerability label generator dry-run for
line-trip labels.
