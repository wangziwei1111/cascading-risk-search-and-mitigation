# IEEE39 L12 Islanding / Timeout Diagnosis

## Status

- line_id: `L12`
- line block path: `IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B19 to B16`
- validation_passed: `true`
- simulation_success: `false`
- measurement_extraction_status: `simulation_timeout`
- training_ready_candidate: `false`
- should_merge_as_training_ready: `false`
- should_retrain_reranker: `false`

L12 is not merged into the formal fault summary as a training-ready line-trip
label. It remains a suspected islanding / timeout special case.

## Topology Diagnosis

- removed edge: `B19-B16`
- B19-side component after opening L12: `B19`
- component size: `1`
- component_contains_reference_or_main_grid: `false`
- islanding_candidate: `true`

Removing B19-B16 leaves the B19-side component with 1 bus(es): ['B19']. This component does not contain the selected reference/main-grid buses ['B1', 'B39'] and is not the largest remaining component.

This does not prove a stable or unstable dynamic conclusion. It only indicates
that L12 should be treated carefully as an islanding / timeout case.

## Recommended Manual Checks

- Check whether L12_HandwiredTimedBreaker is truly in series with Grid/B19 to B16.
- Check whether the original B19-B16 connection is actually opened when the breaker trips.
- Check whether any bypass path remains around the L12 breaker.
- Check whether L12_TripCommand controls only the L12 breaker.
- Check whether the Step command direction is 0 -> 1.
- Check whether the breaker control port is connected to the intended control input.
- Check whether opening B19-B16 creates an abnormal B19-side Simscape island.
- If this is a natural islanding branch, keep L12 as an islanding special case rather than a standard training-ready single-line label.

## Recommended Next Action

Manually inspect and optionally rewire L12; if it is a natural islanding case, keep it as a special-case timeout label and do not merge as standard training-ready line trip.

## Optional Commands After Manual Repair

MATLAB:

```matlab
cd matlab/simulink_ieee39
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_lines_batch(["L12"])
```

PowerShell:

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L12 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx" --timeout-seconds 240 --simulation-stop-time 0.5
```

Do not rerun this automatically before the user confirms L12 has been inspected
or rewired.

## Caveats

- Topology diagnosis is based on the wrapper Grid line inventory, not a full dynamic stability proof.
- phasor_RMS, not EMT
- generator_speed_proxy, not direct frequency
- pilot breaker-like validation, not engineering-grade protection
- L12 remains a suspected islanding / timeout special case, not a verified stable or unstable conclusion.

Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full
timeseries.
