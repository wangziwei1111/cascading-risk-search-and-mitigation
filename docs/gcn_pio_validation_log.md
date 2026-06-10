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

## Round 15: Real Learned-Reranker Top-K Event-Driven Dynamic Validation

Round 15 connects the event-driven closed-loop dynamic prototype to real learned path-reranker Top-K ranking artifacts when a local per-path CSV is available.

Added or updated:

```text
src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py
src/gcn_search/legacy_rts79/prepare_dynamic_method_comparison_topk.py
matlab/simulink_rts79/run_real_topk_event_driven_dynamic_validation.m
docs/pio_gcn_simulink_real_topk_event_driven_validation.md
tests/test_real_topk_dynamic_pipeline.py
tests/test_dynamic_method_comparison_inputs.py
```

The preparation script now searches common local ignored ranking directories and writes:

```text
results/gcn_search/simulink_dynamic_real_topk/real_topk_input_paths.csv
```

with `case_id`, `source_seed`, `path_rank`, `path`, `first_line`, `second_line`, `pio_score`, `paper_score`, `lodf_score`, `reranker_score`, `opa_is_critical`, and `opa_total_load_shed_mw`.

Default behavior is strict: if no real per-path ranking CSV is available, the script fails. Demo fallback is only enabled by `--allow-demo-fallback` and is for interface testing only.

Method-comparison input preparation can create learned-reranker, PIO-GCN, and LODF Top-K dynamic input CSVs from the same per-path table when the relevant score columns exist.

Required validation commands for this round:

```powershell
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
git diff -- src/rl_mitigation scripts/rl_mitigation
```

If no real per-path ranking CSV is found in the local checkout, the correct status is: real per-path ranking CSV not available; real Top-K dynamic validation was not run.

Local validation result:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py
18 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

Automatic real CSV search was run without demo fallback. After excluding generated `simulink_dynamic*` artifacts and non-RTS-79 files, no real learned-reranker per-path ranking CSV was found in the local checkout. Therefore real Top-K dynamic validation was not run in this round. RL mitigation files were not modified.

## Round 16: Per-Path Ranking Export And Real Top-K Dynamic Smoke Pipeline

Round 16 addresses the main Round 15 blocker: the checkout did not contain a real learned-reranker per-path ranking CSV. The new workflow adds a reproducible local export path and a one-step dynamic smoke pipeline.

Added:

```text
src/gcn_search/legacy_rts79/export_path_reranker_per_path_ranking.py
src/gcn_search/legacy_rts79/run_real_topk_dynamic_validation_pipeline.py
src/gcn_search/legacy_rts79/summarize_real_topk_dynamic_validation.py
docs/pio_gcn_simulink_real_topk_dynamic_smoke.md
tests/test_export_path_reranker_per_path_ranking.py
tests/test_real_topk_dynamic_validation_pipeline.py
tests/test_real_topk_dynamic_summary.py
```

The per-path exporter normalizes local learned-reranker artifacts into:

```text
learned_mlp_per_path_ranking.csv
```

with the required path, score, OPA label, split, and method fields. This full CSV is a local ignored runtime artifact and should not be committed. If dataset/model artifacts are unavailable, the exporter fails explicitly and asks the user to run the dataset builder and training script first.

The pipeline wrapper can generate dynamic inputs and a MATLAB command file with `--skip-matlab`, or attempt MATLAB execution with `--run-matlab`. The summary script reports dynamic precision, OPA/dynamic overlap, and relay/security counts. It does not report dynamic recall without full dynamic truth.

Round 16 validation commands:

```powershell
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
git diff -- src/rl_mitigation scripts/rl_mitigation
```

Local validation result:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py
23 passed
```

Real export attempt:

```text
python src/gcn_search/legacy_rts79/export_path_reranker_per_path_ranking.py --dataset-dir results/gcn_search/path_reranker_dataset --model-dir results/gcn_search/path_reranker_models --output-dir results/gcn_search/simulink_dynamic_real_per_path_ranking --method learned_mlp_reranker_strict --split test --top-k 20 50 100 --retrain-if-missing
RuntimeError: path reranker dataset/model artifacts not available; run build_path_reranker_dataset.py and train_path_reranker.py first.
```

Pipeline attempt:

```text
python src/gcn_search/legacy_rts79/run_real_topk_dynamic_validation_pipeline.py --top-k 20 --max-cases 20 --skip-matlab --output-dir results/gcn_search/simulink_dynamic_real_pipeline
RuntimeError: path reranker dataset/model artifacts not available; run build_path_reranker_dataset.py and train_path_reranker.py first.
```

Therefore no real learned-reranker per-path ranking CSV was exported in this checkout, no retraining was performed, MATLAB was not run, and no real Top20/Top50/Top100 dynamic validation result was produced in Round 16.

Artifact check:

```text
python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

RL mitigation files were not modified.

## Round 17: Rebuilt Learned-Reranker Per-Path Ranking Export and Top20 Dynamic Smoke

Round 17 fixes the upstream blocker from Round 16. Git history contained historical path-reranker source scripts, so the source files were restored and adapted into a minimal reproducible smoke pipeline:

```text
src/gcn_search/legacy_rts79/build_path_reranker_dataset.py
src/gcn_search/legacy_rts79/train_path_reranker.py
src/gcn_search/legacy_rts79/evaluate_path_reranker_strict_heldout.py
```

The restored pipeline generated local ignored artifacts:

```text
results/gcn_search/path_reranker_dataset/path_reranker_dataset.csv
results/gcn_search/path_reranker_models/path_reranker_model.pkl
results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking.csv
```

Dataset stats:

```text
num_samples = 1000
num_critical = 17
positive_ratio = 0.017
train_seeds = 20260722, 20260723, 20260724
test_seeds = 20260726
smoke = true
```

MATLAB Top20 preliminary dynamic smoke was run through:

```powershell
python src/gcn_search/legacy_rts79/run_real_topk_dynamic_validation_pipeline.py --retrain-if-missing --smoke --top-k 20 --max-cases 20 --max-paths-per-seed 200 --run-matlab --output-dir results/gcn_search/simulink_dynamic_real_pipeline
```

Compact summary:

```text
result_scope = top20_preliminary_dynamic_smoke
num_dynamic_cases = 20
dynamic_precision_at_k = 1.0
opa_critical_and_dynamic_unstable_count = 1
opa_critical_but_dynamic_stable_count = 0
opa_noncritical_but_dynamic_unstable_count = 19
cases_with_security_redispatch_or_load_shed = 0
cases_with_passive_relay_trip = 20
total_dynamic_load_shed_mw = 0.0
matlab_executed = true
```

No dynamic recall is reported because no full dynamic truth is available. This remains a simplified swing-equation Top20 preliminary dynamic smoke, not a formal engineering dynamic stability conclusion.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py
26 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

RL mitigation files were not modified. Generated `.pkl`, `.slx`, `.mat`, full per-path ranking, and raw dynamic artifacts remain local ignored artifacts and are not intended for commit.

## Round 18: Non-Degeneracy Diagnostics and Event-Driven Calibration

Round 18 fixes the documentation mismatch by treating the tracked CSV as authoritative:

```text
opa_critical_and_dynamic_unstable_count = 1
opa_noncritical_but_dynamic_unstable_count = 19
```

The default Top20 dynamic smoke showed:

```text
dynamic_precision_at_k = 1.0
cases_with_passive_relay_trip = 20
cases_with_security_redispatch_or_load_shed = 0
degeneracy_warning = true
```

This is a non-degeneracy warning. It does not prove the pipeline is wrong; it indicates that default dynamic scale parameters are too sensitive for interpretation.

Added:

```text
src/gcn_search/legacy_rts79/analyze_dynamic_smoke_degeneracy.py
matlab/simulink_rts79/calibrate_event_driven_dynamic_scales.m
src/gcn_search/legacy_rts79/compare_default_vs_calibrated_dynamic_smoke.py
```

Small calibration grid recommendation:

```text
line_loading_scale = 0.005
coupling_scale = 0.5
damping_scale = 1.0
inertia_scale = 1.0
relay_beta = 1.2
```

Calibrated Top20 result:

```text
dynamic_precision_at_k = 1.0
cases_with_passive_relay_trip = 0
cases_with_security_redispatch_or_load_shed = 20
total_dynamic_load_shed_mw = 231.32117491281207
opa_critical_and_dynamic_unstable_count = 1
opa_noncritical_but_dynamic_unstable_count = 19
degeneracy_warning = true
```

Calibration removed the all-passive-relay-trip degeneracy, but all cases remain dynamically unstable, so the calibrated smoke still carries a degeneracy warning. No dynamic recall is reported because no full dynamic truth exists. This remains a simplified swing-equation preliminary dynamic smoke, not EMT, not full OPF, and not an engineering-grade dynamic stability conclusion.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py
30 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

RL mitigation files were not modified. Generated `.pkl`, `.slx`, `.mat`, raw per-case calibration outputs, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.
