# GCN PIO Validation Log

This compact log preserves the review milestones for the RTS-79 PIO-GCN PathRank work after repository cleanup.

## Round 7

Validated the Top-K depth tradeoff, score-level ensemble feasibility, and hard-negative-aware reranking on the RTS-79 preliminary setting.

## Round 8

Removed large tracked result artifacts from Git tracking and kept compact review summaries, figures, and diagnostics.

## Round 9

Audited learned path-reranker leakage, strict held-out seed behavior, external-seed behavior, synthetic renewable robustness, and path-pattern memorization risk.

## Current Scope

The public repository scope is the GCN cascading-failure path-search reproduction and its RTS-79 PIO-GCN PathRank extensions.

## Round 10: Simulink Dynamic Validation Prototype

Added a reproducible prototype for checking whether learned path reranker / PIO-GCN Top-K ordered N-2 paths also look risky in a simplified time-domain Simulink validation flow.

New files:

```text
src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py
src/gcn_search/legacy_rts79/export_rts79_simulink_basecase.py
src/gcn_search/legacy_rts79/make_mock_simulink_dynamic_results.py
src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py
matlab/simulink_rts79/build_rts79_swing_simulink_model.m
matlab/simulink_rts79/run_rts79_dynamic_path_case.m
matlab/simulink_rts79/run_rts79_dynamic_batch.m
matlab/simulink_rts79/README.md
docs/pio_gcn_simulink_dynamic_validation_plan.md
```

Workflow:

```text
learned reranker / PIO-GCN Top-K paths
-> export two trip events per ordered N-2 path
-> generate simplified RTS-79 Simulink scaffold from MATLAB script
-> run MATLAB batch when Simulink is available
-> analyze dynamic_precision@K and OPA/dynamic overlap
```

Current limitation: this is a Simulink dynamic validation prototype only. It is not EMT, not a real engineering-grade dynamic model, not a renewable dynamic model, and mock results are only for no-MATLAB workflow testing.

## Round 11: Simplified Swing-Equation Trajectory Engine

Round 11 moves the dynamic validation scaffold from event export plus mock metrics to a real simplified electromechanical trajectory workflow.

Implemented changes:

```text
src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py --input-csv
src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py --dynamic-truth-csv
matlab/simulink_rts79/simulate_rts79_swing_case.m
matlab/simulink_rts79/run_rts79_dynamic_path_case.m
matlab/simulink_rts79/run_rts79_dynamic_batch.m
```

The MATLAB engine reads RTS-79 basecase CSV files, applies two ordered line-trip events segment by segment, integrates a simplified multi-machine swing-equation model with `ode45`, and computes frequency nadir, frequency zenith, rotor-angle separation, and approximate line-loading metrics from the trajectory. MATLAB-generated rows are marked as `result_source=simulink_swing_prototype`; mock rows remain marked as `result_source=mock`.

Dynamic precision and dynamic recall are now separated. Top-K-only simulations report `dynamic_precision@K`; `dynamic_recall@K` is emitted only when a full dynamic truth CSV is provided or the result CSV is explicitly marked as full dynamic truth.

Current limitation: this is still a simplified swing-equation prototype. It is not EMT, has no renewable dynamics, has no detailed controls, uses assumed default dynamic parameters, and supplements rather than replaces improved OPA full-truth validation.
