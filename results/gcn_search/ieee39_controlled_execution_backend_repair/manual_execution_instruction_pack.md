# IEEE39 Selected-32 Manual Execution Instruction Pack

This instruction pack is for a future separately approved execution round. Do not use it to train GCN, rerun formal audit, export formal labels, retrain the reranker, or run full 1056 generation.

## 1. Confirm MATLAB/Simulink

Run `matlab -batch "ver"` locally and confirm Simulink is licensed. This repair round does not run Simulink.

## 2. Run Only Selected 32 Pairs

Use only `results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/selected_single_outage_pilot_pairs.json`. Do not substitute the 1056-pair plan.

## 3. Python Runner

Future approved command:

```powershell
python scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py --approved-selected-pairs-only --max-pairs 32 --execute --write-report
```

The repair round must not use `--execute`.

## 4. MATLAB Entrypoint

Future approved MATLAB entrypoint:

```matlab
run_ieee39_selected_pair_line_trip_sequence(manifestPath, outputDir, "approved_selected_pairs_only", true, "execute", true)
```

## 5. Output Directory

Write only compact evidence summaries under a future approved output directory. Do not write raw trajectory, full timeseries, or `.mat` files.

## 6. Safety Checks

Before committing, verify no raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, or model files are staged.

## 7. Timeout

Timeout remains timeout/unknown and must not become 0 or 1.

## 8. Blocked

Blocked remains null. Do not fabricate pilot labels.

## 9. Compact Evidence Summary

Collect one compact row per pair with `pair_id`, `execution_status`, `pilot_label_value`, `pilot_label_status`, `dynamic_stress_score_if_available`, `unstable_flag_if_available`, and `timeout_or_failure_reason`.

## 10. Forbidden Actions

Do not export formal labels. Do not train GCN. Do not run full 1056 generation. Manual approval is required before execution.
