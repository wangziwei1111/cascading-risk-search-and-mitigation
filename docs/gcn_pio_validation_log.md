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

## Round 12: Real Top-K Dynamic Validation And Calibration

Round 12 adds the workflow needed to move from demo cases to real learned-reranker Top-K dynamic review.

New components:

```text
src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py
src/gcn_search/legacy_rts79/check_simulink_dynamic_sanity_artifacts.py
src/gcn_search/legacy_rts79/analyze_opa_dynamic_disagreement.py
matlab/simulink_rts79/check_rts79_swing_model_sanity.m
matlab/simulink_rts79/calibrate_rts79_swing_scales.m
matlab/simulink_rts79/run_real_topk_dynamic_validation.m
docs/pio_gcn_simulink_real_topk_validation.md
```

The real Top-K preparation script fails explicitly when a per-path ranking CSV is missing; it does not silently fall back to demo paths. The calibration scripts produce `no_disturbance_sanity.csv`, `swing_scale_grid.csv`, and `recommended_swing_options.json` as local ignored artifacts. OPA/dynamic disagreement diagnostics separate static OPA-critical but dynamic-stable cases from static non-critical but dynamic-unstable cases.

Current limitation: real Top-K dynamic precision depends on a local per-path ranking CSV. Demo precision must not be reported as a formal dynamic conclusion. No full dynamic truth means no dynamic recall.

Local validation note: in the current repository checkout, no tracked real per-path learned-reranker ranking CSV was found, so the end-to-end real Top-K entry was exercised with explicit demo fallback only. The no-disturbance sanity check passed with frequency max deviation 0 Hz, rotor-angle separation about 35.66 degrees, and max line loading ratio about 1.38. The full scale grid calibration was attempted but did not finish within the local timeout, so the temporary recommended options remain sanity-passing default prototype values until a complete calibration run is available.

## Round 13: Relay Threshold vs Security Constraint

Round 13 adds a prototype distinction between line security limits and relay thresholds.

Key logic:

```text
loading_ratio <= 1.0: no overload action
1.0 < loading_ratio <= beta: security redispatch/load shedding approximation
loading_ratio > beta: passive relay trip
```

The default `relay_beta` is `1.2`. This means `loading_ratio > 1.0` is a security constraint violation, not a relay trip by itself. The Simulink prototype now writes `dynamic_case_event_log_<case_id>.csv` with `active_trip_first_line`, `active_trip_second_line`, `security_redispatch_or_load_shed`, and `passive_relay_trip` event types. Summary rows include passive relay trip counts, security redispatch counts, dynamic load shedding, and separate maximum security and relay violation loading ratios.

Current limitation: the redispatch/load shedding step is an approximation near overloaded branch terminal buses. It is not a full OPF, not EMT, and not an engineering-grade dynamic model.

## Round 14: Event-Driven Closed-Loop Dynamic Prototype

Round 13 separated relay/security events in post-processing. Round 14 upgrades the prototype to an event-driven closed-loop simulation:

- scheduled active trips change `offlineLines` before later integration segments;
- passive relay trips add the tripped line to `offlineLines`, so subsequent segments rebuild topology without that line;
- security redispatch/load shedding updates `currentLoads` and scales the subsequent `Pm` approximation through `update_swing_power_after_load_shed.m`;
- the event loop repeats until simulation end, `max_passive_trip_rounds`, or `max_event_rounds`.

Round 14 also adds two MATLAB demos:

- mild overload demo: validates `1.0 < loading_ratio <= beta` causes `security_redispatch_or_load_shed` and no passive relay trip;
- severe overload demo: validates `loading_ratio > beta` causes passive relay trip.

Current limitation: this is still a simplified swing-equation prototype. Redispatch/load shedding is not full OPF, relay logic is not an engineering-grade protection model, and demos are not formal dynamic stability conclusions.
