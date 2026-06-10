# Real Top-K Dynamic Smoke Workflow

## Purpose

This note documents the Round 16 workflow for producing a local learned-reranker per-path ranking CSV and connecting it to the event-driven dynamic validation prototype.

In plain terms, the workflow does three things:

1. Export the learned path reranker ranking as a per-path ranking CSV.
2. Convert the Top-K ordered N-2 paths into dynamic line-trip events.
3. Run or prepare the simplified event-driven swing-equation validation and summarize `dynamic_precision@K`, OPA/dynamic overlap, and relay/security events.

## Per-Path Ranking CSV

Generate the local per-path ranking CSV:

```powershell
python src/gcn_search/legacy_rts79/export_path_reranker_per_path_ranking.py `
  --dataset-dir results/gcn_search/path_reranker_dataset `
  --model-dir results/gcn_search/path_reranker_models `
  --output-dir results/gcn_search/simulink_dynamic_real_per_path_ranking `
  --method learned_mlp_reranker_strict `
  --split test `
  --top-k 20 50 100 `
  --retrain-if-missing
```

Output:

```text
results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking.csv
results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking_config.json
results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_topk_preview.csv
```

The full per-path ranking CSV is a local ignored runtime artifact and should not be committed. Only compact summaries and documentation should be tracked.

If the dataset/model artifacts are missing and the training scripts are unavailable in the checkout, the exporter fails with a clear message asking the user to run `build_path_reranker_dataset.py` and `train_path_reranker.py` first.

The exporter does not use label columns such as `is_critical`, `total_load_shed_mw`, oracle rank, or truth rank as model input features. Those columns may appear only as reporting labels.

## Dynamic Pipeline

Run the pipeline in input-generation mode:

```powershell
python src/gcn_search/legacy_rts79/run_real_topk_dynamic_validation_pipeline.py `
  --top-k 20 50 100 `
  --max-cases 20 `
  --skip-matlab `
  --output-dir results/gcn_search/simulink_dynamic_real_pipeline
```

This writes:

```text
results/gcn_search/simulink_dynamic_real_pipeline/run_matlab_real_topk_dynamic_validation.m
results/gcn_search/simulink_dynamic_real_pipeline/real_topk/real_topk_input_paths.csv
results/gcn_search/simulink_dynamic_real_pipeline/dynamic_cases/matlab_batch_input.csv
```

If MATLAB is available, run the generated command file or pass `--run-matlab`. If runtime is high, use `--top-k 20 --max-cases 20` and report the result as `top20_preliminary_smoke`.

## Summary

After MATLAB results exist, summarize:

```powershell
python src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py `
  --dynamic-results-csv results/gcn_search/simulink_dynamic_real_results/simulink_dynamic_simulation_results.csv `
  --topk-paths-csv results/gcn_search/simulink_dynamic_real_cases/simulink_topk_paths.csv `
  --output-dir results/gcn_search/simulink_dynamic_real_analysis

python src/gcn_search/legacy_rts79/analyze_relay_vs_security_events.py `
  --dynamic-results-csv results/gcn_search/simulink_dynamic_real_results/simulink_dynamic_simulation_results.csv `
  --event-log-glob "results/gcn_search/simulink_dynamic_real_results/dynamic_case_event_log_*.csv" `
  --output-dir results/gcn_search/simulink_dynamic_real_relay_security_analysis

python src/gcn_search/legacy_rts79/summarize_real_topk_dynamic_validation.py `
  --precision-csv results/gcn_search/simulink_dynamic_real_analysis/simulink_dynamic_precision_at_k.csv `
  --overlap-csv results/gcn_search/simulink_dynamic_real_analysis/simulink_opa_dynamic_overlap.csv `
  --relay-security-summary-csv results/gcn_search/simulink_dynamic_real_relay_security_analysis/relay_vs_security_summary.csv `
  --output-dir results/gcn_search/simulink_dynamic_real_pipeline_summary `
  --result-scope top20_preliminary_smoke
```

The compact summary includes:

- `dynamic_precision@K`
- OPA/dynamic overlap counts
- relay/security event summary
- security redispatch or load shedding cases
- passive relay trip cases
- dynamic load shedding total
- result scope

There is no dynamic recall unless full dynamic truth is available.

## Current Interpretation

If only Top20 is run, the result is a Top20 preliminary dynamic smoke, not a complete dynamic validation.

Current limitations:

- simplified swing-equation prototype;
- not EMT;
- not full OPF;
- no renewable generation model;
- no exciter, governor, or PSS;
- preliminary dynamic smoke / preliminary dynamic validation only;
- not an engineering-grade dynamic stability conclusion.

## Round 17 Result

Round 17 first checked git history and found historical path-reranker scripts. The source files were restored, then adapted into a minimal reproducible smoke pipeline because the current checkout does not contain the full historical model/dataset artifacts.

Restored/rebuilt source files:

```text
src/gcn_search/legacy_rts79/build_path_reranker_dataset.py
src/gcn_search/legacy_rts79/train_path_reranker.py
src/gcn_search/legacy_rts79/evaluate_path_reranker_strict_heldout.py
```

Local smoke artifacts were generated:

```text
results/gcn_search/path_reranker_dataset/path_reranker_dataset.csv
results/gcn_search/path_reranker_models/path_reranker_model.pkl
results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking.csv
```

These files are ignored runtime artifacts and should not be committed.

Round 17 ran MATLAB Top20 preliminary dynamic smoke:

```text
result_scope = top20_preliminary_dynamic_smoke
num_dynamic_cases = 20
dynamic_precision@20 = 1.0
opa_critical_and_dynamic_unstable_count = 1
opa_critical_but_dynamic_stable_count = 0
opa_noncritical_but_dynamic_unstable_count = 19
cases_with_security_redispatch_or_load_shed = 0
cases_with_passive_relay_trip = 20
total_dynamic_load_shed_mw = 0.0
```

This is a smoke result from a minimal learned-reranker dataset, not a formal final conclusion. No dynamic recall is reported.

Next step: expand from Top20 smoke to Top50/Top100 using a non-smoke learned-reranker dataset and then compare dynamic precision across learned reranker, PIO-GCN, and LODF inputs.

## Round 18 Non-Degeneracy Calibration

Round 17 default Top20 smoke showed a degeneracy warning:

```text
dynamic_precision@20 = 1.0
opa_critical_and_dynamic_unstable_count = 1
opa_critical_but_dynamic_stable_count = 0
opa_noncritical_but_dynamic_unstable_count = 19
cases_with_security_redispatch_or_load_shed = 0
cases_with_passive_relay_trip = 20
```

The important issue is not that the pipeline failed. The issue is that the default dynamic scaling made all Top20 cases unstable and all 20 cases caused passive relay trips. That is a non-degeneracy warning: the prototype parameters are too sensitive for interpretation and should be calibrated before expanding to Top50/Top100.

Round 18 added:

```text
src/gcn_search/legacy_rts79/analyze_dynamic_smoke_degeneracy.py
matlab/simulink_rts79/calibrate_event_driven_dynamic_scales.m
src/gcn_search/legacy_rts79/compare_default_vs_calibrated_dynamic_smoke.py
```

The small event-driven calibration grid recommended:

```text
line_loading_scale = 0.005
coupling_scale = 0.5
damping_scale = 1.0
inertia_scale = 1.0
relay_beta = 1.2
```

Calibrated Top20 smoke result:

```text
dynamic_precision@20 = 1.0
opa_critical_and_dynamic_unstable_count = 1
opa_critical_but_dynamic_stable_count = 0
opa_noncritical_but_dynamic_unstable_count = 19
cases_with_security_redispatch_or_load_shed = 20
cases_with_passive_relay_trip = 0
total_dynamic_load_shed_mw = 231.32117491281207
```

Calibration removed the all-passive-relay-trip degeneracy, but dynamic_precision@20 remained 1.0, so the calibrated result still carries a degeneracy warning. This means the line-loading relay scale was improved, but the instability criterion or swing-equation scale still needs further calibration.

No dynamic recall is reported. This is still a simplified swing-equation preliminary dynamic smoke, not EMT, not full OPF, and not an engineering-grade dynamic stability conclusion.

## Round 19 Dynamic Negative Controls

Round 19 added instability-reason diagnostics and negative controls to test whether the calibrated dynamic layer can discriminate learned Top20 paths from easy controls.

Calibrated learned Top20 instability reasons:

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

Negative-control comparison:

| group | precision@20 | passive relay trips | security actions | mean dynamic stress |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 1.0000 | 0 | 20 | 4.9614 |
| low_score_top20 | 1.0000 | 0 | 15 | 5.1883 |
| random_top20 | 1.0000 | 0 | 18 | 4.9650 |
| line_order_top20 | 1.0000 | 0 | 12 | 4.9756 |

The result still has `global_degeneracy_warning = true` and `dynamic_discrimination_signal = false`. The important conclusion is conservative: the event-driven Simulink wrapper now runs real learned and control Top20 batches, but the current calibrated swing-equation instability threshold is still too broad to support a learned-method performance claim.

## Round 20 Equilibrium and Threshold Calibration

Round 20 adds no-trip sanity, COI reference angle diagnostics, Pm/Pe residual diagnostics, threshold sensitivity, and negative controls v2. The purpose is to make the dynamic layer physically interpretable before any Top-K dynamic precision claim.

The main rule remains: no dynamic recall is reported without full dynamic truth, and Top20 smoke is not a formal dynamic validation conclusion.

Round 20 no-trip sanity passed, but single mild trip and low-risk N-2 still became dynamically unstable. Negative controls v2 still reports `global_degeneracy_warning = true`. Threshold sensitivity contains a diagnostic separation signal, but this is not a formal performance claim.

Round 21 post-fault calibration removes the all-unstable control behavior. The interpretability gate allows Top50/Top100 diagnostic expansion, but the current v3 Top20 groups are all stable, so there is no learned dynamic discrimination signal yet.
