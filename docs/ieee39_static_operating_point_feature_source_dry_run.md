# IEEE39 Static Operating Point Feature Source Dry-Run

This round is a static operating point feature source dry-run. It does not train GCN, does not rerun the formal audit, does not run Simulink, does not export labels, does not retrain the reranker, and does not save a production model.

The goal is to fill trustworthy sources for the paper inputs `x_p`, `x_b`, and `x_l`. `x_t` is already constructed from branch outage status. Branch flow can only come from verified static/pre-fault/current-state PF or OPF. Line limit or relay threshold must have provenance. Bus load must have provenance.

## Selected Static Source

- selected_case_source: `pypower.case39`
- selected_case_source_trust_level: `standard_installed_case_loader_static_pre_fault`
- dc_pf_run_this_round: `True`
- branch_flow_source_ready: `True`
- line_limit_source_ready: `True`
- relay_threshold_source_ready: `False`
- relay_threshold_proxy_proposed: `True`
- relay_threshold_proxy_allowed_for_training_now: `False`
- bus_load_source_ready: `True`
- can_build_l01_l34_static_feature_matrix: `False`
- can_build_required_paper_features_without_proxy: `False`
- can_build_required_paper_features_with_documented_proxy: `True`

## Relay Threshold Proxy

The case provides line limits through `RATE_A`, but it does not provide a verified relay threshold table. A proxy `beta * line_limit` is proposed with project default `beta = 1.2`, but this proxy is not allowed for training now. It needs explicit approval and documentation before any training run.

## No-Leakage Rule

Post-fault dynamic measurements are not used as inputs. `min_voltage_pu`, `max_voltage_pu`, frequency, rotor angle, speed deviation, `dynamic_stress_score`, `unstable_flag`, `phasor_RMS`, and `generator_speed_proxy` are forbidden as GCN inputs. `dynamic_stress_score` and `unstable_flag` can only be labels or audit targets.

L12 remains a special case.

## Blocker

`relay threshold is available only as an unapproved beta * RATE_A proxy proposal`

## Next Step

`document and approve relay threshold proxy before paper-style label generator`

This is not deployment, not reranker retraining, and not a final engineering conclusion. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Relay Threshold Proxy Approval Follow-Up

A later approval round approved `beta * RATE_A` only as an audit-only
paper-aligned prototype proxy. The proxy uses project default `beta = 1.2` and
the `pypower.case39` branch `RATE_A` line limit. It is not a real relay
protection setting, not an engineering-grade relay threshold, and not allowed
for production.

After that approval, the L01-L34 paper feature source matrix can be built with
proxy:

- `relay_threshold_proxy_approved = true`
- `relay_threshold_proxy_allowed_for_audit_only_prototype = true`
- `relay_threshold_proxy_allowed_for_production = false`
- `can_build_required_paper_features_with_approved_proxy = true`
- `can_build_l01_l34_paper_feature_matrix_with_proxy = true`

The approval still does not train GCN, does not rerun formal audit, does not
run Simulink, does not export labels, and does not retrain the reranker. The
next step is a paper-style branch vulnerability label generator dry-run for
line-trip labels.
