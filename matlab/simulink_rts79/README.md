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
