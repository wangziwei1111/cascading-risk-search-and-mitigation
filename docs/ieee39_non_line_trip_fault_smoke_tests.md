# IEEE39 Non-Line-Trip Fault Smoke Tests

## Purpose

This round runs a small Simulink smoke test for the non-line-trip expansion
plan. It checks whether selected non-line-trip scenarios can produce compact
dynamic measurements before any formal label export is attempted.

The smoke-tested scenarios are:

- `NF01`: existing three-phase fault-clear baseline.
- `NF02`: existing three-phase fault block with 0.05 s clearing duration.
- `NF03`: existing three-phase fault block with 0.08 s clearing duration.
- `NF04`: existing three-phase fault block with 0.10 s clearing duration.
- `NF06`: existing basic relay proxy case.

`NF07-NF10` remain `manual_required` and were not executed.

## Runner

```powershell
python scripts/gcn_search/run_ieee39_non_line_trip_fault_smoke_tests.py ^
  --scenario-manifest results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_scenario_manifest.csv ^
  --scenario-ids NF01 NF02 NF03 NF04 NF06 ^
  --timeout-seconds 240 ^
  --simulation-stop-time 0.8 ^
  --output-dir results/gcn_search/ieee39_dynamic_fault_type_expansion/smoke_outputs
```

Each scenario runs in a separate MATLAB process with timeout protection. A
failure or timeout in one scenario is recorded and does not block later
scenarios.

## Smoke Result

All five requested scenarios completed as smoke candidates:

- `scenario_ids_successful = NF01, NF02, NF03, NF04, NF06`
- `scenario_ids_failed = none`
- `scenario_ids_timeout = none`
- `num_successful_smoke_candidates = 5`

Output files:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_summary.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_report.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_report.md`

## Boundary Rules

- This round allowed only small Simulink smoke tests.
- This round did not modify `.slx` files.
- This round did not modify Simscape physical wiring.
- This round did not fix L12 and did not touch L12.
- This round did not update the formal training-ready label count.
- This round did not retrain the dynamic-aware reranker.
- Smoke-test success is not a formal merge into training-ready dynamic labels.
- A later merge/export round must keep non-line-trip labels separate from
  handwired line-trip labels.
- The model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The relay proxy is not engineering-grade protection.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, full
  timeseries, or large checkpoints.

## Next Step

Create a separate non-line-trip label export / merge round for successful smoke
candidates. That round should explicitly keep non-line-trip labels separate
from handwired line-trip labels and should not change the current formal gate
until the new label schema is reviewed.

## Candidate Export Follow-Up

The successful smoke rows have now been exported as a separate non-line-trip
candidate label set. The original formal gate remains `35 / 33 / 33`; the new
v2 combined candidate schema has `40` rows, including `5` non-line-trip
candidate labels.

`NF01`, `NF04`, and `NF06` share identical compact measurements. `NF06` remains
in the candidate export, but it is marked `provenance_check_required = true`
because the relay proxy row currently matches the `0.10 s` fault group.

This export still does not retrain the dynamic-aware reranker and is not final
dynamic performance conclusion.

## v2 Preview Training Follow-Up

The exported candidate rows were later used in a preview-only v2 dynamic-aware
reranker training check. The include-all version uses all `40` v2 rows and keeps
`NF06`; the provenance sensitivity version uses `39` rows and excludes `NF06`.
The old formal gate remains `35 / 33 / 33`.

The label-family holdout result is the main caution: training on existing formal
line-trip rows and testing on non-line-trip rows gives RMSE around `0.142`,
which is much higher than the leave-one-out preview RMSE around `0.028`.

No Simulink simulation was run in that training follow-up, no `.slx` file was
modified, L12 was not fixed, and the result is still preview-only. It is not a
final dynamic performance conclusion.

This is not a final dynamic performance conclusion.
