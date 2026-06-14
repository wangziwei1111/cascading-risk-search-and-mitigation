# IEEE39 L12 Islanding / Timeout Case

## Plain-Language Status

L12 is not treated as a normal training-ready line-trip sample. Its clean
breaker lab structure validation passed, so the expected `L12_TripCommand` and
`L12_HandwiredTimedBreaker` were found near the target line. However, the
compact isolated Simulink run timed out after 240 seconds.

The current diagnosis says: opening `Grid/B19 to B16` may separate the Bus19
side from the main grid. In the simplified wrapper inventory graph, removing
the `B19-B16` edge leaves the B19-side component as `B19` only. That is why L12
is recorded as a suspected islanding / timeout special case, not as a verified
stable or unstable dynamic result.

## Recorded Fields

- line_id: `L12`
- line block path: `IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B19 to B16`
- validation_passed: `true`
- simulation_success: `false`
- measurement_extraction_status: `simulation_timeout`
- training_ready_candidate: `false`
- should_merge_as_training_ready: `false`
- should_retrain_reranker: `false`
- islanding_candidate: `true`
- removed_edge: `B19-B16`
- B19-side component after L12 open: `B19`

## What This Means

This result does not prove that L12 is dynamically stable or unstable. It only
means the current clean breaker lab compact run did not finish, and the
topology diagnosis gives a plausible reason: the L12 outage may create an
abnormal or natural islanding case around Bus19.

Therefore, L12 is not merged into the formal training-ready fault summary. The
current formal label gate remains:

- `num_training_ready_labels = 35`
- `num_training_ready_handwired_line_trip_labels = 33`
- `num_unique_handwired_line_ids = 33`

## Recommended Manual Checks

- Check whether `L12_HandwiredTimedBreaker` is truly in series with
  `Grid/B19 to B16`.
- Check whether the original B19-B16 connection is opened when the breaker
  trips.
- Check whether any bypass path remains around the L12 breaker.
- Check whether `L12_TripCommand` controls only the L12 breaker.
- Check whether the Step command direction is `0 -> 1`.
- Check whether the breaker control port is connected to the intended control
  input.
- Check whether opening B19-B16 creates an abnormal B19-side Simscape island.
- If this is a natural islanding branch, keep L12 as an islanding special case
  rather than a standard training-ready single-line label.

## Optional Rerun After Manual Repair

Do not rerun L12 automatically. After the user manually inspects or rewires the
case, the narrow validation can be rerun with:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_lines_batch(["L12"])
```

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L12 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx" --timeout-seconds 240 --simulation-stop-time 0.5
```

## Boundaries

- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker is pilot breaker-like validation, not engineering-grade
  protection.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full
  timeseries.
- No dynamic-aware reranker retraining is triggered by this L12 diagnosis.

## Expanded Preview Training Note

The later expanded-label preview training still excludes L12. That rerun uses
the 35 training-ready compact dynamic labels, keeps L12 as
`simulation_timeout / suspected islanding`, and does not fix or merge L12. No
`.slx` file is modified for the expanded preview run.

The stricter dynamic-aware comparison also excludes L12. L12 remains excluded.
It does not fix L12, does not run Simulink, and does not modify Simscape
physical wiring. It is not a final dynamic performance conclusion.

## Non-line-trip expansion boundary

The non-line-trip fault expansion preparation also excludes L12. It does not
repair, rerun, or merge the L12 timeout case. The new manifest is for
three-phase fault-clear, duration-sweep, relay-proxy, and future manual
non-line-trip scenarios only; it is not a new training-ready label set and it
does not change the current L12 status.
