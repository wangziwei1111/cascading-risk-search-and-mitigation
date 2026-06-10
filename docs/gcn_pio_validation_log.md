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

## Round 24: TopK Coverage Fix And Event Strength Calibration

Round 24 first fixes non-smoke TopK case coverage, then calibrates post-fault event strength so the simplified dynamic layer is no longer all-stable or all-unstable. This remains a preliminary diagnostic result, not a formal dynamic stability conclusion.

Coverage diagnosis after the fix:

| method | Top50 coverage | Top100 coverage |
| --- | ---: | ---: |
| learned_mlp | 1.0000 | 1.0000 |
| pio_gcn | 1.0000 | 1.0000 |
| lodf | 1.0000 | 1.0000 |

The Round 23 shortfall was caused by duplicate ordered N-2 paths in the input ranking. Round 24 uses `--ensure-unique-paths --fill-to-k` to fill from deeper ranks until enough unique valid paths are available.

Recommended event strength options:

```text
frequency_unstable_threshold_hz = 49.3
rotor_angle_unstable_threshold_deg = 180.0
damping_scale = 2.0
inertia_scale = 2.0
coupling_scale = 0.2
line_loading_scale = 0.002
relay_beta = 1.5
load_shed_step_fraction = 0.01
```

Event-strength calibrated result:

| method | Top50 precision | Top100 precision | Top50 mean stress | Top100 mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_mlp | 0.3000 | 0.2700 | 0.0985 | 0.0871 |
| pio_gcn | 0.3400 | 0.3600 | 0.0997 | 0.1029 |
| lodf | 0.2800 | 0.3000 | 0.0887 | 0.0900 |

The event-strength calibrated dynamic layer is nondegenerate:

```text
all_stable_warning = false
all_unstable_warning = false
nondegenerate_dynamic_layer = true
dynamic_discrimination_signal = false
allowed_next_step = report_no_dynamic_advantage_preliminary
```

OPA/dynamic alignment remains mixed. Learned Top100 has `corr(stress, OPA shed) = 0.1211` and `corr(dynamic_unstable, OPA critical) = 0.1461`, but learned Top100 precision is lower than PIO-GCN, so there is no learned dynamic advantage observed.

Commands:

```powershell
python src/gcn_search/legacy_rts79/prepare_dynamic_method_comparison_topk.py --input-csv results/gcn_search/simulink_dynamic_real_per_path_ranking_non_smoke/learned_mlp_per_path_ranking.csv --output-dir results/gcn_search/simulink_dynamic_method_comparison_inputs_non_smoke_top100 --top-k 100 --ensure-unique-paths --fill-to-k

python src/gcn_search/legacy_rts79/export_dynamic_method_comparison_cases.py --input-root results/gcn_search/simulink_dynamic_method_comparison_inputs_non_smoke_top100 --output-root results/gcn_search/simulink_dynamic_method_comparison_cases_non_smoke --top-k 50 100 --event-1-time 1.0 --event-2-time 5.0 --simulation-end-time 10.0

python src/gcn_search/legacy_rts79/diagnose_dynamic_topk_case_coverage.py --ranking-csv results/gcn_search/simulink_dynamic_real_per_path_ranking_non_smoke/learned_mlp_per_path_ranking.csv --input-root results/gcn_search/simulink_dynamic_method_comparison_inputs_non_smoke_top100 --cases-root results/gcn_search/simulink_dynamic_method_comparison_cases_non_smoke --results-root results/gcn_search/simulink_dynamic_method_comparison_results_non_smoke_event_strength --output-dir results/gcn_search/simulink_dynamic_method_comparison_non_smoke_summary

python src/gcn_search/legacy_rts79/calibrate_post_fault_event_strength.py --cases-root results/gcn_search/simulink_dynamic_method_comparison_cases_non_smoke --basecase-path results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json --output-dir results/gcn_search/simulink_dynamic_event_strength_calibration --results-root results/gcn_search/simulink_dynamic_method_comparison_results_non_smoke --max-cases-per-group 30 --run-matlab
```

MATLAB rerun:

```matlab
run_dynamic_method_comparison_batch( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_cases_non_smoke", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_results_non_smoke_event_strength", ...
  "../../results/gcn_search/simulink_dynamic_event_strength_calibration/recommended_event_strength_options.json", ...
  100 ...
)
```

No dynamic recall is reported because no full dynamic truth exists. Generated `.slx`, `.mat`, full per-case results, full per-path ranking, event logs, and raw trajectories remain local ignored artifacts and are not intended for commit.

Validation to run:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py tests/test_post_fault_sanity_ladder.py tests/test_dynamic_interpretability_gate.py tests/test_negative_control_v3_summary.py tests/test_dynamic_method_comparison_cases.py tests/test_dynamic_method_comparison_analysis.py tests/test_dynamic_rank_depth_curve.py tests/test_non_smoke_path_reranker_dataset.py tests/test_non_smoke_dynamic_method_comparison.py tests/test_non_smoke_label_dynamic_alignment.py tests/test_dynamic_topk_case_coverage.py tests/test_post_fault_event_strength_calibration.py tests/test_event_strength_dynamic_summary.py

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

## Round 19: Dynamic Instability Reasons and Negative Controls

Round 19 diagnoses the calibrated Top20 result from Round 18. The goal is to answer whether the event-driven dynamic validation layer has discrimination, or whether it still marks almost every tested path as unstable.

Added:

```text
src/gcn_search/legacy_rts79/analyze_dynamic_instability_reasons.py
src/gcn_search/legacy_rts79/compute_dynamic_stress_score.py
src/gcn_search/legacy_rts79/prepare_dynamic_negative_control_inputs.py
src/gcn_search/legacy_rts79/run_dynamic_negative_control_pipeline.py
matlab/simulink_rts79/run_dynamic_negative_control_batch.m
tests/test_dynamic_instability_reasons.py
tests/test_dynamic_stress_score.py
tests/test_dynamic_negative_controls.py
docs/pio_gcn_simulink_dynamic_negative_controls.md
```

The MATLAB stability classifier was checked. Security redispatch/load shedding is not directly treated as `dynamic_unstable`. The calibrated Top20 instability reasons are frequency and rotor-angle based:

```text
num_cases = 20
dynamic_unstable_count = 20
frequency_nadir_below_threshold = 20
rotor_angle_above_threshold = 20
relay_violation_not_eliminated = 0
sim_failed = 0
passive_relay_trip_count = 0
security_redispatch_count = 38
```

Round 19 negative-control command:

```powershell
python src/gcn_search/legacy_rts79/run_dynamic_negative_control_pipeline.py `
  --input-csv results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking.csv `
  --output-dir results/gcn_search/simulink_dynamic_negative_controls `
  --top-k 20 `
  --run-matlab `
  --options-json-path results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json
```

Negative-control result:

| group | dynamic precision@20 | passive relay trips | security actions | mean dynamic stress |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 1.0000 | 0 | 20 | 4.9614 |
| low_score_top20 | 1.0000 | 0 | 15 | 5.1883 |
| random_top20 | 1.0000 | 0 | 18 | 4.9650 |
| line_order_top20 | 1.0000 | 0 | 12 | 4.9756 |

Summary:

```text
global_degeneracy_warning = true
dynamic_discrimination_signal = false
matlab_executed = true
```

Interpretation: the calibrated dynamic layer still lacks discrimination because all four groups are 20/20 dynamically unstable and the learned group is not more stressful than all controls. Therefore dynamic precision@20 should not be used as a performance claim at this stage. No dynamic recall is reported because no full dynamic truth set exists.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py
35 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

RL mitigation files were not modified. Generated `.pkl`, `.slx`, `.mat`, dynamic case folders, raw event logs, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.

## Round 20: Swing Equilibrium Sanity and Threshold Sensitivity

Round 20 addresses the Round 19 problem that all negative-control groups were 20/20 dynamically unstable. The aim is not to tune thresholds for a nicer precision number; the aim is to check whether the swing-equation dynamic layer has a stable no-trip baseline and whether threshold sensitivity gives any diagnostic separation.

Added:

```text
matlab/simulink_rts79/initialize_swing_equilibrium.m
matlab/simulink_rts79/run_swing_equilibrium_sanity_demo.m
src/gcn_search/legacy_rts79/analyze_swing_equilibrium_diagnostics.py
src/gcn_search/legacy_rts79/analyze_dynamic_threshold_sensitivity.py
src/gcn_search/legacy_rts79/summarize_dynamic_negative_controls_v2.py
tests/test_swing_equilibrium_diagnostics.py
tests/test_dynamic_threshold_sensitivity.py
tests/test_negative_controls_v2_summary.py
docs/pio_gcn_swing_equilibrium_and_threshold_calibration.md
```

MATLAB sanity command:

```matlab
run_swing_equilibrium_sanity_demo( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_equilibrium_sanity" ...
)
```

No-trip sanity result:

```text
no_trip_dynamic_unstable = false
no_trip_frequency_nadir_hz = 50.0
no_trip_frequency_zenith_hz = 50.0
no_trip_final_mean_frequency_hz = 50.0
no_trip_max_rotor_angle_separation_coi_deg = 18.671415861494207
pre_event_frequency_drift_hz_per_s = 0.0
initial_pm_pe_residual_norm = 0.0
initial_pm_pe_max_abs_residual = 0.0
sanity_passed = true
dynamic_model_equilibrium_failed = false
```

This fixes the baseline equilibrium sanity: no active trip stays stable. However:

```text
single_mild_trip_dynamic_unstable = true
low_risk_n2_dynamic_unstable = true
```

Updated negative controls v2:

| group | default unstable fraction | relaxed-threshold unstable fraction | passive trip fraction | mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 1.00 | 1.00 | 1.00 | 26.1084 |
| low_score_top20 | 1.00 | 0.70 | 0.75 | 11.7528 |
| random_top20 | 1.00 | 0.90 | 0.90 | 16.1437 |
| line_order_top20 | 1.00 | 0.40 | 0.60 | 9.1307 |

Threshold sensitivity:

```text
num_threshold_cases = 80
all_groups_unstable_for_all_thresholds = false
has_threshold_discrimination_signal = true
interpretation = threshold sensitivity only; not a formal dynamic conclusion
```

Interpretation: the COI and equilibrium changes make the no-trip baseline physically sane, but default-threshold Top20 dynamic validation remains globally degenerate. The sensitivity scan suggests there may be separability under relaxed thresholds, but this is a calibration clue only and must not be reported as a formal learned-method result. No dynamic recall is reported because no full dynamic truth exists.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py
40 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

RL mitigation files were not modified. Generated `.slx`, `.mat`, dynamic case folders, raw event logs, full per-case dynamic results, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.

## Round 21: Post-Fault Sanity Ladder Calibration

Round 21 calibrates post-fault dynamic response after Round 20 made no-trip stable. The purpose is not to improve learned precision; it is to make low-risk and random controls physically interpretable.

Added:

```text
matlab/simulink_rts79/run_post_fault_sanity_ladder.m
matlab/simulink_rts79/calibrate_post_fault_dynamic_response.m
src/gcn_search/legacy_rts79/check_dynamic_interpretability_gate.py
docs/pio_gcn_post_fault_sanity_ladder.md
tests/test_post_fault_sanity_ladder.py
tests/test_dynamic_interpretability_gate.py
tests/test_negative_control_v3_summary.py
```

MATLAB commands:

```matlab
run_post_fault_sanity_ladder( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_negative_controls/inputs", ...
  "../../results/gcn_search/simulink_dynamic_post_fault_sanity", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json" ...
)

calibrate_post_fault_dynamic_response( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_negative_controls/inputs", ...
  "../../results/gcn_search/simulink_dynamic_calibration", ...
  4 ...
)
```

Recommended post-fault options:

```text
damping_scale = 2
inertia_scale = 2
coupling_scale = 0.2
line_loading_scale = 0.002
relay_beta = 1.5
load_shed_step_fraction = 0.01
pm_update_mode = rebalance_to_current_pe
```

Post-fault sanity ladder with recommended options:

| case group | unstable fraction | passive trip fraction | mean stress | passed |
| --- | ---: | ---: | ---: | --- |
| no_trip | 0.00 | 0.00 | 0.0000 | true |
| single_mild_trip | 0.00 | 0.00 | 0.2423 | true |
| low_risk_ordered_n2 | 0.00 | 0.00 | 0.1137 | true |
| random_ordered_n2 | 0.00 | 0.00 | 0.0782 | true |
| learned_high_risk_n2 | 0.00 | 0.00 | 0.1137 | true |

Negative controls v3:

| group | unstable fraction | mean frequency nadir | mean stress | passive trip fraction |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 0.00 | 49.3998 | 0.1002 | 0.00 |
| low_score_top20 | 0.00 | 49.3804 | 0.1217 | 0.00 |
| random_top20 | 0.00 | 49.3682 | 0.1336 | 0.00 |
| line_order_top20 | 0.00 | 49.4051 | 0.0986 | 0.00 |

Interpretability gate:

```text
no_trip_passed = true
single_mild_trip_passed = true
low_risk_not_all_unstable = true
random_not_all_unstable = true
controls_have_variation = true
default_dynamic_precision_interpretable = true
allowed_next_step = expand_top50_top100
```

Interpretation: Round 21 removes the all-unstable post-fault degeneracy. However, the current Top20 v3 groups are all stable, so there is still no learned dynamic discrimination signal. Top50/Top100 expansion is allowed for diagnostic coverage, not as a formal performance conclusion. No dynamic recall is reported because no full dynamic truth exists.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py tests/test_post_fault_sanity_ladder.py tests/test_dynamic_interpretability_gate.py tests/test_negative_control_v3_summary.py
45 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

RL mitigation files were not modified. Generated `.slx`, `.mat`, full per-case dynamic results, raw event logs, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.

## Round 23: Non-Smoke Dynamic Method Comparison

Round 23 expands the learned path-reranker diagnosis from the minimal smoke dataset to a medium non-smoke dataset. This remains a simplified swing-equation preliminary diagnostic, not a formal dynamic stability conclusion.

Dataset:

```text
dataset_source = simulator_derived_medium
dataset_scale = medium
num_samples = 8000
num_critical = 471
positive_ratio = 0.058875
train/val/test seeds = 10/3/3
max_paths_per_seed = 500
```

Learned reranker held-out metrics:

```text
test_auc = 0.7907
test_average_precision = 0.1340
test_precision_at_20 = 0.1500
test_recall_at_20 = 0.0370
```

Dynamic method comparison:

| method | Top50 precision | Top100 precision | Top50 mean stress | Top100 mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_mlp | 0.0000 | 0.0000 | 0.1034 | 0.1040 |
| pio_gcn | 0.0000 | 0.0000 | 0.1034 | 0.1040 |
| lodf | 0.0000 | 0.0000 | 0.0856 | 0.0949 |

The non-smoke Top50/Top100 comparison is still all stable, so `calibration_warning = true` and `dynamic_discrimination_signal = false`.

Rank-depth curve: learned and PIO-GCN are identical in this run; learned does not concentrate dynamic stress earlier than PIO-GCN or LODF.

OPA/dynamic alignment: OPA load-shed label and dynamic stress correlation remains weak. Learned Top100 `corr(stress, OPA shed) = -0.0829`; LODF Top100 `corr(stress, OPA shed) = -0.0288`.

Updated gate:

```text
allowed_next_step = tune_post_fault_event_strength
```

No dynamic recall is reported because no full dynamic truth exists. Generated `.pkl`, `.slx`, `.mat`, full per-path ranking, full dataset CSVs, input paths, event logs, and raw dynamic results remain local ignored artifacts and are not intended for commit.

Validation to run for this round:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py tests/test_post_fault_sanity_ladder.py tests/test_dynamic_interpretability_gate.py tests/test_negative_control_v3_summary.py tests/test_dynamic_method_comparison_cases.py tests/test_dynamic_method_comparison_analysis.py tests/test_dynamic_rank_depth_curve.py tests/test_non_smoke_path_reranker_dataset.py tests/test_non_smoke_dynamic_method_comparison.py tests/test_non_smoke_label_dynamic_alignment.py

python scripts/gcn_search/check_pio_gcn_artifacts.py

git diff -- src/rl_mitigation scripts/rl_mitigation
```

## Round 22: Top50/Top100 Dynamic Method Comparison

Round 22 expands the event-driven dynamic diagnostic after the Round 21 post-fault sanity ladder passed. The comparison covers learned MLP reranker, PIO-GCN, and LODF Top50/Top100 inputs. This remains a simplified swing-equation preliminary diagnostic, not a formal dynamic stability conclusion.

Commands:

```powershell
python src/gcn_search/legacy_rts79/prepare_dynamic_method_comparison_topk.py --input-csv results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking.csv --output-dir results/gcn_search/simulink_dynamic_method_comparison_inputs_top100 --top-k 100

python src/gcn_search/legacy_rts79/export_dynamic_method_comparison_cases.py --input-root results/gcn_search/simulink_dynamic_method_comparison_inputs_top100 --output-root results/gcn_search/simulink_dynamic_method_comparison_cases --top-k 50 100 --event-1-time 1.0 --event-2-time 5.0 --simulation-end-time 10.0
```

MATLAB:

```matlab
run_dynamic_method_comparison_batch( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_cases", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_results", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json", ...
  100 ...
)
```

Dynamic method comparison summary:

| method | top_k | dynamic precision | mean stress |
| --- | ---: | ---: | ---: |
| learned_mlp | 50 | 0.0000 | 0.0936 |
| learned_mlp | 100 | 0.0000 | 0.0881 |
| pio_gcn | 50 | 0.0000 | 0.0823 |
| pio_gcn | 100 | 0.0000 | 0.1013 |
| lodf | 50 | 0.0000 | 0.0912 |
| lodf | 100 | 0.0000 | 0.1007 |

Interpretation:

```text
calibration_warning = true
dynamic_discrimination_signal = false
allowed_next_step = expand_non_smoke_dataset
```

All Top100 methods are dynamically stable under the recommended post-fault options. This removes the all-unstable degeneracy but creates an all-stable calibration warning. The rank-depth curve does not show learned concentrating higher dynamic stress earlier than PIO-GCN or LODF. No dynamic recall is reported because no full dynamic truth exists.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py tests/test_post_fault_sanity_ladder.py tests/test_dynamic_interpretability_gate.py tests/test_negative_control_v3_summary.py tests/test_dynamic_method_comparison_cases.py tests/test_dynamic_method_comparison_analysis.py tests/test_dynamic_rank_depth_curve.py
48 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

RL mitigation files were not modified. Generated `.slx`, `.mat`, full per-case dynamic results, raw event logs, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.
