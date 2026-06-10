# RTS-79 Simulink Dynamic Validation Prototype

This folder contains MATLAB scripts for a simplified Simulink dynamic validation prototype for PIO-GCN PathRank / learned path reranker Top-K ordered N-2 paths.

## Scope

- This is a Simulink dynamic validation prototype.
- It is not EMT.
- It is not a field-grade dynamic model.
- It does not include renewable generation, inverter controls, detailed exciters, governors, or PSS.
- Missing dynamic parameters are represented by assumed defaults and are marked as such in the exported JSON/CSV files.
- The current real dynamic path uses `simulate_rts79_swing_case.m`, a MATLAB `ode45` simplified swing-equation engine.
- The generated Simulink file is a scaffold; trajectory metrics are computed by the MATLAB ODE engine in this round.

## Python Export

```powershell
python src/gcn_search/legacy_rts79/export_rts79_simulink_basecase.py --output-dir results/gcn_search/simulink_dynamic_basecase
python src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py --make-demo-cases --output-dir results/gcn_search/simulink_dynamic_cases
```

For a real local Top-K ranking CSV:

```powershell
python src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py --input-csv results/gcn_search/local_topk_paths.csv --output-dir results/gcn_search/simulink_dynamic_cases --top-k 20 50 100
```

## MATLAB Batch Run

From MATLAB:

```matlab
cd matlab/simulink_rts79
run_rts79_dynamic_batch( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_cases/matlab_batch_input.csv", ...
  "../../results/gcn_search/simulink_dynamic_results" ...
)
```

The batch output is:

```text
results/gcn_search/simulink_dynamic_results/simulink_dynamic_simulation_results.csv
```

Rows from the MATLAB ODE engine are marked with:

```text
result_source = simulink_swing_prototype
```

The generated `.slx` model is saved under:

```text
results/gcn_search/simulink_dynamic_models/
```

Do not commit generated `.slx`, `.mat`, `.mdl`, or large raw trajectory files.

If full raw trajectories are needed, call `run_rts79_dynamic_batch(..., true)`. They are written under the ignored directory:

```text
results/gcn_search/simulink_dynamic_results/raw_trajectories/
```

## Metrics

- `frequency_nadir_hz`: minimum frequency during the time-domain run.
- `frequency_zenith_hz`: maximum frequency during the time-domain run.
- `max_rotor_angle_separation_deg`: maximum rotor-angle separation.
- `max_line_loading_ratio`: approximate maximum line loading ratio.
- `dynamic_unstable`: default true if frequency nadir is below 49 Hz, rotor-angle separation exceeds 180 degrees, simulation fails, or line loading exceeds 1.5 for the configured duration.

If only Top-K paths are simulated, report `dynamic_precision@K` only. Do not report `dynamic_recall@K` unless a full dynamic truth set is available.

Use `--dynamic-truth-csv` in the Python analyzer when a full dynamic truth set exists. Without it, recall is intentionally unavailable.

## Round 12 Real Top-K And Calibration

Prepare real Top-K input from a local per-path ranking CSV:

```powershell
python src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py --input-csv results/gcn_search/local_real_topk_paths.csv --output-dir results/gcn_search/simulink_dynamic_real_topk --top-k 20 50 100
```

Run no-disturbance sanity and prototype scale calibration:

```matlab
check_rts79_swing_model_sanity( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_calibration" ...
)

calibrate_rts79_swing_scales( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_cases/matlab_batch_input.csv", ...
  "../../results/gcn_search/simulink_dynamic_calibration" ...
)
```

Run calibrated real Top-K dynamic validation:

```matlab
run_real_topk_dynamic_validation( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_real_topk/matlab_batch_input.csv", ...
  "../../results/gcn_search/simulink_dynamic_real_results", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_swing_options.json" ...
)
```

## Relay Threshold vs Security Constraint

Default `relay_beta` is `1.2`.

- `loading_ratio <= 1.0`: no overload action.
- `1.0 < loading_ratio <= relay_beta`: security redispatch/load shedding approximation.
- `loading_ratio > relay_beta`: passive relay trip.

Each case writes:

```text
dynamic_case_event_log_<case_id>.csv
```

The event log distinguishes active trips, security actions, and passive relay trips. The security action is a prototype approximation, not a full OPF.

## Event-Driven Closed Loop

Round 14 uses an event-driven loop:

- active trips update later topology;
- passive relay trips update later topology;
- security redispatch/load shedding updates later loads and the simplified `Pm` approximation.

Demo commands:

```matlab
run_mild_overload_security_demo( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_mild_overload_demo" ...
)

run_severe_overload_relay_demo( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_severe_overload_demo" ...
)
```

These demos validate prototype logic only. They are not formal dynamic stability conclusions.

## Round 15 Real Learned-Reranker Top-K Event-Driven Flow

Round 16 can first export a local learned-reranker per-path ranking CSV:

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

Prepare a real learned-reranker Top-K table. The script searches common local per-path ranking locations by default and fails if no real CSV is found:

```powershell
python src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py `
  --method learned_mlp_reranker_strict `
  --top-k 20 50 100 200 `
  --output-dir results/gcn_search/simulink_dynamic_real_topk
```

If the ranking table is local and ignored, pass it explicitly:

```powershell
python src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py `
  --input-csv results/gcn_search/local_real_per_path_ranking.csv `
  --method learned_mlp_reranker_strict `
  --top-k 20 50 100 200 `
  --output-dir results/gcn_search/simulink_dynamic_real_topk
```

Export event cases:

```powershell
python src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py `
  --input-csv results/gcn_search/simulink_dynamic_real_topk/real_topk_input_paths.csv `
  --output-dir results/gcn_search/simulink_dynamic_real_cases `
  --top-k 20 50 100 200
```

Run the event-driven wrapper from MATLAB:

```matlab
run_real_topk_event_driven_dynamic_validation( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_real_cases/matlab_batch_input.csv", ...
  "../../results/gcn_search/simulink_dynamic_real_results", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_swing_options.json" ...
)
```

For Top-K-only simulations, report dynamic precision only. Do not report dynamic recall unless a full dynamic truth table exists.

One-step input generation and MATLAB command-file export:

```powershell
python src/gcn_search/legacy_rts79/run_real_topk_dynamic_validation_pipeline.py `
  --top-k 20 50 100 `
  --max-cases 20 `
  --skip-matlab `
  --output-dir results/gcn_search/simulink_dynamic_real_pipeline
```

Use Top20 as preliminary dynamic smoke if runtime is limited.

## Event-Driven Calibration

Round 18 adds a small event-driven calibration grid for the Top20 preliminary dynamic smoke:

```matlab
calibrate_event_driven_dynamic_scales( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_real_pipeline/dynamic_cases/matlab_batch_input.csv", ...
  "../../results/gcn_search/simulink_dynamic_calibration" ...
)
```

The default Top20 smoke produced a non-degeneracy warning: all 20 cases caused passive relay trips and `dynamic_precision@20 = 1.0`. The calibration grid writes:

```text
results/gcn_search/simulink_dynamic_calibration/event_driven_scale_grid.csv
results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json
results/gcn_search/simulink_dynamic_calibration/event_driven_calibration_summary.json
```

The current calibrated Top20 smoke removes the all-passive-relay-trip condition, but all 20 cases remain dynamically unstable. This is still a preliminary smoke result, not EMT, not full OPF, and not an engineering-grade dynamic stability conclusion.

## Round 19 Negative Controls

Round 19 adds a four-group negative-control wrapper:

```matlab
run_dynamic_negative_control_batch( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_negative_controls/cases", ...
  "../../results/gcn_search/simulink_dynamic_negative_controls/results", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json", ...
  20 ...
)
```

The Python driver prepares learned, low-score, random, and line-order Top20 inputs and can call MATLAB automatically:

```powershell
python src/gcn_search/legacy_rts79/run_dynamic_negative_control_pipeline.py `
  --input-csv results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking.csv `
  --output-dir results/gcn_search/simulink_dynamic_negative_controls `
  --top-k 20 `
  --run-matlab `
  --options-json-path results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json
```

Current result: all four groups remain 20/20 dynamically unstable, with no passive relay trips. The learned group is not more stressful than all controls, so the calibrated dynamic validation layer still carries a global degeneracy warning.

## Round 20 Swing Equilibrium Sanity

Round 20 adds a no-trip and low-risk sanity demo:

```matlab
run_swing_equilibrium_sanity_demo( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_equilibrium_sanity" ...
)
```

The swing engine now records COI-relative rotor angle separation, raw rotor angle separation, initial Pm/Pe residuals, mean frequency, final mean frequency, and frequency drift. The default rotor-angle instability check uses COI-relative separation, while raw angle values remain available for diagnostics.

This is still a simplified swing-equation prototype. COI reference reduces angle-reference drift; it does not make the model EMT, full OPF, or engineering-grade.

Current Round 20 sanity result:

```text
no_trip_dynamic_unstable = false
no_trip_frequency_nadir_hz = 50.0
no_trip_max_rotor_angle_separation_coi_deg = 18.6714
initial_pm_pe_max_abs_residual = 0.0
single_mild_trip_dynamic_unstable = true
low_risk_n2_dynamic_unstable = true
```

This means the equilibrium baseline passes, but faulted low-risk controls are still too sensitive and need further calibration before dynamic precision is interpretable.

## Round 21 Post-Fault Sanity Ladder

Run the post-fault ladder:

```matlab
run_post_fault_sanity_ladder( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_negative_controls/inputs", ...
  "../../results/gcn_search/simulink_dynamic_post_fault_sanity", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json" ...
)
```

Run the small post-fault calibration grid:

```matlab
calibrate_post_fault_dynamic_response( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_negative_controls/inputs", ...
  "../../results/gcn_search/simulink_dynamic_calibration" ...
)
```

The current recommended post-fault options pass the sanity ladder, but Top20 v3 does not yet show learned dynamic discrimination. Use Top50/Top100 only as diagnostic expansion, not as final dynamic proof.

## Round 22 Dynamic Method Comparison

Run learned / PIO-GCN / LODF Top50 and Top100 batches:

```matlab
run_dynamic_method_comparison_batch( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_cases", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_results", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json", ...
  100 ...
)
```

Current Round 22 result: all Top100 dynamic precision values are 0, so this is still a calibration_warning and not a formal dynamic conclusion.

## Round 23 Non-Smoke Dynamic Method Comparison

Round 23 uses the same MATLAB wrapper on a medium non-smoke learned-reranker dataset:

```matlab
run_dynamic_method_comparison_batch( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_cases_non_smoke", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_results_non_smoke", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json", ...
  100 ...
)
```

Current Round 23 result: learned, PIO-GCN, and LODF Top100 dynamic precision values are still 0. The non-smoke result remains a preliminary diagnostic comparison with `calibration_warning = true`, not a formal dynamic stability conclusion. No dynamic recall is reported without full dynamic truth.
