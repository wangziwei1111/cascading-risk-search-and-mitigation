# PIO-GCN Simulink Dynamic Validation Prototype Plan

## Purpose

The current PIO-GCN and learned path reranker are evaluated mainly by improved OPA / OPF static cascading simulation. The Simulink dynamic validation prototype adds a complementary time-domain check for Top-K ordered N-2 paths. In plain terms, it asks: if the learned reranker says a path is risky, does a simplified dynamic simulation also show frequency, rotor-angle, or line-loading stress?

## Difference From OPA / OPF Validation

OPA / OPF validation focuses on sequential branch outages, DC power flow, relay thresholds, island balancing, redispatch, and load shedding. It is suitable for large-scale path screening and full-truth ordered N-2 comparison.

The Simulink prototype focuses on time-domain response after two scheduled trip events:

```text
t = 1.0 s: trip first_line
t = 5.0 s: trip second_line
```

It reports dynamic indicators such as frequency nadir, frequency zenith, maximum rotor-angle separation, maximum line loading ratio, and a configurable unstable flag.

## Current Model Scope

The current Simulink dynamic validation is a prototype with the following assumptions:

- simplified synchronous-machine swing-equation representation;
- simplified DC-network / susceptance-matrix style network representation;
- branch trip events are driven by exported event tables;
- trajectory metrics are computed by `simulate_rts79_swing_case.m` using MATLAB `ode45`;
- missing inertia and damping parameters use assumed defaults;
- no renewable generation model;
- no inverter model;
- no EMT;
- no detailed exciter, governor, or PSS model unless explicitly added later.

Therefore, this prototype is a high-fidelity supplement relative to static ranking only in the sense that it introduces time-domain indicators. It is not a replacement for full-truth OPA / OPF and not a field-grade dynamic model.

## Workflow

1. Export RTS-79 basecase data:

```powershell
python src/gcn_search/legacy_rts79/export_rts79_simulink_basecase.py --output-dir results/gcn_search/simulink_dynamic_basecase
```

2. Export Top-K dynamic trip events:

```powershell
python src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py `
  --input-dir results/gcn_search/path_reranker_strict_heldout_eval `
  --output-dir results/gcn_search/simulink_dynamic_cases `
  --top-k 20 50 100 `
  --event-1-time 1.0 `
  --event-2-time 5.0 `
  --simulation-end-time 20.0 `
  --method learned_mlp_reranker_strict
```

If the path-level ranking CSV is local and not a tracked artifact, pass it explicitly:

```powershell
python src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py `
  --input-csv results/gcn_search/local_topk_paths.csv `
  --output-dir results/gcn_search/simulink_dynamic_cases `
  --top-k 20 50 100
```

3. If no real path-level ranking CSV is available, generate demo cases:

```powershell
python src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py --make-demo-cases --output-dir results/gcn_search/simulink_dynamic_cases
```

4. Run MATLAB batch:

```matlab
cd matlab/simulink_rts79
run_rts79_dynamic_batch( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_cases/matlab_batch_input.csv", ...
  "../../results/gcn_search/simulink_dynamic_results" ...
)
```

5. If MATLAB/Simulink is unavailable, generate mock results for CI/no-MATLAB flow testing:

```powershell
python src/gcn_search/legacy_rts79/make_mock_simulink_dynamic_results.py `
  --case-manifest results/gcn_search/simulink_dynamic_cases/simulink_dynamic_case_manifest.csv `
  --output-csv results/gcn_search/simulink_dynamic_results/simulink_dynamic_simulation_results.csv
```

Mock results must not be interpreted as real dynamic simulation results.

6. Analyze dynamic precision:

```powershell
python src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py `
  --dynamic-results-csv results/gcn_search/simulink_dynamic_results/simulink_dynamic_simulation_results.csv `
  --topk-paths-csv results/gcn_search/simulink_dynamic_cases/simulink_topk_paths.csv `
  --output-dir results/gcn_search/simulink_dynamic_analysis
```

If a full dynamic truth CSV is available, dynamic recall can be reported:

```powershell
python src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py `
  --dynamic-results-csv results/gcn_search/simulink_dynamic_results/simulink_dynamic_simulation_results.csv `
  --topk-paths-csv results/gcn_search/simulink_dynamic_cases/simulink_topk_paths.csv `
  --dynamic-truth-csv results/gcn_search/simulink_dynamic_truth/full_dynamic_truth.csv `
  --output-dir results/gcn_search/simulink_dynamic_analysis
```

## Metrics

- `dynamic_precision@K`: fraction of simulated Top-K paths that are dynamically unstable.
- `dynamic_recall@K`: Top-K dynamically unstable count divided by all dynamically unstable paths in a provided full dynamic truth set.
- `OPA critical and dynamic unstable count`: paths critical in OPA / OPF and unstable in dynamic prototype.
- `OPA critical but dynamic stable count`: static critical paths not unstable in the dynamic prototype.
- `OPA non-critical but dynamic unstable count`: static non-critical paths that show dynamic instability.
- `mean_frequency_nadir_hz`: average minimum frequency.
- `min_frequency_nadir_hz`: worst minimum frequency.
- `max_rotor_angle_separation_deg`: largest rotor-angle separation.

If only Top-K paths are simulated, report `dynamic_precision@K` only. Do not report `dynamic_recall@K` unless `--dynamic-truth-csv` is provided or the dynamic result CSV is explicitly marked as full dynamic truth.

## Round 11 Update

Round 10 provided the scaffold, event export, mock results, and analysis interface. Round 11 adds a simplified swing-equation trajectory engine:

- `simulate_rts79_swing_case.m` reads RTS-79 basecase CSV files and two trip events for each `case_id`;
- line outages are applied segment by segment at the exported event times;
- MATLAB `ode45` integrates generator rotor angle `delta_i` and speed `omega_i`;
- frequency nadir, frequency zenith, rotor-angle separation, and approximate line loading are computed from the trajectory;
- `run_rts79_dynamic_batch.m` writes `result_source=simulink_swing_prototype`;
- mock results still write `result_source=mock`.

This validation is a supplement to learned-reranker Top-K assessment. It does not replace improved OPA full-truth evaluation, does not include renewable dynamics, and remains dependent on assumed default dynamic parameters unless the user replaces them.

## Round 12 Update

Round 12 adds the real Top-K preparation and calibration layer:

- `prepare_real_topk_for_simulink_dynamic.py` prepares `real_topk_input_paths.csv` for `--input-csv`;
- missing per-path ranking artifacts now produce an explicit error unless `--use-demo-fallback` is requested;
- `check_rts79_swing_model_sanity.m` runs a no-disturbance sanity case;
- `calibrate_rts79_swing_scales.m` searches prototype coupling, damping, inertia, and line-loading scales;
- `run_real_topk_dynamic_validation.m` runs calibrated real Top-K cases;
- `analyze_opa_dynamic_disagreement.py` reports OPA/dynamic disagreement categories.

Demo dynamic precision is not a formal dynamic conclusion. Real Top-K dynamic precision should be documented only after running a real local per-path ranking CSV through the calibrated prototype.

## Round 13 Update

Round 13 adds relay threshold vs security constraint handling:

- `L_m^max` is the line security constraint used by OPF/security checks.
- `beta * L_m^max` is the relay threshold.
- `loading_ratio > 1.0` and `loading_ratio <= beta` triggers a security redispatch/load shedding approximation, not relay trip.
- `loading_ratio > beta` triggers passive relay trip logic.

The current redispatch/load shedding model is an approximation around overloaded line terminal buses. It is not a full OPF.

## Round 14 Update

Round 14 changes relay/security handling from post-processing into an event-driven closed-loop prototype. Passive relay trips affect subsequent topology. Security redispatch/load shedding affects subsequent loads and the simplified `Pm` approximation. Two MATLAB demos were added to separately verify mild overload security action and severe overload relay action.

The closed-loop behavior is still a prototype. It is not full OPF redispatch, not EMT, and has no renewable generation or detailed controls.

## Next Steps

- Add passive overload relay tripping in the time-domain prototype.
- Add more detailed synchronous-machine controls.
- Add voltage-stability indicators.
- Add renewable inverter models in a later round.
- Build dynamic full-truth for a small subset when runtime permits.
