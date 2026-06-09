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
