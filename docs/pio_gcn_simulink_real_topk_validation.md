# PIO-GCN Simulink Real Top-K Dynamic Validation

## Scope

Round 10 added the Simulink dynamic validation scaffold and mock output flow. Round 11 added a simplified swing-equation trajectory engine. Round 12 connects that engine to real learned-reranker Top-K input, adds prototype scale calibration, and adds OPA/dynamic disagreement diagnostics.

This remains a simplified electromechanical prototype. It is not EMT, has no renewable model, and has no detailed exciter, governor, or PSS. Dynamic parameters are assumed/default/calibrated prototype values unless manually replaced.

## Real Top-K Input

Prepare a real path-level ranking CSV:

```powershell
python src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py `
  --input-csv results/gcn_search/local_real_topk_paths.csv `
  --output-dir results/gcn_search/simulink_dynamic_real_topk `
  --top-k 20 50 100
```

If no per-path ranking CSV is available in tracked artifacts, the script fails by default. Use `--use-demo-fallback` only to test the interface.

## Sanity And Calibration

Run no-disturbance sanity:

```matlab
cd matlab/simulink_rts79
check_rts79_swing_model_sanity( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_calibration" ...
)
```

Run prototype scale calibration:

```matlab
calibrate_rts79_swing_scales( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_cases/matlab_batch_input.csv", ...
  "../../results/gcn_search/simulink_dynamic_calibration" ...
)
```

The calibration output is:

```text
results/gcn_search/simulink_dynamic_calibration/swing_scale_grid.csv
results/gcn_search/simulink_dynamic_calibration/recommended_swing_options.json
```

This is prototype scale calibration, not real power-system parameter identification.

## Real Top-K Dynamic Run

```matlab
run_real_topk_dynamic_validation( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_real_topk/matlab_batch_input.csv", ...
  "../../results/gcn_search/simulink_dynamic_real_results", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_swing_options.json" ...
)
```

Analyze dynamic precision and OPA/dynamic overlap:

```powershell
python src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py `
  --dynamic-results-csv results/gcn_search/simulink_dynamic_real_results/simulink_dynamic_simulation_results.csv `
  --topk-paths-csv results/gcn_search/simulink_dynamic_real_topk/simulink_topk_paths.csv `
  --output-dir results/gcn_search/simulink_dynamic_real_analysis

python src/gcn_search/legacy_rts79/analyze_opa_dynamic_disagreement.py `
  --topk-paths-csv results/gcn_search/simulink_dynamic_real_topk/simulink_topk_paths.csv `
  --dynamic-results-csv results/gcn_search/simulink_dynamic_real_results/simulink_dynamic_simulation_results.csv `
  --output-dir results/gcn_search/simulink_dynamic_disagreement
```

Without full dynamic truth, report dynamic precision only. Do not report dynamic recall.

## Current Conclusion

Demo precision is not a formal dynamic conclusion. Formal Top-K dynamic precision requires a real local per-path ranking CSV. The Simulink validation supplements learned reranker / PIO-GCN Top-K analysis and does not replace improved OPA full-truth validation. Passive overload relay tripping and renewable dynamic validation are future work.

For the current repository checkout, tracked artifacts did not include a real per-path learned-reranker ranking CSV. The real Top-K workflow therefore requires the user to provide a local ignored CSV through `--input-csv`. Demo fallback can test the pipeline but must not be reported as formal Top-K dynamic precision.
