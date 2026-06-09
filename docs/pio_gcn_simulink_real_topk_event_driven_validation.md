# PIO-GCN Simulink Real Top-K Event-Driven Dynamic Validation

## Scope

Round 15 connects the event-driven closed-loop Simulink dynamic prototype to a real learned path-reranker Top-K input table when such a local per-path ranking CSV is available.

The physical meaning is:

1. Take ordered N-2 paths ranked by the learned path reranker.
2. Convert each path into two scheduled line-trip events.
3. Run the simplified event-driven swing-equation prototype.
4. After each active trip, check overloads, distinguish security actions from relay trips, update topology/loads, and continue the dynamic simulation.

This remains a simplified dynamic validation prototype. It is not EMT, not a field-grade dynamic model, and not a renewable dynamic validation.

## Real Input Requirement

The preparation script now searches common local result locations for per-path ranking CSV files:

```text
results/gcn_search/path_reranker_strict_heldout_eval/
results/gcn_search/path_reranker_extended_strict_eval/
results/gcn_search/path_reranker_fulltruth_eval/
results/gcn_search/path_reranker_renewable_eval/
results/gcn_search/**/diagnostics/
results/gcn_search/**/per_path*.csv
results/gcn_search/**/*rank*.csv
results/gcn_search/**/*score*.csv
```

By default, it does not use demo fallback:

```powershell
python src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py `
  --method learned_mlp_reranker_strict `
  --top-k 20 50 100 200 `
  --output-dir results/gcn_search/simulink_dynamic_real_topk
```

If no real per-path ranking CSV is found, the script fails and prints an explicit message. Use `--input-csv` when the real ranking CSV is local and ignored:

```powershell
python src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py `
  --input-csv results/gcn_search/local_real_per_path_ranking.csv `
  --method learned_mlp_reranker_strict `
  --top-k 20 50 100 200 `
  --output-dir results/gcn_search/simulink_dynamic_real_topk
```

The required normalized output is:

```text
results/gcn_search/simulink_dynamic_real_topk/real_topk_input_paths.csv
```

with these fields:

```text
case_id, source_seed, path_rank, path, first_line, second_line,
pio_score, paper_score, lodf_score, reranker_score,
opa_is_critical, opa_total_load_shed_mw
```

Demo fallback exists only for interface testing:

```powershell
python src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py --allow-demo-fallback
```

Demo outputs must not be reported as real Top-K dynamic validation.

## Event Export

After preparing the normalized Top-K path CSV, export MATLAB event cases:

```powershell
python src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py `
  --input-csv results/gcn_search/simulink_dynamic_real_topk/real_topk_input_paths.csv `
  --output-dir results/gcn_search/simulink_dynamic_real_cases `
  --top-k 20 50 100 200
```

The MATLAB batch input is:

```text
results/gcn_search/simulink_dynamic_real_cases/matlab_batch_input.csv
```

## Event-Driven MATLAB Run

Run the event-driven closed-loop prototype:

```matlab
cd matlab/simulink_rts79
run_real_topk_event_driven_dynamic_validation( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_real_cases/matlab_batch_input.csv", ...
  "../../results/gcn_search/simulink_dynamic_real_results", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_swing_options.json" ...
)
```

Each simulated case may write an event log:

```text
results/gcn_search/simulink_dynamic_real_results/dynamic_case_event_log_<case_id>.csv
```

The event log distinguishes:

- `active_trip_first_line`
- `active_trip_second_line`
- `security_redispatch_or_load_shed`
- `passive_relay_trip`

## Analysis

Top-K-only dynamic simulation supports precision-style reporting:

```powershell
python src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py `
  --dynamic-results-csv results/gcn_search/simulink_dynamic_real_results/simulink_dynamic_simulation_results.csv `
  --topk-paths-csv results/gcn_search/simulink_dynamic_real_cases/simulink_topk_paths.csv `
  --output-dir results/gcn_search/simulink_dynamic_real_analysis
```

Relay/security event distinction:

```powershell
python src/gcn_search/legacy_rts79/analyze_relay_vs_security_events.py `
  --dynamic-results-csv results/gcn_search/simulink_dynamic_real_results/simulink_dynamic_simulation_results.csv `
  --event-log-glob "results/gcn_search/simulink_dynamic_real_results/dynamic_case_event_log_*.csv" `
  --output-dir results/gcn_search/simulink_dynamic_relay_security_analysis
```

Without full dynamic truth, report only `dynamic_precision_at_k`. Do not report dynamic recall.

## Method Comparison Inputs

When the same per-path CSV contains `reranker_score`, `pio_score`, and `lodf_score`, prepare three comparable Top-K dynamic inputs:

```powershell
python src/gcn_search/legacy_rts79/prepare_dynamic_method_comparison_topk.py `
  --input-csv results/gcn_search/local_real_per_path_ranking.csv `
  --output-dir results/gcn_search/simulink_dynamic_method_comparison_inputs `
  --top-k 100
```

Outputs:

```text
learned_mlp_topk_input_paths.csv
pio_gcn_topk_input_paths.csv
lodf_topk_input_paths.csv
```

If a score column is missing, that method is skipped with a warning.

## Current Round 15 Status

If the local checkout does not contain a real learned-reranker per-path ranking CSV, the real Top-K dynamic validation is not run. In that case, the correct conclusion is:

```text
real per-path ranking CSV not available; real Top-K dynamic validation was not run.
```

The implemented value of Round 15 is the reviewable connection between learned-reranker ranking outputs and event-driven dynamic validation inputs, with explicit failure when real ranking data is absent.
