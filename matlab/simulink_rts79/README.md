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
