# GCN PIO Validation Log

This compact log preserves the review milestones for the RTS-79 PIO-GCN PathRank work after repository cleanup.

## Round 7

Validated the Top-K depth tradeoff, score-level ensemble feasibility, and hard-negative-aware reranking on the RTS-79 preliminary setting.

## Round 8

Removed large tracked result artifacts from Git tracking and kept compact review summaries, figures, and diagnostics.

## Round 9

Audited learned path-reranker leakage, strict held-out seed behavior, external-seed behavior, synthetic renewable robustness, and path-pattern memorization risk.

## Current Scope

The public repository scope is the GCN cascading-failure path-search reproduction and its RTS-79 PIO-GCN PathRank extensions.

## IEEE39 L02 Handwired Breaker Recheck

The user manually revised `L02_TripCommand` and
`L02_HandwiredTimedBreaker` in the local Simulink GUI model:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx
```

Validation result:

```text
L01-L04 structure validation = passed
L02 breaker_block_found = true
L02 trip_command_found = true
L02 breaker_near_line = true
L02 validation_passed = true
handwired_model_committed = false
```

Compact simulation result:

```text
L01 simulation_success = true
L02 simulation_success = false
L02 timeout_or_error_message = isolated MATLAB run timed out after 240 seconds
L03/L04 training_ready_candidate = false
```

The timeout-blocking issue is addressed at the validation-script level by
`scripts/gcn_search/run_ieee39_multi_handwired_line_trip_isolated.py`: each line
is launched in a separate MATLAB process, partial summaries are written after
each line, and the process tree is killed on timeout. MATLAB's internal
`TimeOut` option was also added to the compact suite, but the isolated wrapper
is the more robust guard for this model.

Label gate after merge:

```text
num_training_ready_handwired_line_trip_labels = 1
num_unique_handwired_line_ids = 1
num_training_ready_labels = 3
allowed_for_dynamic_aware_training = false
```

The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency. The handwired breaker remains pilot breaker-like validation, not
engineering-grade protection. The handwired `.slx`, generated `.slx`, `.slxc`,
`slprj`, `.mat`, raw trajectories, and full timeseries are not intended for
commit.

## IEEE39 Clean Breaker Lab Reset

The current old handwired `.slx` is no longer the target for L02-L04 debugging.
It has gone through multiple manual edits and L02-L04 still did not become
training-ready. A clean lab workflow was added so the user can manually wire a
fresh L02 breaker on a clean copy of the generated wrapper.

Created workflow artifacts:

```text
matlab/simulink_ieee39/prepare_ieee39_clean_handwired_breaker_lab.m
matlab/simulink_ieee39/validate_ieee39_clean_breaker_lab_line.m
scripts/gcn_search/print_ieee39_clean_breaker_lab_checklist.py
scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trip_isolated.py
docs/ieee39_clean_breaker_lab_workflow.md
```

Clean lab target:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab.slx
```

Prepare result:

```text
source_found = true
target_created = true
target_loadable = true
contains_existing_L01_HandwiredTimedBreaker = false
contains_existing_L02_HandwiredTimedBreaker = false
contains_existing_L03_HandwiredTimedBreaker = false
contains_existing_L04_HandwiredTimedBreaker = false
```

The clean lab `.slx` is local only and must not be committed. No breaker was
inserted automatically, no Simscape physical-port wiring was modified by Codex,
and no dynamic-aware reranker training is allowed while the label count remains
below 10.

## IEEE39 Clean Breaker Lab L02 Success

The user manually wired L02 in the clean breaker lab model:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab.slx
```

Structure validation:

```text
clean_lab_model_found = true
clean_lab_model_loadable = true
breaker_block_found = true
trip_command_found = true
breaker_near_line = true
validation_passed = true
clean_lab_model_committed = false
```

Isolated compact simulation:

```text
simulation_success = true
physical_fault_or_breaker_action_executed = true
trip_implementation = handwired_timed_breaker
measurement_extraction_status = voltage_speed_angle
training_ready_candidate = true
breaker_opened = true
min_voltage_pu = 0.971757
max_voltage_pu = 1.063647
min_frequency_hz = 49.942069
max_frequency_hz = 50.043873
max_speed_deviation = 0.001159
max_rotor_angle_separation_deg = 60.015942
signal_source_summary includes frequency=generator_speed_proxy
```

Clean lab L02 was merged into the formal fault summary:

```text
output = results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02.csv
num_training_ready_handwired_rows = 2
num_training_ready_handwired_rows_by_line = {"L01": 1, "L02": 1}
static_topology_disable_overwrote_handwired = false
```

Updated dynamic label gate:

```text
num_training_ready_handwired_line_trip_labels = 2
num_unique_handwired_line_ids = 2
num_training_ready_labels = 4
allowed_for_dynamic_aware_training = false
```

The old handwired model's L02 timeout row remains a failed historical result
and is not promoted to training-ready. The model remains `phasor_RMS`, not EMT.
`generator_speed_proxy` is not direct frequency. The handwired breaker remains
pilot breaker-like validation, not engineering-grade protection. No `.slx`,
`.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries are committed.
The next manual target is L03 in the clean breaker lab, not the old handwired
model.

Validation:

```text
python -m pytest tests/test_ieee39_clean_breaker_lab_prepare.py tests/test_ieee39_clean_breaker_lab_checklist.py tests/test_ieee39_clean_breaker_lab_validation_schema.py tests/test_ieee39_clean_breaker_lab_isolated_summary.py tests/test_ieee39_clean_breaker_lab_docs.py
7 passed

python -m pytest tests/test_ieee39_multi_handwired_checklist.py tests/test_ieee39_multi_handwired_validation_schema.py tests/test_ieee39_multi_handwired_line_trip_summary.py tests/test_ieee39_handwired_fault_summary_merge.py tests/test_ieee39_multi_handwired_label_gate.py tests/test_ieee39_multi_handwired_docs.py
7 passed

python -m pytest tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_measurement_quality_gate.py tests/test_ieee39_measurement_docs.py tests/test_ieee39_signal_extraction_summary.py tests/test_ieee39_timed_trip_summary.py tests/test_ieee39_timed_trip_docs.py
8 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

## IEEE39 Per-Line Clean Breaker Lab Workflow

The clean breaker lab workflow is tightened after the L02 success. The target
dataset is a single-line dynamic label set, not a multi-line cascading trip
sequence. Therefore, each compact simulation must let only the target line's
breaker act.

If L03 is added to the same clean lab `.slx` that already contains L02, then
`L02_TripCommand` and `L03_TripCommand` can both act at 0.5 s. That changes the
case into an L02 + L03 simultaneous trip and it must not be treated as a
single-line L03 label.

New per-line workflow:

```text
one target line -> one independent clean lab .slx
next target = L03
per-line clean lab = results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx
L03 line block path = Grid/B10 to B13
L03 breaker name = L03_HandwiredTimedBreaker
L03 trip command name = L03_TripCommand
```

Added workflow files:

```text
matlab/simulink_ieee39/prepare_ieee39_clean_handwired_breaker_lab_for_line.m
scripts/gcn_search/print_ieee39_clean_breaker_lab_per_line_checklist.py
docs/ieee39_per_line_clean_breaker_lab_workflow.md
```

The per-line prepare script only copies the original generated wrapper. It does
not insert a breaker, does not modify Simscape physical-port wiring, and does
not commit the generated `.slx`.

The current successful L02 result is preserved:

```text
num_training_ready_handwired_line_trip_labels = 2
num_unique_handwired_line_ids = 2
num_training_ready_labels = 4
allowed_for_dynamic_aware_training = false
```

No L03 compact simulation is run in this round because the user has not yet
manually wired L03 in the per-line L03 clean lab. Dynamic-aware reranker
training remains blocked while labels remain below ten.

Validation:

```text
matlab:
prepare_ieee39_clean_handwired_breaker_lab_for_line("L03")
generated local .slx only; no breaker inserted

python scripts/gcn_search/print_ieee39_clean_breaker_lab_per_line_checklist.py
checklist generated

python -m pytest tests/test_ieee39_clean_breaker_lab_per_line_prepare.py tests/test_ieee39_clean_breaker_lab_per_line_checklist.py tests/test_ieee39_per_line_clean_breaker_lab_docs.py tests/test_ieee39_clean_breaker_lab_isolated_summary.py
7 passed

python -m pytest tests/test_ieee39_clean_breaker_lab_prepare.py tests/test_ieee39_clean_breaker_lab_checklist.py tests/test_ieee39_clean_breaker_lab_validation_schema.py tests/test_ieee39_clean_breaker_lab_docs.py
4 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

## IEEE39 Per-Line Clean L03 Success And Batch Lab Preparation

The user manually wired L03 in the per-line clean lab:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx
```

L03 validation and compact simulation passed:

```text
validation_passed = true
simulation_success = true
physical_fault_or_breaker_action_executed = true
trip_implementation = handwired_timed_breaker
measurement_extraction_status = voltage_speed_angle
training_ready_candidate = true
breaker_opened = true
source_model = clean_breaker_lab_L03
min_voltage_pu = 0.977216
max_voltage_pu = 1.065946
min_frequency_hz = 49.957951
max_frequency_hz = 50.021909
max_speed_deviation = 0.000841
max_rotor_angle_separation_deg = 59.185166
```

Clean L03 was merged into:

```text
results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03.csv
```

Updated label gate:

```text
num_training_ready_handwired_line_trip_labels = 5
num_unique_handwired_line_ids = 5
num_training_ready_labels = 7
allowed_for_dynamic_aware_training = false
```

Batch per-line lab preparation was added for the next user-wired lines:

```text
L04 -> results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L04.slx
L05 -> results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L05.slx
```

The batch prepare step only copies the original clean generated wrapper. It
does not insert breakers, modify Simscape physical-port wiring, or train the
dynamic-aware reranker. L04/L05 compact simulation is not run in this round
because the user has not manually wired those models yet.

Validation:

```text
python -m pytest tests/test_ieee39_clean_breaker_lab_batch_prepare.py tests/test_ieee39_clean_breaker_lab_batch_checklist.py tests/test_ieee39_clean_breaker_lab_batch_validation_schema.py tests/test_ieee39_clean_breaker_lab_batch_isolated_summary.py tests/test_ieee39_batch_per_line_clean_breaker_lab_docs.py
5 passed

python -m pytest tests/test_ieee39_clean_breaker_lab_prepare.py tests/test_ieee39_clean_breaker_lab_checklist.py tests/test_ieee39_clean_breaker_lab_validation_schema.py tests/test_ieee39_clean_breaker_lab_docs.py tests/test_ieee39_clean_breaker_lab_per_line_prepare.py tests/test_ieee39_clean_breaker_lab_per_line_checklist.py tests/test_ieee39_per_line_clean_breaker_lab_docs.py tests/test_ieee39_clean_breaker_lab_isolated_summary.py
11 passed

python -m pytest tests/test_ieee39_handwired_fault_summary_merge.py tests/test_ieee39_multi_handwired_label_gate.py
4 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

## Round 10: Simulink Dynamic Validation Prototype

Added a reproducible prototype for checking whether learned path reranker / PIO-GCN Top-K ordered N-2 paths also look risky in a simplified time-domain Simulink validation flow.

New files:

```text
src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py
src/gcn_search/legacy_rts79/export_rts79_simulink_basecase.py
src/gcn_search/legacy_rts79/make_mock_simulink_dynamic_results.py
src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py
matlab/simulink_rts79/build_rts79_swing_simulink_model.m
matlab/simulink_rts79/run_rts79_dynamic_path_case.m
matlab/simulink_rts79/run_rts79_dynamic_batch.m
matlab/simulink_rts79/README.md
docs/pio_gcn_simulink_dynamic_validation_plan.md
```

Workflow:

```text
learned reranker / PIO-GCN Top-K paths
-> export two trip events per ordered N-2 path
-> generate simplified RTS-79 Simulink scaffold from MATLAB script
-> run MATLAB batch when Simulink is available
-> analyze dynamic_precision@K and OPA/dynamic overlap
```

Current limitation: this is a Simulink dynamic validation prototype only. It is not EMT, not a real engineering-grade dynamic model, not a renewable dynamic model, and mock results are only for no-MATLAB workflow testing.

## Round 11: Simplified Swing-Equation Trajectory Engine

Round 11 moves the dynamic validation scaffold from event export plus mock metrics to a real simplified electromechanical trajectory workflow.

Implemented changes:

```text
src/gcn_search/legacy_rts79/export_simulink_dynamic_cases.py --input-csv
src/gcn_search/legacy_rts79/analyze_simulink_dynamic_results.py --dynamic-truth-csv
matlab/simulink_rts79/simulate_rts79_swing_case.m
matlab/simulink_rts79/run_rts79_dynamic_path_case.m
matlab/simulink_rts79/run_rts79_dynamic_batch.m
```

The MATLAB engine reads RTS-79 basecase CSV files, applies two ordered line-trip events segment by segment, integrates a simplified multi-machine swing-equation model with `ode45`, and computes frequency nadir, frequency zenith, rotor-angle separation, and approximate line-loading metrics from the trajectory. MATLAB-generated rows are marked as `result_source=simulink_swing_prototype`; mock rows remain marked as `result_source=mock`.

Dynamic precision and dynamic recall are now separated. Top-K-only simulations report `dynamic_precision@K`; `dynamic_recall@K` is emitted only when a full dynamic truth CSV is provided or the result CSV is explicitly marked as full dynamic truth.

Current limitation: this is still a simplified swing-equation prototype. It is not EMT, has no renewable dynamics, has no detailed controls, uses assumed default dynamic parameters, and supplements rather than replaces improved OPA full-truth validation.

## Round 12: Real Top-K Dynamic Validation And Calibration

Round 12 adds the workflow needed to move from demo cases to real learned-reranker Top-K dynamic review.

New components:

```text
src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py
src/gcn_search/legacy_rts79/check_simulink_dynamic_sanity_artifacts.py
src/gcn_search/legacy_rts79/analyze_opa_dynamic_disagreement.py
matlab/simulink_rts79/check_rts79_swing_model_sanity.m
matlab/simulink_rts79/calibrate_rts79_swing_scales.m
matlab/simulink_rts79/run_real_topk_dynamic_validation.m
docs/pio_gcn_simulink_real_topk_validation.md
```

The real Top-K preparation script fails explicitly when a per-path ranking CSV is missing; it does not silently fall back to demo paths. The calibration scripts produce `no_disturbance_sanity.csv`, `swing_scale_grid.csv`, and `recommended_swing_options.json` as local ignored artifacts. OPA/dynamic disagreement diagnostics separate static OPA-critical but dynamic-stable cases from static non-critical but dynamic-unstable cases.

Current limitation: real Top-K dynamic precision depends on a local per-path ranking CSV. Demo precision must not be reported as a formal dynamic conclusion. No full dynamic truth means no dynamic recall.

Local validation note: in the current repository checkout, no tracked real per-path learned-reranker ranking CSV was found, so the end-to-end real Top-K entry was exercised with explicit demo fallback only. The no-disturbance sanity check passed with frequency max deviation 0 Hz, rotor-angle separation about 35.66 degrees, and max line loading ratio about 1.38. The full scale grid calibration was attempted but did not finish within the local timeout, so the temporary recommended options remain sanity-passing default prototype values until a complete calibration run is available.

## Round 13: Relay Threshold vs Security Constraint

Round 13 adds a prototype distinction between line security limits and relay thresholds.

Key logic:

```text
loading_ratio <= 1.0: no overload action
1.0 < loading_ratio <= beta: security redispatch/load shedding approximation
loading_ratio > beta: passive relay trip
```

The default `relay_beta` is `1.2`. This means `loading_ratio > 1.0` is a security constraint violation, not a relay trip by itself. The Simulink prototype now writes `dynamic_case_event_log_<case_id>.csv` with `active_trip_first_line`, `active_trip_second_line`, `security_redispatch_or_load_shed`, and `passive_relay_trip` event types. Summary rows include passive relay trip counts, security redispatch counts, dynamic load shedding, and separate maximum security and relay violation loading ratios.

Current limitation: the redispatch/load shedding step is an approximation near overloaded branch terminal buses. It is not a full OPF, not EMT, and not an engineering-grade dynamic model.

## Round 14: Event-Driven Closed-Loop Dynamic Prototype

Round 13 separated relay/security events in post-processing. Round 14 upgrades the prototype to an event-driven closed-loop simulation:

- scheduled active trips change `offlineLines` before later integration segments;
- passive relay trips add the tripped line to `offlineLines`, so subsequent segments rebuild topology without that line;
- security redispatch/load shedding updates `currentLoads` and scales the subsequent `Pm` approximation through `update_swing_power_after_load_shed.m`;
- the event loop repeats until simulation end, `max_passive_trip_rounds`, or `max_event_rounds`.

Round 14 also adds two MATLAB demos:

- mild overload demo: validates `1.0 < loading_ratio <= beta` causes `security_redispatch_or_load_shed` and no passive relay trip;
- severe overload demo: validates `loading_ratio > beta` causes passive relay trip.

Current limitation: this is still a simplified swing-equation prototype. Redispatch/load shedding is not full OPF, relay logic is not an engineering-grade protection model, and demos are not formal dynamic stability conclusions.

## Round 15: Real Learned-Reranker Top-K Event-Driven Dynamic Validation

Round 15 connects the event-driven closed-loop dynamic prototype to real learned path-reranker Top-K ranking artifacts when a local per-path CSV is available.

Added or updated:

```text
src/gcn_search/legacy_rts79/prepare_real_topk_for_simulink_dynamic.py
src/gcn_search/legacy_rts79/prepare_dynamic_method_comparison_topk.py
matlab/simulink_rts79/run_real_topk_event_driven_dynamic_validation.m
docs/pio_gcn_simulink_real_topk_event_driven_validation.md
tests/test_real_topk_dynamic_pipeline.py
tests/test_dynamic_method_comparison_inputs.py
```

The preparation script now searches common local ignored ranking directories and writes:

```text
results/gcn_search/simulink_dynamic_real_topk/real_topk_input_paths.csv
```

with `case_id`, `source_seed`, `path_rank`, `path`, `first_line`, `second_line`, `pio_score`, `paper_score`, `lodf_score`, `reranker_score`, `opa_is_critical`, and `opa_total_load_shed_mw`.

Default behavior is strict: if no real per-path ranking CSV is available, the script fails. Demo fallback is only enabled by `--allow-demo-fallback` and is for interface testing only.

Method-comparison input preparation can create learned-reranker, PIO-GCN, and LODF Top-K dynamic input CSVs from the same per-path table when the relevant score columns exist.

Required validation commands for this round:

```powershell
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
git diff -- src/rl_mitigation scripts/rl_mitigation
```

## Round 31 - Handwired IEEE39 timed breaker validation flow

Round 31 stops automatic Simscape physical-port breaker insertion. The workflow now assumes the user will manually wire L01 in Simulink GUI and save a local handwired wrapper copy. Codex scripts then validate the handwired copy and update the label gate.

New files:

- `matlab/simulink_ieee39/validate_ieee39_handwired_breaker_model.m`
- `scripts/gcn_search/print_ieee39_handwired_breaker_checklist.py`
- `docs/ieee39_handwired_breaker_validation.md`

Generated compact outputs:

- `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/handwired_breaker_checklist.txt`
- `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_validation_summary.json`
- `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_block_inventory.csv`

Current result:

- `handwired_model_found = false`
- `validation_passed = false`
- `validation_failure_reason = handwired model file not found`
- `num_training_ready_handwired_line_trip_labels = 0`
- `num_training_ready_labels = 2`
- `allowed_for_dynamic_aware_training = false`

Boundary:

- The handwired `.slx` is a local artifact and must not be committed.
- A handwired breaker is a pilot breaker-like validation path, not engineering-grade protection.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- `static_topology_disable` cannot become a training-ready label.

Validation commands:

```bash
python -m pytest tests/test_ieee39_handwired_breaker_validation_schema.py tests/test_ieee39_handwired_label_gate.py tests/test_ieee39_handwired_docs.py tests/test_ieee39_handwired_checklist.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
git diff -- src/rl_mitigation scripts/rl_mitigation
```

## Round 30 - IEEE39 timed line-trip insertion probe

Round 30 specifically targeted the remaining `single_line_trip` gap. The goal was to determine whether L01 could be upgraded from `static_topology_disable` to a true in-simulation timed controlled switch / pilot breaker-like trip.

New MATLAB scripts:

- `matlab/simulink_ieee39/inspect_ieee39_line_ports.m`
- `matlab/simulink_ieee39/find_compatible_ieee39_breaker_blocks.m`
- `matlab/simulink_ieee39/probe_ieee39_breaker_insertion_standalone.m`
- `matlab/simulink_ieee39/insert_ieee39_timed_line_switch.m`

New docs:

- `docs/ieee39_timed_line_trip_probe_status.md`
- `docs/ieee39_timed_breaker_manual_wiring_guide.md`

MATLAB command sequence:

```matlab
inspect_ieee39_line_ports(... L01 ...)
find_compatible_ieee39_breaker_blocks(...)
probe_ieee39_breaker_insertion_standalone(...)
insert_ieee39_timed_line_switch(...)
run_ieee39_fault_test_suite(... ["no_fault_sanity", "three_phase_fault_clear", "single_line_trip", "relay_trip_test"], 0.5)
```

Key result:

- L01 exposes four Simscape physical ports.
- Breaker/switch candidates were found in installed libraries.
- Standalone probe did not find an unambiguous four-physical-port controlled breaker/switch suitable for safe automatic wrapper rewiring.
- `insertion_success = false`
- `trip_implementation = static_topology_disable`
- `single_line_trip training_ready_candidate = false`
- `num_training_ready_timed_line_trip_labels = 0`
- `num_training_ready_labels = 2`
- `measurement_quality_status = partial_dynamic_measurements`
- `label_quality_status = partial_physical_execution`
- `allowed_for_dynamic_aware_training = false`

Boundary:

- `static_topology_disable` is not a timed breaker.
- A future `timed_controlled_switch` is only a pilot breaker-like trip, not engineering-grade protection.
- Frequency remains `generator_speed_proxy`, not a direct frequency measurement.
- The model remains `phasor_RMS`, not EMT.
- Dynamic-aware reranker training remains blocked while `num_training_ready_labels < 10`.

Validation commands:

```bash
python -m pytest tests/test_ieee39_line_port_inventory.py tests/test_ieee39_breaker_candidate_inventory.py tests/test_ieee39_breaker_probe_summary.py tests/test_ieee39_timed_switch_insertion_summary.py tests/test_ieee39_timed_trip_docs.py
python -m pytest tests/test_ieee39_model_inventory.py tests/test_ieee39_dynamic_label_schema.py tests/test_ieee39_graphical_status_docs.py tests/test_ieee39_line_breaker_mapping.py tests/test_ieee39_fault_test_summary.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_relay_proxy_docs.py tests/test_ieee39_real_fault_summary_schema.py tests/test_ieee39_signal_extraction_summary.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_real_fault_docs.py tests/test_ieee39_simlog_inventory.py tests/test_ieee39_measurement_quality_gate.py tests/test_ieee39_timed_trip_summary.py tests/test_ieee39_measurement_docs.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
git diff -- src/rl_mitigation scripts/rl_mitigation
```

## Round 25: Robustness, Bootstrap CI, And Report-Ready Diagnostic Result

Round 25 turns the Round 24 nondegenerate dynamic comparison into a report-ready preliminary diagnostic result. No new MATLAB simulation is required; this round uses the Round 24 event-strength calibrated results.

Robustness summary:

```text
num_nondegenerate_settings = 9
learned_best_count = 0
pio_best_count = 9
lodf_best_count = 0
learned_advantage_robust = false
top100_best_method = pio_gcn
```

Bootstrap CI highlights:

```text
learned_precision_minus_pio_gcn Top100 = -0.09, 95% CI [-0.22, 0.04]
learned_precision_minus_lodf Top100 = -0.03, 95% CI [-0.15, 0.09]
learned_stress_minus_pio_gcn Top100 = -0.0158, 95% CI [-0.0474, 0.0133]
```

Report-ready figures:

```text
results/gcn_search/simulink_dynamic_method_comparison_figures/fig_dynamic_precision_top50_top100.png
results/gcn_search/simulink_dynamic_method_comparison_figures/fig_mean_dynamic_stress_top50_top100.png
results/gcn_search/simulink_dynamic_method_comparison_figures/fig_rank_depth_stress_curve.png
results/gcn_search/simulink_dynamic_method_comparison_figures/fig_opa_dynamic_alignment.png
```

Preliminary report:

```text
docs/pio_gcn_dynamic_preliminary_diagnostic_report.md
```

Gate conclusion:

```text
report_conclusion = no_dynamic_advantage_observed_preliminary
```

Conservative conclusion: no observed learned dynamic advantage in the current simplified swing-equation preliminary diagnostic. PIO-GCN Top100 precision is higher than learned under the current calibrated setting. No dynamic recall is reported because no full dynamic truth exists. This is not EMT, not full OPF, has no renewable dynamic model, and has no exciter, governor, or PSS models.

Validation to run:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py tests/test_post_fault_sanity_ladder.py tests/test_dynamic_interpretability_gate.py tests/test_negative_control_v3_summary.py tests/test_dynamic_method_comparison_cases.py tests/test_dynamic_method_comparison_analysis.py tests/test_dynamic_rank_depth_curve.py tests/test_non_smoke_path_reranker_dataset.py tests/test_non_smoke_dynamic_method_comparison.py tests/test_non_smoke_label_dynamic_alignment.py tests/test_dynamic_topk_case_coverage.py tests/test_post_fault_event_strength_calibration.py tests/test_event_strength_dynamic_summary.py tests/test_event_strength_robustness.py tests/test_dynamic_method_bootstrap_ci.py tests/test_dynamic_method_figures.py tests/test_preliminary_diagnostic_report.py

python scripts/gcn_search/check_pio_gcn_artifacts.py

git diff -- src/rl_mitigation scripts/rl_mitigation
```

## Round 24: TopK Coverage Fix And Event Strength Calibration

Round 24 first fixes non-smoke TopK case coverage, then calibrates post-fault event strength so the simplified dynamic layer is no longer all-stable or all-unstable. This remains a preliminary diagnostic result, not a formal dynamic stability conclusion.

Coverage diagnosis after the fix:

| method | Top50 coverage | Top100 coverage |
| --- | ---: | ---: |
| learned_mlp | 1.0000 | 1.0000 |
| pio_gcn | 1.0000 | 1.0000 |
| lodf | 1.0000 | 1.0000 |

The Round 23 shortfall was caused by duplicate ordered N-2 paths in the input ranking. Round 24 uses `--ensure-unique-paths --fill-to-k` to fill from deeper ranks until enough unique valid paths are available.

Recommended event strength options:

```text
frequency_unstable_threshold_hz = 49.3
rotor_angle_unstable_threshold_deg = 180.0
damping_scale = 2.0
inertia_scale = 2.0
coupling_scale = 0.2
line_loading_scale = 0.002
relay_beta = 1.5
load_shed_step_fraction = 0.01
```

Event-strength calibrated result:

| method | Top50 precision | Top100 precision | Top50 mean stress | Top100 mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_mlp | 0.3000 | 0.2700 | 0.0985 | 0.0871 |
| pio_gcn | 0.3400 | 0.3600 | 0.0997 | 0.1029 |
| lodf | 0.2800 | 0.3000 | 0.0887 | 0.0900 |

The event-strength calibrated dynamic layer is nondegenerate:

```text
all_stable_warning = false
all_unstable_warning = false
nondegenerate_dynamic_layer = true
dynamic_discrimination_signal = false
allowed_next_step = report_no_dynamic_advantage_preliminary
```

OPA/dynamic alignment remains mixed. Learned Top100 has `corr(stress, OPA shed) = 0.1211` and `corr(dynamic_unstable, OPA critical) = 0.1461`, but learned Top100 precision is lower than PIO-GCN, so there is no learned dynamic advantage observed.

Commands:

```powershell
python src/gcn_search/legacy_rts79/prepare_dynamic_method_comparison_topk.py --input-csv results/gcn_search/simulink_dynamic_real_per_path_ranking_non_smoke/learned_mlp_per_path_ranking.csv --output-dir results/gcn_search/simulink_dynamic_method_comparison_inputs_non_smoke_top100 --top-k 100 --ensure-unique-paths --fill-to-k

python src/gcn_search/legacy_rts79/export_dynamic_method_comparison_cases.py --input-root results/gcn_search/simulink_dynamic_method_comparison_inputs_non_smoke_top100 --output-root results/gcn_search/simulink_dynamic_method_comparison_cases_non_smoke --top-k 50 100 --event-1-time 1.0 --event-2-time 5.0 --simulation-end-time 10.0

python src/gcn_search/legacy_rts79/diagnose_dynamic_topk_case_coverage.py --ranking-csv results/gcn_search/simulink_dynamic_real_per_path_ranking_non_smoke/learned_mlp_per_path_ranking.csv --input-root results/gcn_search/simulink_dynamic_method_comparison_inputs_non_smoke_top100 --cases-root results/gcn_search/simulink_dynamic_method_comparison_cases_non_smoke --results-root results/gcn_search/simulink_dynamic_method_comparison_results_non_smoke_event_strength --output-dir results/gcn_search/simulink_dynamic_method_comparison_non_smoke_summary

python src/gcn_search/legacy_rts79/calibrate_post_fault_event_strength.py --cases-root results/gcn_search/simulink_dynamic_method_comparison_cases_non_smoke --basecase-path results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json --output-dir results/gcn_search/simulink_dynamic_event_strength_calibration --results-root results/gcn_search/simulink_dynamic_method_comparison_results_non_smoke --max-cases-per-group 30 --run-matlab
```

MATLAB rerun:

```matlab
run_dynamic_method_comparison_batch( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_cases_non_smoke", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_results_non_smoke_event_strength", ...
  "../../results/gcn_search/simulink_dynamic_event_strength_calibration/recommended_event_strength_options.json", ...
  100 ...
)
```

No dynamic recall is reported because no full dynamic truth exists. Generated `.slx`, `.mat`, full per-case results, full per-path ranking, event logs, and raw trajectories remain local ignored artifacts and are not intended for commit.

Validation to run:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py tests/test_post_fault_sanity_ladder.py tests/test_dynamic_interpretability_gate.py tests/test_negative_control_v3_summary.py tests/test_dynamic_method_comparison_cases.py tests/test_dynamic_method_comparison_analysis.py tests/test_dynamic_rank_depth_curve.py tests/test_non_smoke_path_reranker_dataset.py tests/test_non_smoke_dynamic_method_comparison.py tests/test_non_smoke_label_dynamic_alignment.py tests/test_dynamic_topk_case_coverage.py tests/test_post_fault_event_strength_calibration.py tests/test_event_strength_dynamic_summary.py

python scripts/gcn_search/check_pio_gcn_artifacts.py

git diff -- src/rl_mitigation scripts/rl_mitigation
```

If no real per-path ranking CSV is found in the local checkout, the correct status is: real per-path ranking CSV not available; real Top-K dynamic validation was not run.

Local validation result:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py
18 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

Automatic real CSV search was run without demo fallback. After excluding generated `simulink_dynamic*` artifacts and non-RTS-79 files, no real learned-reranker per-path ranking CSV was found in the local checkout. Therefore real Top-K dynamic validation was not run in this round. RL mitigation files were not modified.

## Round 16: Per-Path Ranking Export And Real Top-K Dynamic Smoke Pipeline

Round 16 addresses the main Round 15 blocker: the checkout did not contain a real learned-reranker per-path ranking CSV. The new workflow adds a reproducible local export path and a one-step dynamic smoke pipeline.

Added:

```text
src/gcn_search/legacy_rts79/export_path_reranker_per_path_ranking.py
src/gcn_search/legacy_rts79/run_real_topk_dynamic_validation_pipeline.py
src/gcn_search/legacy_rts79/summarize_real_topk_dynamic_validation.py
docs/pio_gcn_simulink_real_topk_dynamic_smoke.md
tests/test_export_path_reranker_per_path_ranking.py
tests/test_real_topk_dynamic_validation_pipeline.py
tests/test_real_topk_dynamic_summary.py
```

The per-path exporter normalizes local learned-reranker artifacts into:

```text
learned_mlp_per_path_ranking.csv
```

with the required path, score, OPA label, split, and method fields. This full CSV is a local ignored runtime artifact and should not be committed. If dataset/model artifacts are unavailable, the exporter fails explicitly and asks the user to run the dataset builder and training script first.

The pipeline wrapper can generate dynamic inputs and a MATLAB command file with `--skip-matlab`, or attempt MATLAB execution with `--run-matlab`. The summary script reports dynamic precision, OPA/dynamic overlap, and relay/security counts. It does not report dynamic recall without full dynamic truth.

Round 16 validation commands:

```powershell
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
git diff -- src/rl_mitigation scripts/rl_mitigation
```

Local validation result:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py
23 passed
```

Real export attempt:

```text
python src/gcn_search/legacy_rts79/export_path_reranker_per_path_ranking.py --dataset-dir results/gcn_search/path_reranker_dataset --model-dir results/gcn_search/path_reranker_models --output-dir results/gcn_search/simulink_dynamic_real_per_path_ranking --method learned_mlp_reranker_strict --split test --top-k 20 50 100 --retrain-if-missing
RuntimeError: path reranker dataset/model artifacts not available; run build_path_reranker_dataset.py and train_path_reranker.py first.
```

Pipeline attempt:

```text
python src/gcn_search/legacy_rts79/run_real_topk_dynamic_validation_pipeline.py --top-k 20 --max-cases 20 --skip-matlab --output-dir results/gcn_search/simulink_dynamic_real_pipeline
RuntimeError: path reranker dataset/model artifacts not available; run build_path_reranker_dataset.py and train_path_reranker.py first.
```

Therefore no real learned-reranker per-path ranking CSV was exported in this checkout, no retraining was performed, MATLAB was not run, and no real Top20/Top50/Top100 dynamic validation result was produced in Round 16.

Artifact check:

```text
python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

RL mitigation files were not modified.

## Round 17: Rebuilt Learned-Reranker Per-Path Ranking Export and Top20 Dynamic Smoke

Round 17 fixes the upstream blocker from Round 16. Git history contained historical path-reranker source scripts, so the source files were restored and adapted into a minimal reproducible smoke pipeline:

```text
src/gcn_search/legacy_rts79/build_path_reranker_dataset.py
src/gcn_search/legacy_rts79/train_path_reranker.py
src/gcn_search/legacy_rts79/evaluate_path_reranker_strict_heldout.py
```

The restored pipeline generated local ignored artifacts:

```text
results/gcn_search/path_reranker_dataset/path_reranker_dataset.csv
results/gcn_search/path_reranker_models/path_reranker_model.pkl
results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking.csv
```

Dataset stats:

```text
num_samples = 1000
num_critical = 17
positive_ratio = 0.017
train_seeds = 20260722, 20260723, 20260724
test_seeds = 20260726
smoke = true
```

MATLAB Top20 preliminary dynamic smoke was run through:

```powershell
python src/gcn_search/legacy_rts79/run_real_topk_dynamic_validation_pipeline.py --retrain-if-missing --smoke --top-k 20 --max-cases 20 --max-paths-per-seed 200 --run-matlab --output-dir results/gcn_search/simulink_dynamic_real_pipeline
```

Compact summary:

```text
result_scope = top20_preliminary_dynamic_smoke
num_dynamic_cases = 20
dynamic_precision_at_k = 1.0
opa_critical_and_dynamic_unstable_count = 1
opa_critical_but_dynamic_stable_count = 0
opa_noncritical_but_dynamic_unstable_count = 19
cases_with_security_redispatch_or_load_shed = 0
cases_with_passive_relay_trip = 20
total_dynamic_load_shed_mw = 0.0
matlab_executed = true
```

No dynamic recall is reported because no full dynamic truth is available. This remains a simplified swing-equation Top20 preliminary dynamic smoke, not a formal engineering dynamic stability conclusion.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py
26 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

RL mitigation files were not modified. Generated `.pkl`, `.slx`, `.mat`, full per-path ranking, and raw dynamic artifacts remain local ignored artifacts and are not intended for commit.

## Round 18: Non-Degeneracy Diagnostics and Event-Driven Calibration

Round 18 fixes the documentation mismatch by treating the tracked CSV as authoritative:

```text
opa_critical_and_dynamic_unstable_count = 1
opa_noncritical_but_dynamic_unstable_count = 19
```

The default Top20 dynamic smoke showed:

```text
dynamic_precision_at_k = 1.0
cases_with_passive_relay_trip = 20
cases_with_security_redispatch_or_load_shed = 0
degeneracy_warning = true
```

This is a non-degeneracy warning. It does not prove the pipeline is wrong; it indicates that default dynamic scale parameters are too sensitive for interpretation.

Added:

```text
src/gcn_search/legacy_rts79/analyze_dynamic_smoke_degeneracy.py
matlab/simulink_rts79/calibrate_event_driven_dynamic_scales.m
src/gcn_search/legacy_rts79/compare_default_vs_calibrated_dynamic_smoke.py
```

Small calibration grid recommendation:

```text
line_loading_scale = 0.005
coupling_scale = 0.5
damping_scale = 1.0
inertia_scale = 1.0
relay_beta = 1.2
```

Calibrated Top20 result:

```text
dynamic_precision_at_k = 1.0
cases_with_passive_relay_trip = 0
cases_with_security_redispatch_or_load_shed = 20
total_dynamic_load_shed_mw = 231.32117491281207
opa_critical_and_dynamic_unstable_count = 1
opa_noncritical_but_dynamic_unstable_count = 19
degeneracy_warning = true
```

Calibration removed the all-passive-relay-trip degeneracy, but all cases remain dynamically unstable, so the calibrated smoke still carries a degeneracy warning. No dynamic recall is reported because no full dynamic truth exists. This remains a simplified swing-equation preliminary dynamic smoke, not EMT, not full OPF, and not an engineering-grade dynamic stability conclusion.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py
30 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

RL mitigation files were not modified. Generated `.pkl`, `.slx`, `.mat`, raw per-case calibration outputs, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.

## Round 19: Dynamic Instability Reasons and Negative Controls

Round 19 diagnoses the calibrated Top20 result from Round 18. The goal is to answer whether the event-driven dynamic validation layer has discrimination, or whether it still marks almost every tested path as unstable.

Added:

```text
src/gcn_search/legacy_rts79/analyze_dynamic_instability_reasons.py
src/gcn_search/legacy_rts79/compute_dynamic_stress_score.py
src/gcn_search/legacy_rts79/prepare_dynamic_negative_control_inputs.py
src/gcn_search/legacy_rts79/run_dynamic_negative_control_pipeline.py
matlab/simulink_rts79/run_dynamic_negative_control_batch.m
tests/test_dynamic_instability_reasons.py
tests/test_dynamic_stress_score.py
tests/test_dynamic_negative_controls.py
docs/pio_gcn_simulink_dynamic_negative_controls.md
```

The MATLAB stability classifier was checked. Security redispatch/load shedding is not directly treated as `dynamic_unstable`. The calibrated Top20 instability reasons are frequency and rotor-angle based:

```text
num_cases = 20
dynamic_unstable_count = 20
frequency_nadir_below_threshold = 20
rotor_angle_above_threshold = 20
relay_violation_not_eliminated = 0
sim_failed = 0
passive_relay_trip_count = 0
security_redispatch_count = 38
```

Round 19 negative-control command:

```powershell
python src/gcn_search/legacy_rts79/run_dynamic_negative_control_pipeline.py `
  --input-csv results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking.csv `
  --output-dir results/gcn_search/simulink_dynamic_negative_controls `
  --top-k 20 `
  --run-matlab `
  --options-json-path results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json
```

Negative-control result:

| group | dynamic precision@20 | passive relay trips | security actions | mean dynamic stress |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 1.0000 | 0 | 20 | 4.9614 |
| low_score_top20 | 1.0000 | 0 | 15 | 5.1883 |
| random_top20 | 1.0000 | 0 | 18 | 4.9650 |
| line_order_top20 | 1.0000 | 0 | 12 | 4.9756 |

Summary:

```text
global_degeneracy_warning = true
dynamic_discrimination_signal = false
matlab_executed = true
```

Interpretation: the calibrated dynamic layer still lacks discrimination because all four groups are 20/20 dynamically unstable and the learned group is not more stressful than all controls. Therefore dynamic precision@20 should not be used as a performance claim at this stage. No dynamic recall is reported because no full dynamic truth set exists.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py
35 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.
```

RL mitigation files were not modified. Generated `.pkl`, `.slx`, `.mat`, dynamic case folders, raw event logs, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.

## Round 20: Swing Equilibrium Sanity and Threshold Sensitivity

Round 20 addresses the Round 19 problem that all negative-control groups were 20/20 dynamically unstable. The aim is not to tune thresholds for a nicer precision number; the aim is to check whether the swing-equation dynamic layer has a stable no-trip baseline and whether threshold sensitivity gives any diagnostic separation.

Added:

```text
matlab/simulink_rts79/initialize_swing_equilibrium.m
matlab/simulink_rts79/run_swing_equilibrium_sanity_demo.m
src/gcn_search/legacy_rts79/analyze_swing_equilibrium_diagnostics.py
src/gcn_search/legacy_rts79/analyze_dynamic_threshold_sensitivity.py
src/gcn_search/legacy_rts79/summarize_dynamic_negative_controls_v2.py
tests/test_swing_equilibrium_diagnostics.py
tests/test_dynamic_threshold_sensitivity.py
tests/test_negative_controls_v2_summary.py
docs/pio_gcn_swing_equilibrium_and_threshold_calibration.md
```

MATLAB sanity command:

```matlab
run_swing_equilibrium_sanity_demo( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_equilibrium_sanity" ...
)
```

No-trip sanity result:

```text
no_trip_dynamic_unstable = false
no_trip_frequency_nadir_hz = 50.0
no_trip_frequency_zenith_hz = 50.0
no_trip_final_mean_frequency_hz = 50.0
no_trip_max_rotor_angle_separation_coi_deg = 18.671415861494207
pre_event_frequency_drift_hz_per_s = 0.0
initial_pm_pe_residual_norm = 0.0
initial_pm_pe_max_abs_residual = 0.0
sanity_passed = true
dynamic_model_equilibrium_failed = false
```

This fixes the baseline equilibrium sanity: no active trip stays stable. However:

```text
single_mild_trip_dynamic_unstable = true
low_risk_n2_dynamic_unstable = true
```

Updated negative controls v2:

| group | default unstable fraction | relaxed-threshold unstable fraction | passive trip fraction | mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 1.00 | 1.00 | 1.00 | 26.1084 |
| low_score_top20 | 1.00 | 0.70 | 0.75 | 11.7528 |
| random_top20 | 1.00 | 0.90 | 0.90 | 16.1437 |
| line_order_top20 | 1.00 | 0.40 | 0.60 | 9.1307 |

Threshold sensitivity:

```text
num_threshold_cases = 80
all_groups_unstable_for_all_thresholds = false
has_threshold_discrimination_signal = true
interpretation = threshold sensitivity only; not a formal dynamic conclusion
```

Interpretation: the COI and equilibrium changes make the no-trip baseline physically sane, but default-threshold Top20 dynamic validation remains globally degenerate. The sensitivity scan suggests there may be separability under relaxed thresholds, but this is a calibration clue only and must not be reported as a formal learned-method result. No dynamic recall is reported because no full dynamic truth exists.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py
40 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

RL mitigation files were not modified. Generated `.slx`, `.mat`, dynamic case folders, raw event logs, full per-case dynamic results, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.

## Round 21: Post-Fault Sanity Ladder Calibration

Round 21 calibrates post-fault dynamic response after Round 20 made no-trip stable. The purpose is not to improve learned precision; it is to make low-risk and random controls physically interpretable.

Added:

```text
matlab/simulink_rts79/run_post_fault_sanity_ladder.m
matlab/simulink_rts79/calibrate_post_fault_dynamic_response.m
src/gcn_search/legacy_rts79/check_dynamic_interpretability_gate.py
docs/pio_gcn_post_fault_sanity_ladder.md
tests/test_post_fault_sanity_ladder.py
tests/test_dynamic_interpretability_gate.py
tests/test_negative_control_v3_summary.py
```

MATLAB commands:

```matlab
run_post_fault_sanity_ladder( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_negative_controls/inputs", ...
  "../../results/gcn_search/simulink_dynamic_post_fault_sanity", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json" ...
)

calibrate_post_fault_dynamic_response( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_negative_controls/inputs", ...
  "../../results/gcn_search/simulink_dynamic_calibration", ...
  4 ...
)
```

Recommended post-fault options:

```text
damping_scale = 2
inertia_scale = 2
coupling_scale = 0.2
line_loading_scale = 0.002
relay_beta = 1.5
load_shed_step_fraction = 0.01
pm_update_mode = rebalance_to_current_pe
```

Post-fault sanity ladder with recommended options:

| case group | unstable fraction | passive trip fraction | mean stress | passed |
| --- | ---: | ---: | ---: | --- |
| no_trip | 0.00 | 0.00 | 0.0000 | true |
| single_mild_trip | 0.00 | 0.00 | 0.2423 | true |
| low_risk_ordered_n2 | 0.00 | 0.00 | 0.1137 | true |
| random_ordered_n2 | 0.00 | 0.00 | 0.0782 | true |
| learned_high_risk_n2 | 0.00 | 0.00 | 0.1137 | true |

Negative controls v3:

| group | unstable fraction | mean frequency nadir | mean stress | passive trip fraction |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 0.00 | 49.3998 | 0.1002 | 0.00 |
| low_score_top20 | 0.00 | 49.3804 | 0.1217 | 0.00 |
| random_top20 | 0.00 | 49.3682 | 0.1336 | 0.00 |
| line_order_top20 | 0.00 | 49.4051 | 0.0986 | 0.00 |

Interpretability gate:

```text
no_trip_passed = true
single_mild_trip_passed = true
low_risk_not_all_unstable = true
random_not_all_unstable = true
controls_have_variation = true
default_dynamic_precision_interpretable = true
allowed_next_step = expand_top50_top100
```

Interpretation: Round 21 removes the all-unstable post-fault degeneracy. However, the current Top20 v3 groups are all stable, so there is still no learned dynamic discrimination signal. Top50/Top100 expansion is allowed for diagnostic coverage, not as a formal performance conclusion. No dynamic recall is reported because no full dynamic truth exists.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py tests/test_post_fault_sanity_ladder.py tests/test_dynamic_interpretability_gate.py tests/test_negative_control_v3_summary.py
45 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

RL mitigation files were not modified. Generated `.slx`, `.mat`, full per-case dynamic results, raw event logs, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.

## Round 34: Clean Breaker Lab L06-L08 Batch Validation

This round batch-validates the user-handwired per-line clean breaker lab models
for L06, L07, and L08. It does not train the dynamic-aware reranker. The goal is
only to confirm that the three new single-line labels are structurally valid,
execute a breaker action in compact phasor_RMS simulation, and pass the compact
measurement gate.

MATLAB structure validation:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_lines_batch(string({'L06','L07','L08'}))
```

The batch validator now reads the extended line map, so the validated paths are:

```text
L06 -> IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B14 to B15
L07 -> IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B15 to B16
L08 -> IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B16 to B17
```

Compact isolated simulation:

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L06 L07 L08 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx" --timeout-seconds 240 --simulation-stop-time 0.5
```

Simulation results:

| line | simulation_success | measurement | training_ready | breaker_opened | min_voltage_pu | max_voltage_pu | min_frequency_hz | max_frequency_hz | max_speed_deviation | max_rotor_angle_separation_deg |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L06 | 1 | voltage_speed_angle | 1 | 1 | 0.981795 | 1.063500 | 49.992072 | 50.001596 | 0.000159 | 59.419548 |
| L07 | 1 | voltage_speed_angle | 1 | 1 | 0.977276 | 1.063500 | 49.965959 | 50.063884 | 0.001278 | 64.260372 |
| L08 | 1 | voltage_speed_angle | 1 | 1 | 0.980435 | 1.063500 | 49.922009 | 50.059338 | 0.001560 | 68.693688 |

The latest formal merged summary is:

```text
results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08.csv
```

Updated compact label gate:

```text
num_training_ready_labels = 10
num_training_ready_handwired_line_trip_labels = 8
num_unique_handwired_line_ids = 8
num_handwired_validation_passed = 8
allowed_for_dynamic_aware_training = true
ready_for_preview_training = true
```

Interpretation:

```text
The compact label gate is now sufficient for preview dynamic-aware reranker
training in a separate commit. This is not a final dynamic performance
conclusion. The model remains phasor_RMS, not EMT, and generator_speed_proxy is
not direct frequency.
```

Validation to run:

```powershell
python -m pytest tests/test_ieee39_wrapper_grid_line_inventory.py tests/test_ieee39_line_breaker_map_extension.py tests/test_ieee39_line_map_extension_docs.py tests/test_ieee39_clean_breaker_lab_batch_prepare.py tests/test_ieee39_clean_breaker_lab_batch_checklist.py tests/test_ieee39_clean_breaker_lab_batch_validation_schema.py tests/test_ieee39_clean_breaker_lab_batch_isolated_summary.py tests/test_ieee39_batch_per_line_clean_breaker_lab_docs.py

python -m pytest tests/test_ieee39_clean_breaker_lab_prepare.py tests/test_ieee39_clean_breaker_lab_checklist.py tests/test_ieee39_clean_breaker_lab_validation_schema.py tests/test_ieee39_clean_breaker_lab_docs.py tests/test_ieee39_clean_breaker_lab_per_line_prepare.py tests/test_ieee39_clean_breaker_lab_per_line_checklist.py tests/test_ieee39_per_line_clean_breaker_lab_docs.py tests/test_ieee39_clean_breaker_lab_isolated_summary.py

python -m pytest tests/test_ieee39_handwired_fault_summary_merge.py tests/test_ieee39_multi_handwired_label_gate.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_measurement_quality_gate.py

python -m pytest tests/test_ieee39_dynamic_aware_training_readiness.py

python scripts/gcn_search/check_pio_gcn_artifacts.py

git diff -- src/rl_mitigation scripts/rl_mitigation
```

Executed validation:

```text
python -m pytest tests/test_ieee39_wrapper_grid_line_inventory.py tests/test_ieee39_line_breaker_map_extension.py tests/test_ieee39_line_map_extension_docs.py tests/test_ieee39_clean_breaker_lab_batch_prepare.py tests/test_ieee39_clean_breaker_lab_batch_checklist.py tests/test_ieee39_clean_breaker_lab_batch_validation_schema.py tests/test_ieee39_clean_breaker_lab_batch_isolated_summary.py tests/test_ieee39_batch_per_line_clean_breaker_lab_docs.py
9 passed

python -m pytest tests/test_ieee39_clean_breaker_lab_prepare.py tests/test_ieee39_clean_breaker_lab_checklist.py tests/test_ieee39_clean_breaker_lab_validation_schema.py tests/test_ieee39_clean_breaker_lab_docs.py tests/test_ieee39_clean_breaker_lab_per_line_prepare.py tests/test_ieee39_clean_breaker_lab_per_line_checklist.py tests/test_ieee39_per_line_clean_breaker_lab_docs.py tests/test_ieee39_clean_breaker_lab_isolated_summary.py
11 passed

python -m pytest tests/test_ieee39_handwired_fault_summary_merge.py tests/test_ieee39_multi_handwired_label_gate.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_measurement_quality_gate.py tests/test_ieee39_dynamic_aware_training_readiness.py
11 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

RL mitigation files are not modified. Generated `.slx`, `.slxc`, `slprj`,
`.mat`, raw trajectories, and full timeseries remain local artifacts and are
not intended for commit.

## Round 35: IEEE39 Dynamic-Aware Reranker Preview Training

This round starts the preview dynamic-aware reranker training step after the
compact IEEE39 label gate reached ten training-ready labels. It is a
small-sample sanity check and workflow validation only, not a final dynamic
performance conclusion.

Gate check:

```text
num_training_ready_labels = 10
num_training_ready_handwired_line_trip_labels = 8
num_unique_handwired_line_ids = 8
allowed_for_dynamic_aware_training = true
ready_for_preview_training = true
```

Training command:

```powershell
python scripts/gcn_search/train_ieee39_dynamic_aware_reranker_preview.py ^
  --dynamic-label-summary results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json ^
  --training-readiness results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json ^
  --fault-summary-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08.csv ^
  --output-dir results/gcn_search/ieee39_dynamic_aware_reranker_preview ^
  --random-seed 42
```

Preview outputs:

```text
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_dataset.csv
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_config.json
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_metrics.json
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_predictions.csv
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_model_coefficients.csv
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_dynamic_aware_reranker_model.json
results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_readme.md
```

Preview metrics:

```text
num_samples = 10
target_columns = dynamic_stress_score, unstable_flag
cv_strategy = leave_one_out
regression_mae = 0.025776
regression_rmse = 0.034688
regression_spearman = 0.899700
classification_accuracy = 1.000000
classification_f1 = 1.000000
classification_roc_auc = 1.000000
```

Interpretation:

```text
The preview model can be trained and evaluated on the compact IEEE39 labels,
but the sample count is very small. The continuous dynamic_stress_score is
derived from compact dynamic measurements, and those measurements are also
included as features, so the metrics are likely optimistic. This is a workflow
sanity check only.
```

Boundaries:

```text
phasor_RMS, not EMT
generator_speed_proxy, not direct frequency
pilot breaker-like validation, not engineering-grade protection
preview only, not final dynamic performance conclusion
```

Validation:

```text
python -m pytest tests/test_ieee39_dynamic_aware_reranker_preview_training.py
3 passed

python -m pytest tests/test_ieee39_dynamic_aware_training_readiness.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_measurement_quality_gate.py tests/test_ieee39_handwired_fault_summary_merge.py tests/test_ieee39_multi_handwired_label_gate.py
11 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

No `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries are
included in the preview training artifacts.

## Round 36: Prepare Clean L09/L10 Breaker Labs

This round prepares the next independent per-line clean lab `.slx` files for
manual L09/L10 wiring. It does not automatically insert breakers, does not
modify Simscape physical-port wiring, does not run L09/L10 compact simulation,
and does not train the dynamic-aware reranker.

Extended line map check:

```text
L09 -> IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B16 to B24
L10 -> IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B17 to B27
```

MATLAB prepare command:

```matlab
cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
configure_ieee39_short_filegen_paths()
prepare_ieee39_clean_handwired_breaker_labs_for_lines(string({'L09','L10'}))
```

Prepare summary:

```text
L09 status = prepared
L09 target_created = true
L09 target_loadable = true
L09 clean_lab_committed = false
L10 status = prepared
L10 target_created = true
L10 target_loadable = true
L10 clean_lab_committed = false
```

Local-only prepared models:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L09.slx
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L10.slx
```

Checklist output:

```text
results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/clean_breaker_lab_batch_checklist.txt
```

After the user manually wires L09/L10, ask Codex to run:

```matlab
validate_ieee39_clean_breaker_lab_lines_batch(["L09","L10"])
```

If validation passes, ask Codex to run:

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L09 L10 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx" --timeout-seconds 240 --simulation-stop-time 0.5
```

Boundaries:

```text
phasor_RMS, not EMT
generator_speed_proxy, not direct frequency
pilot breaker-like validation, not engineering-grade protection
single-line labels only
.slx files remain local and are not committed
preview training already ran, but remains a workflow sanity check only
```

Validation:

```text
python -m pytest tests/test_ieee39_clean_breaker_lab_batch_prepare.py tests/test_ieee39_clean_breaker_lab_batch_checklist.py tests/test_ieee39_clean_breaker_lab_batch_validation_schema.py tests/test_ieee39_batch_per_line_clean_breaker_lab_docs.py
4 passed

python -m pytest tests/test_ieee39_dynamic_aware_reranker_preview_training.py tests/test_ieee39_dynamic_aware_training_readiness.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_measurement_quality_gate.py
8 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

No `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, full timeseries, or
large checkpoint files are committed. The L09/L10 `.slx` files remain local
manual-wiring targets.

## Round 32: Batch Validate Clean L04/L05 Per-Line Breaker Labs

Goal: validate the user-handwired per-line clean breaker lab models for L04 and L05, run isolated compact simulations, and merge only successful single-line labels into the formal IEEE39 dynamic-label summary.

Plain-language result: L04 and L05 are now both usable as pilot breaker-like single-line trip labels. The breaker blocks and trip commands were found, the compact phasor_RMS simulations completed, and voltage, generator speed proxy, and rotor-angle signals were extracted. This is still not EMT validation and not engineering-grade protection.

Commands:

```powershell
matlab -batch "cd('C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39'); configure_ieee39_short_filegen_paths(); validate_ieee39_clean_breaker_lab_lines_batch(string({'L04','L05'}));"

python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L04 L05 --timeout-seconds 240 --simulation-stop-time 0.5

python src/gcn_search/legacy_rts79/merge_ieee39_handwired_fault_summaries.py --base-summary-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03.csv --multi-handwired-summary-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_line_trip_summary.csv --output-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05.csv --output-summary-json results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l04_l05_merge_summary.json

python src/gcn_search/legacy_rts79/export_ieee39_dynamic_labels.py --fault-summary-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05.csv --event-log-csv results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_event_log.csv --output-dir results/gcn_search/ieee39_dynamic_labels
```

L04 compact result:

```text
validation_passed = true
simulation_success = true
measurement_extraction_status = voltage_speed_angle
training_ready_candidate = true
breaker_opened = true
min_voltage_pu = 0.970568931976294
max_voltage_pu = 1.06388416646219
min_frequency_hz = 49.9194265059914
max_frequency_hz = 50.0604917001817
max_speed_deviation = 0.0016114698801721
max_rotor_angle_separation_deg = 60.3441340196063
```

L05 compact result:

```text
validation_passed = true
simulation_success = true
measurement_extraction_status = voltage_speed_angle
training_ready_candidate = true
breaker_opened = true
min_voltage_pu = 0.976533231451396
max_voltage_pu = 1.06672687760572
min_frequency_hz = 49.9435041779294
max_frequency_hz = 50.0350763401759
max_speed_deviation = 0.0011299164414124
max_rotor_angle_separation_deg = 59.3996260385128
```

Updated label gate:

```text
merged_training_ready_handwired_lines = L01, L02, L03, L04, L05
latest_fault_summary = results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05.csv
num_training_ready_handwired_line_trip_labels = 5
num_unique_handwired_line_ids = 5
num_training_ready_labels = 7
num_handwired_validation_passed = 5
allowed_for_dynamic_aware_training = false
```

Important fix: the batch isolated runner now uses the batch validation table. When passing `--model-path-pattern` from PowerShell, quote the pattern so `{line_id}` is not consumed by PowerShell.

Validation to run:

```text
python -m pytest tests/test_ieee39_clean_breaker_lab_batch_prepare.py tests/test_ieee39_clean_breaker_lab_batch_checklist.py tests/test_ieee39_clean_breaker_lab_batch_validation_schema.py tests/test_ieee39_clean_breaker_lab_batch_isolated_summary.py tests/test_ieee39_batch_per_line_clean_breaker_lab_docs.py

python -m pytest tests/test_ieee39_clean_breaker_lab_prepare.py tests/test_ieee39_clean_breaker_lab_checklist.py tests/test_ieee39_clean_breaker_lab_validation_schema.py tests/test_ieee39_clean_breaker_lab_docs.py tests/test_ieee39_clean_breaker_lab_per_line_prepare.py tests/test_ieee39_clean_breaker_lab_per_line_checklist.py tests/test_ieee39_per_line_clean_breaker_lab_docs.py tests/test_ieee39_clean_breaker_lab_isolated_summary.py

python -m pytest tests/test_ieee39_handwired_fault_summary_merge.py tests/test_ieee39_multi_handwired_label_gate.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_measurement_quality_gate.py

python scripts/gcn_search/check_pio_gcn_artifacts.py

git diff -- src/rl_mitigation scripts/rl_mitigation
```

RL mitigation files were not modified. Generated `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, and full timeseries remain local-only and must not be committed.

## Round 33: Extend IEEE39 Wrapper Line Map For L06/L07/L08

Goal: extend the IEEE39 wrapper line map using real Simulink `Grid` block
inventory before any new manual breaker wiring. This round does not insert
breakers, does not modify Simscape physical-port wiring, does not run
L06/L07/L08 compact simulation, and does not train the dynamic-aware reranker.

Plain-language result: the wrapper was scanned read-only, and L06/L07/L08 were
mapped to real line blocks instead of guessed paths. Local clean lab `.slx`
copies were prepared for later user wiring only.

Commands:

```powershell
matlab -batch "cd('C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39'); configure_ieee39_short_filegen_paths(); inspect_ieee39_wrapper_grid_line_blocks();"

python scripts/gcn_search/update_ieee39_line_breaker_map_from_inventory.py

matlab -batch "cd('C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39'); configure_ieee39_short_filegen_paths(); prepare_ieee39_clean_handwired_breaker_labs_for_lines(string({'L06','L07','L08'}));"

python scripts/gcn_search/print_ieee39_clean_breaker_lab_batch_checklist.py
```

Inventory outputs:

```text
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.json
```

Extended map outputs:

```text
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extended.csv
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extension_summary.json
```

Verified next line paths:

```text
L06 -> IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B14 to B15
L07 -> IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B15 to B16
L08 -> IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B16 to B17
```

Local-only clean lab `.slx` files prepared:

```text
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L06.slx
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L07.slx
results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L08.slx
```

Current label gate remains:

```text
num_training_ready_labels = 7
num_training_ready_handwired_line_trip_labels = 5
num_unique_handwired_line_ids = 5
allowed_for_dynamic_aware_training = false
```

After the user manually wires L06/L07/L08, run:

```text
validate_ieee39_clean_breaker_lab_lines_batch(["L06","L07","L08"])

python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L06 L07 L08 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx" --timeout-seconds 240 --simulation-stop-time 0.5
```

Boundaries: phasor_RMS is not EMT; `generator_speed_proxy` is not direct
frequency; handwired breaker validation is pilot breaker-like, not
engineering-grade protection; `.slx`, `.slxc`, `slprj`, `.mat`, raw
trajectories, and full timeseries remain local-only and must not be committed.

## Round 31 Follow-up: Windows Path-Length Fix And Handwired Suite Validation

The handwired IEEE39 wrapper initially failed in Simulink build because generated
C files were written below the deep repository `results/.../generated_models`
tree, exceeding the Windows 260-character path limit. A short Simulink
file-generation helper was added:

```text
matlab/simulink_ieee39/configure_ieee39_short_filegen_paths.m
```

The helper redirects Simulink cache/code-generation folders to:

```text
C:\ieee39_codegen\cache
C:\ieee39_codegen\codegen
```

The helper is now called by:

```text
validate_ieee39_handwired_breaker_model.m
run_ieee39_fault_test_suite.m
```

The handwired validation logic was also tightened so the L01 breaker candidate
uses the actual block name `Grid/L01_HandwiredTimedBreaker` instead of matching
generic internal `Switch` blocks from generator control subsystems.

Validation result after the user handwired model was detected:

```text
handwired_model_found = true
handwired_model_loadable = true
breaker_block_path = IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker/Grid/L01_HandwiredTimedBreaker
trip_command_path = IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker/Grid/L01_TripCommand
validation_passed = true
```

The compact handwired fault suite completed for:

```text
no_fault_sanity
single_line_trip
three_phase_fault_clear
relay_trip_test
```

Key label-gate result:

```text
num_fault_rows = 4
num_physical_executed_rows = 3
num_training_ready_labels = 3
num_training_ready_handwired_line_trip_labels = 1
num_handwired_validation_passed = 1
handwired_model_used = true
handwired_model_committed = false
allowed_for_dynamic_aware_training = false
```

The training gate remains closed because `num_training_ready_labels < 10`.
The model remains `phasor_RMS`, not EMT, and the handwired breaker remains a
pilot breaker-like validation path, not engineering-grade protection.

Validation:

```text
python -m pytest tests/test_ieee39_handwired_breaker_validation_schema.py tests/test_ieee39_handwired_label_gate.py tests/test_ieee39_handwired_docs.py tests/test_ieee39_handwired_checklist.py tests/test_ieee39_model_inventory.py tests/test_ieee39_dynamic_label_schema.py tests/test_ieee39_graphical_status_docs.py tests/test_ieee39_line_breaker_mapping.py tests/test_ieee39_fault_test_summary.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_relay_proxy_docs.py tests/test_ieee39_real_fault_summary_schema.py tests/test_ieee39_signal_extraction_summary.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_real_fault_docs.py tests/test_ieee39_simlog_inventory.py tests/test_ieee39_measurement_quality_gate.py tests/test_ieee39_timed_trip_summary.py tests/test_ieee39_measurement_docs.py tests/test_ieee39_line_port_inventory.py tests/test_ieee39_breaker_candidate_inventory.py tests/test_ieee39_breaker_probe_summary.py tests/test_ieee39_timed_switch_insertion_summary.py tests/test_ieee39_timed_trip_docs.py
26 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

The local handwired `.slx`, generated `.slxc`, `slprj`, generated code cache,
large `.mat`, raw trajectories, and full timeseries remain uncommitted.

## Round 32: Multi-Line Handwired Breaker Expansion

Round 32 converts the validated L01 handwired timed breaker path into a
multi-line validation and label-expansion workflow. The workflow remains
manual-wiring first: Codex does not insert Simscape physical-port breakers and
does not save or commit the handwired `.slx`.

Added:

```text
scripts/gcn_search/print_ieee39_multi_handwired_breaker_checklist.py
matlab/simulink_ieee39/validate_ieee39_multi_handwired_breakers.m
matlab/simulink_ieee39/run_ieee39_multi_handwired_line_trip_suite.m
src/gcn_search/legacy_rts79/merge_ieee39_handwired_fault_summaries.py
docs/ieee39_multi_handwired_breaker_expansion.md
```

Current result with the existing local handwired model:

```text
recommended next batch = L02, L03, L04
validation_passed line IDs = L01
validation_passed count = 1
multi line-trip simulation_success count = 1
num_training_ready_handwired_line_trip_labels = 1
num_training_ready_labels = 3
allowed_for_dynamic_aware_training = false
```

Follow-up validation after the user handwired L02-L04:

```text
L01 validation_passed = true
L02 validation_passed = true
L03 validation_passed = true
L04 validation_passed = true
```

Compact simulation result:

```text
L01 simulation_success = true
L02 simulation_success = false, reason = simulation timeout
L03 simulation_success = false, reason = not run after L02 timeout
L04 simulation_success = false, reason = not run after L02 timeout
```

Label gate remains conservative:

```text
num_handwired_validation_passed = 4
num_training_ready_handwired_line_trip_labels = 1
num_unique_handwired_line_ids = 1
num_training_ready_labels = 3
allowed_for_dynamic_aware_training = false
```

The next manual step is to isolate L02 and check whether `L02_TripCommand`
opens the intended breaker. If the control direction is reversed, try
`Initial value = 1` and `Final value = 0`, then rerun validation and compact
simulation.

Validation:

```text
python -m pytest tests/test_ieee39_multi_handwired_checklist.py tests/test_ieee39_multi_handwired_validation_schema.py tests/test_ieee39_multi_handwired_line_trip_summary.py tests/test_ieee39_handwired_fault_summary_merge.py tests/test_ieee39_multi_handwired_label_gate.py tests/test_ieee39_multi_handwired_docs.py

python scripts/gcn_search/check_pio_gcn_artifacts.py

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

The model remains `phasor_RMS`, not EMT. The handwired breakers remain pilot
breaker-like validation, not engineering-grade protection. `generator_speed_proxy`
is not direct frequency. Dynamic-aware reranker training remains blocked while
`num_training_ready_labels < 10`.

## Round 26: IEEE39 Graphical Dynamic Model Intake

Round 26 pauses dynamic-aware reranker training. The goal is to find and prepare an existing IEEE 39-bus / New England 10-machine graphical Simulink model as the future dynamic-label backend.

Local model search found two candidates:

| candidate | path | MATLAB open check |
| --- | --- | ---: |
| MathWorks IEEE39BusSystem example | `C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx` | yes |
| local user copy | `C:/Users/24186/Desktop/灞变笢椤圭洰/IEEE39BusSystemExample/IEEE39BusSystem.slx` | yes |

Primary selected model:

```text
C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx
```

Outputs:

```text
results/gcn_search/ieee39_graphical_dynamic_model/model_inventory.csv
results/gcn_search/ieee39_graphical_dynamic_model/model_inventory.json
results/gcn_search/ieee39_graphical_dynamic_model/toolbox_check_summary.json
results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv
results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_event_log.csv
results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_signal_summary.csv
results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_preview.csv
results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_schema.json
```

Current status:

- `no_fault_sanity` ran as a model-open sanity check and succeeded.
- The generated wrapper copy is local output under `results/gcn_search/ieee39_graphical_dynamic_model/generated_models/` and is not committed.
- `single_line_trip`, `three_phase_fault_clear`, `ordered_N2_trip`, and `relay_trip_test` are schema rows only in this round.
- No dynamic-aware reranker training was performed.
- The selected model is classified conservatively as `phasor_RMS`; do not call it EMT.
- Protection is not engineering-grade and still needs wrapper wiring.

Validation:

```text
python -m pytest tests/test_ieee39_model_inventory.py tests/test_ieee39_dynamic_label_schema.py tests/test_ieee39_graphical_status_docs.py

python scripts/gcn_search/check_pio_gcn_artifacts.py

git diff -- src/rl_mitigation scripts/rl_mitigation
```

RL mitigation files were not modified. No third-party `.slx`, generated wrapper `.slx`, raw trajectories, or large `.mat` files are intended for commit.

## Round 27: IEEE39 Fault / Breaker / Relay Wrapper Pilot

Round 27 starts real wrapper wiring around the local IEEE39 graphical model. It does not train a dynamic-aware reranker.

Added / updated MATLAB scripts:

```text
matlab/simulink_ieee39/setup_ieee39_dynamic_experiment_wrapper.m
matlab/simulink_ieee39/map_ieee39_lines_and_breakers.m
matlab/simulink_ieee39/add_ieee39_basic_relay_proxy.m
matlab/simulink_ieee39/run_ieee39_fault_test_suite.m
```

Key outputs:

```text
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_build_summary.json
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv
results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_fault_injection_points.csv
results/gcn_search/ieee39_graphical_dynamic_model/protection/ieee39_basic_relay_settings.csv
results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv
results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_relay_trip_log.csv
results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json
```

Current result:

- Existing `Fault (Three-Phase)` block was found.
- Five pilot transmission-line blocks were mapped.
- No explicit breaker block was found automatically.
- Pilot line trips use line-block disabling, not timed breaker-control hardware.
- Basic relay proxy was added as a research-grade threshold proxy, not engineering-grade relay coordination.
- A real no-fault graphical simulation and a pilot disabled-line graphical simulation were verified during development, but the full five-case automated run exceeded the available tool timeout.
- The committed label quality summary remains conservative:

```text
label_quality_status = schema_only
allowed_for_dynamic_aware_training = false
```

Validation:

```text
python -m pytest tests/test_ieee39_line_breaker_mapping.py tests/test_ieee39_fault_test_summary.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_relay_proxy_docs.py
python -m pytest tests/test_ieee39_model_inventory.py tests/test_ieee39_dynamic_label_schema.py tests/test_ieee39_graphical_status_docs.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
git diff -- src/rl_mitigation scripts/rl_mitigation
```

The model remains classified as `phasor_RMS`, not EMT. Generated wrapper `.slx`, raw trajectories, and large `.mat` files are not committed.

## Round 28: IEEE39 Small Real Fault Execution

Round 28 changes the IEEE39 wrapper from dry-run/schema-only output to a small partial physical execution set. It does not train a dynamic-aware reranker.

Added MATLAB helpers:

```text
matlab/simulink_ieee39/configure_ieee39_three_phase_fault_case.m
matlab/simulink_ieee39/configure_ieee39_pilot_line_trip_case.m
matlab/simulink_ieee39/extract_ieee39_signal_summary.m
```

Current compact result:

```text
num_fault_rows = 4
num_physical_executed_rows = 2
num_training_ready_labels = 2
label_quality_status = partial_physical_execution
allowed_for_dynamic_aware_training = false
```

Interpretation:

- `no_fault_sanity` is a real simulation but not a training label.
- `three_phase_fault_clear` is a real simulation using the existing `Fault (Three-Phase)` block.
- `relay_trip_test` is a real simulation using the basic relay proxy, not engineering-grade protection.
- `single_line_trip` is a static topology disable, not a timed breaker, so it is not training-ready.
- Measurement extraction is `partial`; unavailable signals are written as `NaN`, not fixed placeholders.

Validation:

```text
python -m pytest tests/test_ieee39_real_fault_summary_schema.py tests/test_ieee39_signal_extraction_summary.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_real_fault_docs.py
python -m pytest tests/test_ieee39_model_inventory.py tests/test_ieee39_dynamic_label_schema.py tests/test_ieee39_graphical_status_docs.py tests/test_ieee39_line_breaker_mapping.py tests/test_ieee39_fault_test_summary.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_relay_proxy_docs.py

## Round 29 - IEEE39 simlog measurement extraction and line-trip gate

Round 29 focused on extracting real compact measurements from `simlog_IEEE39BusSystem` and checking whether the pilot `single_line_trip` could be upgraded from static topology disable to a timed controlled switch.

Changed files:

- `matlab/simulink_ieee39/inventory_ieee39_simlog_tree.m`
- `matlab/simulink_ieee39/extract_ieee39_signal_summary.m`
- `matlab/simulink_ieee39/configure_ieee39_pilot_line_trip_case.m`
- `matlab/simulink_ieee39/run_ieee39_fault_test_suite.m`
- `src/gcn_search/legacy_rts79/export_ieee39_dynamic_labels.py`
- `docs/ieee39_measurement_extraction_and_timed_trip.md`

Compact MATLAB run:

```matlab
run_ieee39_fault_test_suite( ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx", ...
  "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests", ...
  true, ...
  ["no_fault_sanity", "three_phase_fault_clear", "single_line_trip", "relay_trip_test"], ...
  0.5 ...
)
```

Key result:

- `no_fault_sanity`: `measurement_extraction_status = voltage_speed_angle`, `min_voltage_pu = 0.981209`, `frequency_source = generator_speed_proxy`.
- `three_phase_fault_clear`: `measurement_extraction_status = voltage_speed_angle`, `min_voltage_pu = 0.532828`, `frequency_source = generator_speed_proxy`.
- `single_line_trip`: still `trip_implementation = static_topology_disable`; not timed breaker, not training-ready.
- `num_training_ready_labels = 2`
- `num_labels_with_voltage_measurement = 4`
- `num_labels_with_frequency_measurement = 4`
- `num_labels_with_speed_measurement = 4`
- `num_labels_with_rotor_angle_measurement = 4`
- `measurement_quality_status = partial_dynamic_measurements`
- `label_quality_status = partial_physical_execution`
- `allowed_for_dynamic_aware_training = false`

Important boundary:

- Frequency is a generator-speed proxy, not a direct frequency measurement.
- The model is `phasor_RMS`, not EMT.
- The basic relay proxy is not engineering-grade protection.
- Dynamic-aware reranker training remains blocked because there are fewer than ten training-ready labels.

Validation commands:

```bash
python -m pytest tests/test_ieee39_simlog_inventory.py tests/test_ieee39_measurement_quality_gate.py tests/test_ieee39_timed_trip_summary.py tests/test_ieee39_measurement_docs.py
python -m pytest tests/test_ieee39_model_inventory.py tests/test_ieee39_dynamic_label_schema.py tests/test_ieee39_graphical_status_docs.py tests/test_ieee39_line_breaker_mapping.py tests/test_ieee39_fault_test_summary.py tests/test_ieee39_dynamic_label_quality_gate.py tests/test_ieee39_relay_proxy_docs.py tests/test_ieee39_real_fault_summary_schema.py tests/test_ieee39_signal_extraction_summary.py tests/test_ieee39_training_ready_label_gate.py tests/test_ieee39_real_fault_docs.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
git diff -- src/rl_mitigation scripts/rl_mitigation
```
python scripts/gcn_search/check_pio_gcn_artifacts.py
git diff -- src/rl_mitigation scripts/rl_mitigation
```

The model remains `phasor_RMS`, not EMT. Generated `.slx`, `.slxc`, `slprj`, large `.mat`, and raw trajectories are not committed.

## Round 23: Non-Smoke Dynamic Method Comparison

Round 23 expands the learned path-reranker diagnosis from the minimal smoke dataset to a medium non-smoke dataset. This remains a simplified swing-equation preliminary diagnostic, not a formal dynamic stability conclusion.

Dataset:

```text
dataset_source = simulator_derived_medium
dataset_scale = medium
num_samples = 8000
num_critical = 471
positive_ratio = 0.058875
train/val/test seeds = 10/3/3
max_paths_per_seed = 500
```

Learned reranker held-out metrics:

```text
test_auc = 0.7907
test_average_precision = 0.1340
test_precision_at_20 = 0.1500
test_recall_at_20 = 0.0370
```

Dynamic method comparison:

| method | Top50 precision | Top100 precision | Top50 mean stress | Top100 mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_mlp | 0.0000 | 0.0000 | 0.1034 | 0.1040 |
| pio_gcn | 0.0000 | 0.0000 | 0.1034 | 0.1040 |
| lodf | 0.0000 | 0.0000 | 0.0856 | 0.0949 |

The non-smoke Top50/Top100 comparison is still all stable, so `calibration_warning = true` and `dynamic_discrimination_signal = false`.

Rank-depth curve: learned and PIO-GCN are identical in this run; learned does not concentrate dynamic stress earlier than PIO-GCN or LODF.

OPA/dynamic alignment: OPA load-shed label and dynamic stress correlation remains weak. Learned Top100 `corr(stress, OPA shed) = -0.0829`; LODF Top100 `corr(stress, OPA shed) = -0.0288`.

Updated gate:

```text
allowed_next_step = tune_post_fault_event_strength
```

No dynamic recall is reported because no full dynamic truth exists. Generated `.pkl`, `.slx`, `.mat`, full per-path ranking, full dataset CSVs, input paths, event logs, and raw dynamic results remain local ignored artifacts and are not intended for commit.

Validation to run for this round:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py tests/test_post_fault_sanity_ladder.py tests/test_dynamic_interpretability_gate.py tests/test_negative_control_v3_summary.py tests/test_dynamic_method_comparison_cases.py tests/test_dynamic_method_comparison_analysis.py tests/test_dynamic_rank_depth_curve.py tests/test_non_smoke_path_reranker_dataset.py tests/test_non_smoke_dynamic_method_comparison.py tests/test_non_smoke_label_dynamic_alignment.py

python scripts/gcn_search/check_pio_gcn_artifacts.py

git diff -- src/rl_mitigation scripts/rl_mitigation
```

## Round 22: Top50/Top100 Dynamic Method Comparison

Round 22 expands the event-driven dynamic diagnostic after the Round 21 post-fault sanity ladder passed. The comparison covers learned MLP reranker, PIO-GCN, and LODF Top50/Top100 inputs. This remains a simplified swing-equation preliminary diagnostic, not a formal dynamic stability conclusion.

Commands:

```powershell
python src/gcn_search/legacy_rts79/prepare_dynamic_method_comparison_topk.py --input-csv results/gcn_search/simulink_dynamic_real_per_path_ranking/learned_mlp_per_path_ranking.csv --output-dir results/gcn_search/simulink_dynamic_method_comparison_inputs_top100 --top-k 100

python src/gcn_search/legacy_rts79/export_dynamic_method_comparison_cases.py --input-root results/gcn_search/simulink_dynamic_method_comparison_inputs_top100 --output-root results/gcn_search/simulink_dynamic_method_comparison_cases --top-k 50 100 --event-1-time 1.0 --event-2-time 5.0 --simulation-end-time 10.0
```

MATLAB:

```matlab
run_dynamic_method_comparison_batch( ...
  "../../results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_cases", ...
  "../../results/gcn_search/simulink_dynamic_method_comparison_results", ...
  "../../results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json", ...
  100 ...
)
```

Dynamic method comparison summary:

| method | top_k | dynamic precision | mean stress |
| --- | ---: | ---: | ---: |
| learned_mlp | 50 | 0.0000 | 0.0936 |
| learned_mlp | 100 | 0.0000 | 0.0881 |
| pio_gcn | 50 | 0.0000 | 0.0823 |
| pio_gcn | 100 | 0.0000 | 0.1013 |
| lodf | 50 | 0.0000 | 0.0912 |
| lodf | 100 | 0.0000 | 0.1007 |

Interpretation:

```text
calibration_warning = true
dynamic_discrimination_signal = false
allowed_next_step = expand_non_smoke_dataset
```

All Top100 methods are dynamically stable under the recommended post-fault options. This removes the all-unstable degeneracy but creates an all-stable calibration warning. The rank-depth curve does not show learned concentrating higher dynamic stress earlier than PIO-GCN or LODF. No dynamic recall is reported because no full dynamic truth exists.

Validation:

```text
python -m pytest tests/test_simulink_dynamic_case_export.py tests/test_simulink_dynamic_result_analysis.py tests/test_simulink_dynamic_disagreement.py tests/test_simulink_real_topk_preparation.py tests/test_relay_vs_security_logic.py tests/test_event_driven_dynamic_loop.py tests/test_real_topk_dynamic_pipeline.py tests/test_dynamic_method_comparison_inputs.py tests/test_export_path_reranker_per_path_ranking.py tests/test_real_topk_dynamic_validation_pipeline.py tests/test_real_topk_dynamic_summary.py tests/test_path_reranker_minimal_pipeline.py tests/test_real_topk_dynamic_smoke_summary.py tests/test_dynamic_smoke_degeneracy.py tests/test_default_vs_calibrated_dynamic_smoke.py tests/test_dynamic_instability_reasons.py tests/test_dynamic_stress_score.py tests/test_dynamic_negative_controls.py tests/test_swing_equilibrium_diagnostics.py tests/test_dynamic_threshold_sensitivity.py tests/test_negative_controls_v2_summary.py tests/test_post_fault_sanity_ladder.py tests/test_dynamic_interpretability_gate.py tests/test_negative_control_v3_summary.py tests/test_dynamic_method_comparison_cases.py tests/test_dynamic_method_comparison_analysis.py tests/test_dynamic_rank_depth_curve.py
48 passed

python scripts/gcn_search/check_pio_gcn_artifacts.py
PASS: GCN Simulink dynamic validation artifacts are review-ready.

git diff -- src/rl_mitigation scripts/rl_mitigation
empty
```

RL mitigation files were not modified. Generated `.slx`, `.mat`, full per-case dynamic results, raw event logs, and full per-path ranking artifacts remain local ignored artifacts and are not intended for commit.

## Round 37: Clean L09/L10 validation and remaining IEEE39 lab preparation

This round validated the user-handwired per-line clean breaker labs for `L09`
and `L10`, merged the successful compact results into the formal IEEE39 fault
summary, refreshed the dynamic label gate, and prepared local clean lab `.slx`
models for the remaining mapped lines `L11-L34`.

L09/L10 validation and simulation:

- `L09`: `validation_passed = true`, `simulation_success = true`,
  `breaker_opened = true`, `training_ready_candidate = true`,
  `measurement_extraction_status = voltage_speed_angle`
- `L10`: `validation_passed = true`, `simulation_success = true`,
  `breaker_opened = true`, `training_ready_candidate = true`,
  `measurement_extraction_status = voltage_speed_angle`
- Batch validation summary:
  `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.csv`
- Batch compact simulation summary:
  `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_line_trip_summary.csv`
- Latest formal fault summary:
  `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10.csv`

Updated dynamic label gate:

- `num_training_ready_labels = 35`
- `num_training_ready_handwired_line_trip_labels = 33`
- `num_unique_handwired_line_ids = 33`
- `allowed_for_dynamic_aware_training = true`
- `ready_for_preview_training = true`

Full line map and remaining lab preparation:

- Full map:
  `results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv`
- Newly mapped line IDs: `L11-L34`
- Remaining prepare summary:
  `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_remaining_prepare_summary.csv`
- The `L11-L34` clean lab `.slx` files were generated locally only. They are
  prepared-but-unwired: no breaker was auto-inserted and no Simscape physical
  wiring was modified.

Boundaries:

- No dynamic-aware reranker retraining in this round.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker remains pilot breaker-like validation, not
  engineering-grade protection.
- `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, and full timeseries are
  not intended for commit.
- RL mitigation files were not modified.
## Round 38: Batch validation of remaining clean labs L11-L34

This round validated the user-wired remaining per-line clean breaker labs
`L11-L34`. Structure validation passed for all 24 lines. Compact isolated
simulation succeeded for `L11` and `L13-L34`; `L12` timed out after 240 seconds
and is not training-ready.

Merged into formal summary:

- `L11`
- `L13-L34`

Not merged:

- `L12`: simulation timeout

Latest formal fault summary:

- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10_l11_to_l34.csv`

Latest merge summary:

- `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l11_to_l34_merge_summary.json`

Latest label gate:

- `num_training_ready_labels = 35`
- `num_training_ready_handwired_line_trip_labels = 33`
- `num_unique_handwired_line_ids = 33`
- `allowed_for_dynamic_aware_training = true`
- `ready_for_preview_training = true`

No dynamic-aware reranker training was run. The previous preview training remains
a workflow sanity check only, not a final dynamic performance conclusion.

Boundaries:

- No automatic breaker insertion.
- No Simscape physical wiring modification.
- No `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries are
  intended for commit.
- phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- handwired breaker is pilot breaker-like validation, not engineering-grade
  protection.
- These are single-line dynamic labels, not simultaneous or sequential
  multi-line trip experiments.

## Round 39: L12 Islanding / Timeout Diagnosis

This round handles `L12` separately and does not force it into the standard
training-ready single-line label set.

Diagnosis command:

```text
python scripts/gcn_search/diagnose_ieee39_l12_islanding_case.py
```

Key result:

- `L12` line block path:
  `IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B19 to B16`
- structure validation passed: `validation_passed = true`
- compact simulation status: `measurement_extraction_status = simulation_timeout`
- `training_ready_candidate = false`
- `should_merge_as_training_ready = false`
- `should_retrain_reranker = false`
- suspected islanding: opening `B19-B16` leaves the B19-side simplified
  component as `B19`

Outputs:

- `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_l12_islanding_diagnosis.json`
- `results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_l12_islanding_diagnosis.md`
- `docs/ieee39_l12_islanding_timeout_case.md`

The L12 timeout is not a verified stable or unstable dynamic conclusion. It is
a suspected islanding / timeout special case. The formal label gate remains
`35 / 33 / 33`, and no dynamic-aware reranker retraining was run. The model
remains `phasor_RMS`, not EMT; `generator_speed_proxy` is not direct frequency;
the handwired breaker remains pilot breaker-like validation, not
engineering-grade protection; and `.slx`, `.slxc`, `slprj`, `.mat`, raw
trajectories, and full timeseries are not committed.

## Round 40: Expanded-label dynamic-aware preview rerun

This round reruns the preview dynamic-aware reranker with the expanded IEEE39
compact dynamic label set. It does not modify L12, `.slx` files, Simscape
physical wiring, or RL mitigation.

Input summary:

- formal fault summary:
  `results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10_l11_to_l34.csv`
- training-ready labels: `35`
- handwired line-trip labels: `33`
- L12 excluded: `simulation_timeout / suspected islanding`

Expanded preview output:

- `results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_dataset.csv`
- `results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_predictions.csv`
- `results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_comparison.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_comparison.md`

Key metrics:

```text
num_samples = 35
cv_strategy = leave_one_out
random_seed = 42
regression_mae = 0.022533
regression_rmse = 0.030822
regression_spearman = 0.576371
classification_accuracy = 1.000000
classification_f1 = 1.000000
classification_roc_auc = 1.000000
```

The result is preview-only and may be optimistic because `dynamic_stress_score`
is derived from compact dynamic measurements and some input features also come
from compact dynamic measurements. The model remains `phasor_RMS`, not EMT;
`generator_speed_proxy` is not direct frequency; and the handwired breaker is
pilot breaker-like validation, not engineering-grade protection.

## Round 41: Stricter dynamic-aware leakage comparison

This round does not run Simulink, does not modify `.slx`, does not fix L12, and
does not modify Simscape physical wiring. It only reuses the existing 35-sample
expanded compact label dataset to compare feature leakage levels.

Output:

- `results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_dataset.csv`
- `results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_metrics.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_predictions.csv`
- `results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_summary.md`
- `results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_leakage_notes.md`

Main finding:

```text
best leaky RMSE = 0.030455
best no-leakage RMSE = 0.107855
gap = 0.077400
```

This gap shows that removing compact dynamic measurement features makes the task
harder. That is expected and important because `dynamic_stress_score` is a
synthetic proxy target derived from compact dynamic measurements. The result is
still preview-only and not a final dynamic performance conclusion. L12 remains
excluded because it is `simulation_timeout / suspected islanding`.

## Round 42: IEEE39 Non-Line-Trip Fault Expansion Preparation

This round prepares additional IEEE39 dynamic fault types without running
Simulink and without modifying any `.slx` file. It is a feasibility audit and
scenario-manifest step only.

Generated artifacts:

- `scripts/gcn_search/prepare_ieee39_non_line_trip_fault_expansion.py`
- `docs/ieee39_non_line_trip_fault_type_expansion.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_fault_taxonomy.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_fault_taxonomy.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_scenario_manifest.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_scenario_manifest.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_feasibility_report.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_feasibility_report.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_dry_run_commands.txt`

Capability audit:

- Existing `three_phase_fault_clear` can be run by the current fault-test suite.
- Existing `Fault (Three-Phase)` timing can be configured with
  `fault_start_s` and `fault_clear_s`.
- Existing `relay_trip_test` can be used as a basic relay proxy case.
- Different-bus three-phase faults, load-step disturbances, generator-trip /
  mechanical-power-step events, and bus-voltage-reference events are marked as
  manual/future work until a safe injection point is verified.

Recommended first smoke-test candidates:

- `NF01`
- `NF02`
- `NF03`
- `NF04`
- `NF06`

Boundaries:

- This round did not run Simulink.
- No `.slx` was modified.
- No Simscape physical wiring was modified.
- L12 was not fixed and remains excluded.
- No dynamic-aware reranker retraining was run.
- Training-ready label counts remain unchanged.
- These preparation rows are not new training-ready labels.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- Handwired breaker validation remains pilot breaker-like, not
  engineering-grade protection.
- RL mitigation files were not modified.

## Round 43: IEEE39 Non-Line-Trip Fault Smoke Tests

This round ran a small Simulink smoke test for selected non-line-trip scenarios:

- `NF01`: existing three-phase fault-clear baseline
- `NF02`: fault duration sweep, 0.05 s
- `NF03`: fault duration sweep, 0.08 s
- `NF04`: fault duration sweep, 0.10 s
- `NF06`: basic relay proxy

Result:

- `scenario_ids_successful = NF01, NF02, NF03, NF04, NF06`
- `scenario_ids_failed = none`
- `scenario_ids_timeout = none`
- `num_successful_smoke_candidates = 5`

Outputs:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_summary.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_report.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/ieee39_non_line_trip_smoke_test_report.md`
- `docs/ieee39_non_line_trip_fault_smoke_tests.md`

Boundaries:

- Only small Simulink smoke tests were run.
- No `.slx` was modified or committed.
- No Simscape physical wiring was modified.
- L12 was not fixed and remains excluded.
- The formal label gate remains `35 / 33 / 33`.
- No dynamic-aware reranker retraining was run.
- Smoke candidates are not yet formal training-ready dynamic labels.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The relay proxy is not engineering-grade protection.
- RL mitigation files were not modified.

## Round 44: IEEE39 Non-Line-Trip Candidate Label Export

This round did not run Simulink, did not modify `.slx`, did not fix L12, and did
not retrain the dynamic-aware reranker. It only exports the successful
non-line-trip smoke rows as a separate candidate label set and builds a v2
combined candidate schema.

Outputs:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_non_line_trip_dynamic_label_candidates.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_label_schema_v2_combined_candidates.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_label_quality_summary_v2_with_non_line_trip_candidates.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_dynamic_aware_training_readiness_v2_with_non_line_trip_candidates.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export/ieee39_non_line_trip_duplicate_provenance_report.md`
- `docs/ieee39_non_line_trip_label_export.md`

Counts:

- original formal gate remains `35 / 33 / 33`
- non-line-trip candidate labels = `5`
- v2 combined candidate rows = `40`

Duplicate/provenance warning:

- `NF01`, `NF04`, and `NF06` have identical compact measurements.
- `NF01` and `NF04` are both existing three-phase fault block `0.10 s` cases.
- `NF06` is retained but marked `provenance_check_required = true` because the
  relay proxy measurements match the same group.

The v2 set is ready for a future preview training run, but this export round
does not train. The model remains `phasor_RMS`, not EMT;
`generator_speed_proxy` is not direct frequency; and relay proxy is not
engineering-grade protection. RL mitigation files were not modified.

## Round 45: IEEE39 Dynamic-Aware v2 Preview Training

This round did not run Simulink, did not modify `.slx`, did not fix L12, did
not modify Simscape physical wiring, and did not overwrite the old formal gate.
It trains only lightweight preview Ridge / LogisticRegression models on the v2
candidate schema and records duplicate/provenance sensitivity.

Outputs:

- `scripts/gcn_search/train_ieee39_dynamic_aware_reranker_v2_preview.py`
- `scripts/gcn_search/compare_ieee39_dynamic_aware_v2_preview_runs.py`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/include_all_candidates/`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/exclude_provenance_required/`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/v2_preview_comparison.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview/v2_preview_comparison.md`
- `docs/ieee39_dynamic_aware_reranker_v2_preview_training.md`

Counts:

- old formal gate remains `35 / 33 / 33`
- `include_all_candidates`: `40` rows and includes `NF06`
- `exclude_provenance_required`: `39` rows and excludes `NF06`
- both versions exclude L12
- provenance-excluded count = `1`

Preview metrics:

```text
include_all leave_one_out RMSE = 0.028367
include_all label_family_holdout RMSE = 0.142731
exclude_provenance leave_one_out RMSE = 0.028697
exclude_provenance label_family_holdout RMSE = 0.142087
rmse_exclude_minus_include = 0.000330
```

The label-family holdout is the key generalization smoke check because it trains
on `existing_formal_dynamic` and tests on `non_line_trip`. Its error is much
larger than leave-one-out error, so this remains a preview-only sensitivity
check, not a final dynamic performance conclusion. Classification holdout is
skipped because the non-line-trip test fold contains only one `unstable_flag`
class.

`NF01`, `NF04`, and `NF06` remain duplicate/provenance warning rows. `NF06` is
excluded in the sensitivity check. The model remains `phasor_RMS`, not EMT;
`generator_speed_proxy` is not direct frequency; and the relay proxy is not
engineering-grade protection. RL mitigation files were not modified.

## Round 46: IEEE39 Independent Bus-Fault Smoke Feasibility

This round is the first step toward truly independent non-line-trip fault types. It focuses on different-bus three-phase fault smoke candidates, not load steps, not generator trips, and not the full GCN pipeline.

Generated artifacts:

- `scripts/gcn_search/audit_ieee39_bus_fault_injection_points.py`
- `scripts/gcn_search/run_ieee39_bus_fault_smoke_tests.py`
- `docs/ieee39_bus_fault_smoke_tests.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_injection_feasibility.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_injection_feasibility.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_scenario_manifest.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_scenario_manifest.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_test_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/ieee39_bus_fault_smoke_test_report.json`

Result:

```text
scenario_ids_requested = BF01, BF02, BF03, BF04
scenario_ids_runnable = none
scenario_ids_successful = none
scenario_ids_failed = BF01, BF02, BF03, BF04
scenario_ids_timeout = none
```

The audit found that the current scripts can configure timing on the existing `Fault (Three-Phase)` block, but do not expose a safe target-bus selector for B16, B39, B21, or B26. Therefore the runner did not force a Simulink execution. No source `.slx` was modified or committed. L12 remains excluded.

The old formal gate remains `35 / 33 / 33`, the v2 candidate count remains `40`, no labels were exported, no GCN was trained, and the reranker was not retrained. The model remains `phasor_RMS`, not EMT; `generator_speed_proxy` is not direct frequency; relay proxy / handwired breaker is not engineering-grade protection. RL mitigation files were not modified.

## Round 47: IEEE39 Bus-Fault Temporary Lab Injection

This round prepares a temporary-lab injection workflow for different-bus
three-phase faults. It prioritizes `B39` and uses `B26` as the fallback target.
The goal is to find a safe physical bus injection point on an ignored local copy
before any smoke simulation is allowed.

Generated artifacts:

- `scripts/gcn_search/prepare_ieee39_bus_fault_temp_lab.py`
- `scripts/gcn_search/run_ieee39_bus_fault_temp_lab_smoke.py`
- `matlab/simulink_ieee39/prepare_ieee39_bus_fault_temp_lab_copy.m`
- `docs/ieee39_bus_fault_temp_lab_injection.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B39_plan.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/matlab_bus_fault_injection_inventory_B39.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B26_plan.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/matlab_bus_fault_injection_inventory_B26.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_feasibility_summary.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.json`

Result:

```text
B39 injection_point_found = false
B39 safe_to_run_smoke = false
B26 injection_point_found = false
B26 safe_to_run_smoke = false
B39 smoke_executed = false
smoke_not_run_reason = safe_to_run_smoke=false; refusing execution
```

The MATLAB helper loaded and updated only the temporary local copies, then
closed them without saving. It inventoried nearby target-bus candidate blocks
but did not add or wire a three-phase fault block.

Boundaries:

- No source `.slx` was modified or committed.
- No temporary `.slx` was committed.
- No full Simulink smoke simulation was executed.
- L12 was not touched or fixed.
- No labels were exported.
- No GCN was trained.
- The dynamic-aware reranker was not retrained.
- The old formal gate remains `35 / 33 / 33`.
- The v2 candidate count remains `40`.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- Relay proxy / handwired breaker behavior is not engineering-grade protection.
- RL mitigation files were not modified.

Next step: manually identify a safe physical bus injection point for B39 or
B26. If a later temporary lab smoke succeeds, export bus-fault candidate labels
in a separate round; otherwise continue injection-point work and do not train.

## Round 48: IEEE39 Bus-Fault GUI Manual Checklist

This round adds only human GUI review material for B39/B26 bus-fault injection.
It does not run Simulink, does not modify `.slx`, does not commit temporary
`.slx`, does not fix L12, does not train GCN, does not retrain the reranker, and
does not export labels.

Generated artifacts:

- `docs/ieee39_bus_fault_gui_manual_checklist.md`
- `scripts/gcn_search/collect_ieee39_bus_fault_manual_review.py`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B39.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B39.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B26.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B26.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary.md`

Initial default consolidation result before B39 human evidence:

```text
target_bus = B39
recommendation = do_not_run_smoke
human_verified_injection_point = false
safe_to_run_smoke_recommendation = false
```

B39/B26 were still not smoke success at that point. The old formal gate
remained `35 / 33 / 33`, the v2 candidate count remained `40`, the model
remained phasor_RMS, not EMT, `generator_speed_proxy` was not direct frequency,
and relay proxy / handwired breaker behavior was not engineering-grade
protection. RL mitigation files were not modified.

## Round 49: IEEE39 B39 Manual Bus-Fault Injection Review

This round records human Simulink GUI review evidence for the temporary B39
bus-fault injection point. It does not run Simulink smoke, does not run a full
simulation, does not modify source `.slx`, does not commit temporary `.slx`,
does not fix L12, does not export labels, does not train GCN, and does not
retrain the dynamic-aware reranker.

Manual evidence:

- B39 block path:
  `IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B39_TEMP_LOCAL_ONLY/Grid/Bus39`
- `BlockType = SimscapeBlock`
- `MaskType = Busbar`
- Bus39 original connections remain present: `B9 to B39`, `Gen1 BusLabel`,
  `B39 to B1`, and `Load39 BusLabel`.
- The old `Fault (Three-Phase)` remains near `Bus16_1 / B16 to B17` and is not
  treated as the B39 fault.
- `Grid/Fault_B39_TEMP` is manually connected in parallel at Bus39 Port 1 /
  `B9 to B39`.
- Update Diagram passed without error.
- `Fault_B39_TEMP` uses `R_pn_fault = 1e-3 Ohm`, `R_ng_fault = 1e-3 Ohm`,
  `fault_start_time = 0.5 s`, and `fault_duration = 0.08 s`.

Updated artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B39.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary.json`
- `docs/ieee39_bus_fault_b39_manual_review_result.md`

Consolidation result:

```text
human_verified_injection_point = true
safe_to_run_smoke_recommendation = true
recommendation = manual_review_supports_next_round_inventory_update
simulink_run = false
labels_exported = false
gcn_trained = false
reranker_retrained = false
```

B39 is human verified but is not smoke success. B26 remains unverified. The old
formal gate remains `35 / 33 / 33`, the v2 candidate count remains `40`, the
model remains phasor_RMS, not EMT, `generator_speed_proxy` is not direct
frequency, and relay proxy / handwired breaker / temporary bus fault injection
behavior is not engineering-grade protection. RL mitigation files were not
modified.

## Round 50: IEEE39 B39 Temporary Smoke Readiness Gate

This round updates only the B39 readiness / inventory artifacts after the
human-verified manual review. It does not run Simulink smoke, does not run a
full simulation, does not submit `.slx`, does not modify the source `.slx`,
does not export labels, does not train GCN, and does not retrain the reranker.

New readiness artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.md`
- `docs/ieee39_b39_temp_smoke_readiness.md`

Dry-run readiness command:

```bash
python scripts/gcn_search/run_ieee39_bus_fault_temp_lab_smoke.py --temp-lab-plan results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B39_plan.json --manual-review-summary results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary.json --human-readiness-json results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.json --target-bus B39 --timeout-seconds 240 --simulation-stop-time 0.8 --output-dir results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs --dry-run
```

Dry-run output:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_dry_run_readiness.md`

Dry-run result:

```text
target_bus = B39
readiness_status = ready_for_next_round_temp_smoke
would_run_smoke_next_round = true
actual_simulink_run = false
smoke_success = false
labels_exported = false
gcn_trained = false
reranker_retrained = false
formal_label_gate = 35 / 33 / 33
v2_candidate_count = 40
```

B39 can enter the next separate actual temporary smoke round. B39 is still not
smoke success. B26 remains unverified. `phasor_RMS` is not EMT,
`generator_speed_proxy` is not direct frequency, and the temporary bus-fault
injection is not engineering-grade protection.

## Round 51: IEEE39 B39 Temporary Bus-Fault Smoke

This round runs one actual B39 temporary smoke from the ignored local temporary
copy only:

`results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B39_TEMP_LOCAL_ONLY.slx`

Command:

```bash
python scripts/gcn_search/run_ieee39_bus_fault_temp_lab_smoke.py --temp-lab-plan results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B39_plan.json --manual-review-summary results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary.json --human-readiness-json results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b39_human_verified_readiness.json --target-bus B39 --timeout-seconds 240 --simulation-stop-time 0.8 --output-dir results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs
```

Result:

```text
scenario_id = BF_B39_TEMP_SMOKE
simulation_success = true
physical_fault_or_breaker_action_executed = true
measurement_extraction_status = voltage_speed_angle
training_ready_candidate_smoke = true
min_voltage_pu = 0.000160777190390721
max_voltage_pu = 1.0635
min_frequency_hz = 49.7327386072042
max_frequency_hz = 50.1408910900975
max_speed_deviation = 0.00534522785591696
max_rotor_angle_separation_deg = 73.905967084859
unstable_flag = true
signal_source_summary = voltage=generator_terminal_voltage_pu;speed=generator_rotor_velocity_pu;frequency=generator_speed_proxy;rotor_angle=generator_rotor_electrical_angle
```

Artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_bus_fault_temp_lab_smoke_report.md`
- `docs/ieee39_b39_temporary_bus_fault_smoke.md`

Boundaries: no `.slx` was submitted, the source `.slx` was not modified, L12
was not touched, labels were not exported, GCN was not trained, the reranker was
not retrained, the old formal gate remains `35 / 33 / 33`, and the v2 candidate
count remains `40`. This is a temporary smoke candidate only, not a final
dynamic performance conclusion. `phasor_RMS` is not EMT,
`generator_speed_proxy` is not direct frequency, and the temporary bus-fault
injection is not engineering-grade protection.

## Round 52: IEEE39 B39 Temporary Smoke Quality Review

This round reviews the previous B39 temporary smoke result. It does not run
Simulink, does not submit `.slx`, does not modify the source `.slx`, does not
touch L12, does not export labels, does not train GCN, and does not retrain the
reranker.

Quality review result:

```text
target_bus = B39
scenario_id = BF_B39_TEMP_SMOKE
simulation_success = true
measurement_extraction_status = voltage_speed_angle
signal_source_has_frequency_proxy = true
min_voltage_near_zero = true
unstable_flag = true
dynamic_measurement_available = true
quality_review_passed_for_candidate_export = true
labels_exported = false
gcn_trained = false
reranker_retrained = false
old_formal_gate = 35 / 33 / 33
v2_candidate_count = 40
```

The near-zero minimum voltage is expected for a close-in three-phase B39
bus-fault candidate and still needs separate export review. The unstable flag is
plausible for severe B39 temporary smoke, but it is not a final generalized
stability conclusion. `phasor_RMS` is not EMT, `generator_speed_proxy` is not
direct frequency, and the temporary bus-fault injection is not
engineering-grade protection.

Artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_quality_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b39_temp_smoke_quality_review.md`
- `docs/ieee39_b39_temp_smoke_quality_review.md`

Recommended next step: export the B39 bus-fault candidate label in a separate
round, without training.

## Round 53: IEEE39 B39 Candidate Label Export

This round exports the quality-reviewed B39 temporary bus-fault smoke result as
one separate candidate label. It does not run Simulink, does not submit `.slx`,
does not modify source `.slx`, does not touch L12, does not train GCN, does not
retrain the dynamic-aware reranker, and does not update the old v2 preview
training results.

Result:

```text
scenario_id = BF_B39_TEMP_SMOKE
target_bus = B39
fault_type = three_phase_bus_fault_temp_smoke
line_id = NO_LINE
simulation_success = true
measurement_extraction_status = voltage_speed_angle
signal_source_summary includes frequency=generator_speed_proxy
training_ready_label_candidate = true
formal_line_trip_label = false
handwired_line_trip_label = false
non_line_trip_label = true
bus_fault_label = true
candidate_not_formal_label = true
```

Counts and boundaries:

```text
previous_v2_candidate_count = 40
num_v2_plus_b39_candidate_labels = 41
old_formal_gate = 35 / 33 / 33
l12_excluded = true
nf06_provenance_warning_preserved = true
gcn_trained = false
reranker_retrained = false
should_train_now = false
```

Artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_b39_bus_fault_dynamic_label_candidate.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_b39_bus_fault_dynamic_label_candidate.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_dynamic_label_schema_v2_plus_b39_candidate.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_dynamic_label_quality_summary_v2_plus_b39_candidate.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_dynamic_aware_training_readiness_v2_plus_b39_candidate.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/ieee39_b39_candidate_duplicate_provenance_report.md`
- `docs/ieee39_b39_bus_fault_candidate_label_export.md`

Interpretation: B39 is a temporary local-lab smoke candidate only. `phasor_RMS`
is not EMT, `generator_speed_proxy` is not direct frequency, and the temporary
bus-fault injection is not engineering-grade protection. The next step should
be a no-training composition/comparison review, not immediate training.

## Round 54: IEEE39 v2-plus-B39 Schema Fix and No-Training Composition Review

This round fixes the B39 candidate label schema and performs a no-training
composition/comparison review. It does not run Simulink, does not submit `.slx`,
does not modify source `.slx`, does not touch L12, does not train GCN, does not
retrain the dynamic-aware reranker, and does not update the old formal gate or
existing v2 preview training results.

Schema fix:

```text
B39 target_bus = B39
B39 target_bus_or_component = B39
B39 line_id = NO_LINE
B39 fault_type = three_phase_bus_fault_temp_smoke
B39 bus_fault_label = true
B39 candidate_not_formal_label = true
B39 formal_line_trip_label = false
B39 handwired_line_trip_label = false
B39 non_line_trip_label = true
```

No-training review result:

```text
previous_v2_candidate_count = 40
v2_plus_b39_candidate_count = 41
old_formal_gate = 35 / 33 / 33
L12 excluded = true
NF06 provenance warning preserved = true
B39 exact duplicate = false
B39 provenance risk = false
b39_schema_consistency_passed = true
count_consistency_passed = true
export_boundary_passed = true
should_train_now = false
```

Artifacts:

- `docs/ieee39_v2_plus_b39_no_training_composition_review.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_composition_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_composition_review.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_label_family_counts.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_fault_type_counts.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_bus_fault_comparison.csv`

Interpretation: B39 remains a candidate label, not a formal label. `phasor_RMS`
is not EMT, `generator_speed_proxy` is not direct frequency, and the temporary
bus-fault injection is not engineering-grade protection. A later separate
v2-plus-B39 preview training round may be considered, but it must include
label-family holdout and no-leakage comparison.

## Round 55: IEEE39 v2-plus-B39 Dynamic-Aware Reranker Preview Training

This round runs v2-plus-B39 dynamic-aware reranker preview training. It does not
run Simulink, does not submit `.slx`, does not modify source `.slx`, does not
train GCN, and does not change the old formal gate. It is preview-only and not
a final performance conclusion.

Dataset:

```text
previous_v2_candidate_count = 40
v2_plus_b39_candidate_count = 41
B39 candidate count = 1
old_formal_gate = 35 / 33 / 33
L12 excluded = true
NF06 provenance warning preserved = true
```

Preview metrics:

```text
include_all_41_candidates RMSE = 0.043432, F1 = 1.0
exclude_provenance_required RMSE = 0.044357, F1 = 1.0
no_dynamic_measurement_features RMSE = 0.061018, F1 = 1.0
label_family_holdout RMSE = 0.179264, classification skipped because test predictions contain one unstable_flag class
bus_fault_holdout B39 true dynamic_stress_score = 0.605781
bus_fault_holdout B39 predicted dynamic_stress_score = 0.394178
bus_fault_holdout B39 absolute error = 0.211603
bus_fault_holdout B39 predicted unstable probability = 0.966723
```

Interpretation: include-all metrics are not final performance because the proxy
target is derived from compact dynamic measurements that can also appear as
features. The no-dynamic-measurement result is worse, confirming leakage risk.
The B39 holdout is a one-sample bus-fault sanity check only; it cannot represent
all bus faults. `phasor_RMS` is not EMT, `generator_speed_proxy` is not direct
frequency, and the temporary bus-fault injection is not engineering-grade
protection.

Artifacts:

- `docs/ieee39_v2_plus_b39_preview_training.md`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/v2_plus_b39_preview_comparison.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview/v2_plus_b39_preview_comparison.md`

## Round 56: B39 Preview Interpretation and B26 Manual Verification Prep

This round does not run Simulink, does not submit `.slx`, does not modify source
`.slx`, does not train GCN, does not retrain the reranker, and does not export
labels. It interprets the B39 holdout result and prepares the B26 manual GUI
verification workflow.

Interpretation:

```text
include_all_41 RMSE = 0.043432407857356255
no_dynamic_measurement_features RMSE = 0.06101753319040434
label_family_holdout RMSE = 0.17926382339205915
B39 holdout true dynamic_stress_score = 0.6057813745060507
B39 holdout predicted dynamic_stress_score = 0.3941782648518122
B39 holdout absolute error = 0.2116031096542385
B39 holdout unstable probability = 0.9667234869320884
```

The no-dynamic-measurement result is worse, so leakage risk remains. The B39
holdout underestimates dynamic_stress_score, so bus-fault / fault-family
generalization is still weak. The next priority is another independent
bus-fault sample: `B26`.

B26 status:

```text
B26 verified = false
B26 smoke success = false
B26 candidate label exported = false
human_verified_injection_point = false
safe_to_run_smoke_recommendation = false
old formal gate = 35 / 33 / 33
v2-plus-B39 count = 41
```

Artifacts:

- `docs/ieee39_v2_plus_b39_preview_interpretation.md`
- `docs/ieee39_b26_manual_bus_fault_verification_plan.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_gui_check_commands.md`

The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.

## Round 66: All-Remaining Bus-Fault Manual Connection Evidence

This round collected and consolidated manual connection evidence for the 37
remaining IEEE39 bus-fault temporary local copies after the user declared manual
GUI wiring complete. It used load/get_param/Update Diagram checks only. It did
not run Simulink simulation, did not run actual smoke, did not export labels,
did not train GCN, did not retrain the reranker, and did not run a GCN
usefulness audit.

Plain wording: each short-path temporary model was opened for structural
inspection. The expected `Grid/Fault_<BUS>_TEMP` block was found, its
connectivity was readable, and Update Diagram completed successfully for all 37
targets. This means the batch is ready for a separate readiness dry-run round,
not direct smoke.

```text
total_targets = 37
num_temp_models_found = 37
num_fault_blocks_found = 37
num_update_diagram_success = 37
num_automated_evidence_check_passed = 37
num_human_verified_injection_point = 37
num_safe_to_run_smoke_recommendation = 37
buses_ready_for_next_round_readiness = 37
buses_blocked = 0
B16 special check passed = true
B16 old fault not moved = true
current candidate count = 42
old formal gate = 35 / 33 / 33
```

Recommended next step: prepare batch readiness dry-run for all 37 targets in a
separate round. Do not directly jump to smoke, do not export labels, and do not
train GCN.

## Round 58: B26 Manual Bus-Fault Rename Recheck

This round re-collects B26 manual evidence after the user renamed the temporary
fault block to `Grid/Fault_B26_TEMP` in the ignored temporary local copy. It
does not run Simulink smoke, does not submit `.slx`, does not modify source
`.slx`, does not export labels, does not train GCN, and does not retrain the
reranker.

Checked B26 result:

```text
target_bus = B26
Grid/Fault_B26_TEMP found = true
selected_fault_block_path = Grid/Fault_B26_TEMP
selected_injection_block_path = Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node
update_diagram_attempted = true
update_diagram_success = true
human_verified_injection_point = true
safe_to_run_smoke_recommendation = true
B26 smoke success = false
B26 candidate label exported = false
old formal gate = 35 / 33 / 33
v2-plus-B39 count = 41
```

Interpretation: `Grid/Fault_B26_TEMP` is now present and connected in parallel
to the B26 physical node shared by `Grid/B25 to B26`, `Grid/Bus26_1`, and
`Grid/Bus26_2`. The old `Grid/Fault (Three-Phase)` remains near B16. B26 can
proceed to a separate readiness gate in the next round, but it is still not
smoke success and is not a candidate label.

Artifacts:

- `docs/ieee39_b26_manual_bus_fault_review_result.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.md`

## Round 59: B26 Temporary Smoke Readiness Dry-Run

This round updates only the B26 readiness / dry-run readiness artifacts after
the B26 injection point was human verified. It does not run actual Simulink
smoke, does not submit `.slx`, does not modify source `.slx`, does not export
labels, does not train GCN, and does not retrain the reranker.

New readiness artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.md`
- `docs/ieee39_b26_temp_smoke_readiness.md`

Dry-run readiness command:

```bash
python scripts/gcn_search/run_ieee39_bus_fault_temp_lab_smoke.py --temp-lab-plan results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B26_plan.json --manual-review-summary results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.json --human-readiness-json results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.json --target-bus B26 --timeout-seconds 240 --simulation-stop-time 0.8 --output-dir results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs --dry-run
```

Dry-run readiness outputs:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_dry_run_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_dry_run_readiness.md`

Key result:

```text
target_bus = B26
dry_run = true
actual_simulink_run = false
readiness_status = ready_for_next_round_temp_smoke
would_run_smoke_next_round = true
selected_fault_block_path = Grid/Fault_B26_TEMP
selected_injection_block_path = Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node
B26 smoke success = false
B26 candidate label exported = false
```

The old formal gate remains `35 / 33 / 33`; the v2-plus-B39 count remains `41`.
B39 remains a candidate label, not a formal label. `phasor_RMS` is not EMT,
`generator_speed_proxy` is not direct frequency, and temporary bus-fault
injection is not engineering-grade protection.

Recommended next step: run actual B26 temporary smoke in a separate next round;
still do not export labels or train models until the smoke output is reviewed.

## Round 60: B26 Actual Temporary Bus-Fault Smoke

This round runs one actual B26 temporary bus-fault smoke using only the ignored
temporary local copy. It does not submit `.slx`, does not modify source `.slx`,
does not export labels, does not train GCN, does not retrain the reranker, does
not update the old formal gate, and does not update the v2-plus-B39 count.

Command:

```bash
python scripts/gcn_search/run_ieee39_bus_fault_temp_lab_smoke.py --temp-lab-plan results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_temp_lab_B26_plan.json --manual-review-summary results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.json --human-readiness-json results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/ieee39_bus_fault_b26_human_verified_readiness.json --target-bus B26 --timeout-seconds 240 --simulation-stop-time 0.8 --output-dir results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs
```

New B26-specific smoke outputs:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_report.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_bus_fault_temp_lab_smoke_report.md`
- `docs/ieee39_b26_temporary_bus_fault_smoke.md`

Key result:

```text
target_bus = B26
scenario_id = BF_B26_TEMP_SMOKE
actual_simulink_run = true
dry_run = false
simulation_success = true
physical_fault_or_breaker_action_executed = true
measurement_extraction_status = voltage_speed_angle
training_ready_candidate_smoke = true
min_voltage_pu = 0.525205016184139
max_voltage_pu = 1.0635
min_frequency_hz = 49.9925858325228
max_frequency_hz = 50.4143232407741
max_speed_deviation = 0.00828646481548212
max_rotor_angle_separation_deg = 86.3888369812931
unstable_flag = true
signal_source_summary includes frequency=generator_speed_proxy
```

B26 is still only a temporary smoke candidate, not a formal label. This round
does not export B26 candidate labels. B39 remains `candidate_label_not_formal`.
The old formal gate remains `35 / 33 / 33`; the v2-plus-B39 count remains `41`.
`phasor_RMS` is not EMT, and `generator_speed_proxy` is not direct frequency.

Recommended next step: review B26 smoke output quality before any label export.

The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.

## Round 61: B26 Temporary Smoke Quality Review

This round reviews the B26 temporary bus-fault smoke output that was already
generated in Round 60. It does not run Simulink, does not submit `.slx`, does
not modify source `.slx`, does not export labels, does not train GCN, does not
retrain the reranker, does not update the old formal gate, and does not update
the v2-plus-B39 count.

Plain wording: Round 60 proved that the temporary B26 fault case can run and
produce voltage, speed, and rotor-angle measurements. Round 61 only checks
whether that evidence is complete and conservative enough to support a later
candidate-label export round.

Reviewed B26 result:

```text
target_bus = B26
scenario_id = BF_B26_TEMP_SMOKE
simulation_success = true
physical_fault_or_breaker_action_executed = true
measurement_extraction_status = voltage_speed_angle
training_ready_candidate_smoke = true
signal_source_has_frequency_proxy = true
min_voltage_pu = 0.525205016184139
max_frequency_hz = 50.4143232407741
max_rotor_angle_separation_deg = 86.3888369812931
unstable_flag = true
quality_review_passed_for_candidate_export = true
labels_exported = false
gcn_trained = false
reranker_retrained = false
source_slx_modified = false
temporary_slx_committed = false
```

Interpretation: B26 `min_voltage_pu` is about `0.525`, so it is not near zero
like the B39 close-in severe case, but it is still a clear voltage sag. The
rotor-angle separation is about `86.39` degrees, so the compact phasor_RMS
smoke output shows a strong dynamic disturbance. The `unstable_flag = true`
value is a compact smoke threshold flag, not a final stability conclusion.

New quality-review artifacts:

- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_quality_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs/ieee39_b26_temp_smoke_quality_review.md`
- `docs/ieee39_b26_temp_smoke_quality_review.md`

Boundary status: B26 is still temporary smoke evidence, not a formal label.
B26 candidate label export remains false in this round. B39 remains
`candidate_label_not_formal`. The old formal gate remains `35 / 33 / 33`, and
the v2-plus-B39 count remains `41`. `phasor_RMS` is not EMT,
`generator_speed_proxy` is not direct frequency, and temporary bus-fault
injection is not engineering-grade protection.

Recommended next step: export the B26 bus-fault candidate label in a separate
round, without training. That later export should still include composition
review and no-leakage preview before any model training.

## Round 62: B26 Bus-Fault Candidate Label Export

This round exports only one B26 temporary bus-fault candidate label from the
quality-reviewed B26 smoke result. It does not run Simulink, does not submit
`.slx`, does not modify source `.slx`, does not train GCN, does not retrain the
reranker, does not run a GCN usefulness audit, does not update the old formal
gate, and does not touch L12.

Plain wording: the B26 smoke evidence passed quality review, so this round
places it into a candidate-label table. It is a candidate sample for later
review, not a formal label and not training data used in this round.

```text
scenario_id = BF_B26_TEMP_SMOKE
target_bus = B26
target_bus_or_component = B26
line_id = NO_LINE
fault_type = three_phase_bus_fault_temp_smoke
label_family = non_line_trip
dynamic_stress_score = 0.5314759474846006
unstable_flag = true
candidate_not_formal_label = true
quality_review_passed_for_candidate_export = true
labels_exported_this_round = candidate_only
gcn_trained = false
reranker_retrained = false
should_train_now = false
previous_v2_plus_b39_count = 41
num_new_b26_bus_fault_candidates = 1
num_v2_plus_b39_b26_candidate_labels = 42
old formal gate = 35 / 33 / 33
B39 status = candidate_label_not_formal
L12 excluded = true
NF06 provenance warning preserved = true
```

New artifacts:

- `docs/ieee39_b26_bus_fault_candidate_label_export.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_dynamic_label_candidate.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_dynamic_label_candidate.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_dynamic_label_schema_v2_plus_b39_b26_candidate.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_candidate_export_summary.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_b26_bus_fault_candidate_export_summary.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/ieee39_v2_plus_b39_b26_training_readiness.json`

Boundary status: B26 is a candidate label, not a formal label. B39 is still a
candidate label, not a formal label. The old formal gate remains
`35 / 33 / 33`. `phasor_RMS` is not EMT, `generator_speed_proxy` is not direct
frequency, and temporary bus-fault injection is not engineering-grade
protection.

Recommended next step: run v2-plus-B39+B26 no-training composition review
before any training.

## Round 63: v2-plus-B39+B26 No-Training Composition Review

This round reviews the already exported 42-row v2-plus-B39+B26 candidate table.
It does not run Simulink, does not export new labels, does not train GCN, does
not retrain the reranker, does not run preview training, and does not run a GCN
usefulness audit.

Plain wording: B39 and B26 are now both in the candidate-label table. This
round checks whether the table is internally consistent and whether the leakage
risk is documented before any later model experiment.

```text
review_scope = no_training_composition_comparison
v2_plus_b39_b26_candidate_count = 42
previous_v2_plus_b39_count = 41
num_bus_fault_candidates = 2
bus_fault_targets = B39, B26
b39_candidate_present = true
b26_candidate_present = true
b39_status = candidate_label_not_formal
b26_status = candidate_label_not_formal
bus_fault_target_bus_complete = true
bus_fault_target_bus_or_component_complete = true
bus_fault_line_id_no_line = true
b39_b26_schema_consistency_passed = true
count_consistency_passed = true
export_boundary_passed = true
leakage_risk_reviewed = true
target_feature_leakage_risk_if_used_as_inputs = true
should_train_now = false
old formal gate = 35 / 33 / 33
L12 excluded = true
NF06 provenance warning preserved = true
```

New artifacts:

- `docs/ieee39_v2_plus_b39_b26_no_training_composition_review.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_composition_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_composition_review.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_label_family_counts.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_fault_type_counts.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export/no_training_composition_review/ieee39_v2_plus_b39_b26_bus_fault_comparison.csv`

Leakage note: `min_voltage_pu`, `max_voltage_pu`, `min_frequency_hz`,
`max_frequency_hz`, `max_speed_deviation`, and
`max_rotor_angle_separation_deg` are post-fault compact dynamic measurements.
They can support target construction and quality review, but they create
target-feature leakage risk if used directly as model input features. Any later
preview or audit must include no-dynamic-measurement and no-leakage comparison.

Recommended next step: run v2-plus-B39+B26 preview/no-leakage comparison in a
separate round, still not GCN usefulness audit.

## Round 64: v2-plus-B39+B26 Preview/No-Leakage Comparison

This round runs a preview/no-leakage comparison on the 42-row
v2-plus-B39+B26 candidate table. It does not run Simulink, does not export new
labels, does not train GCN, does not run a GCN usefulness audit, and does not
retrain the formal reranker.

Plain wording: B39 and B26 are both temporary bus-fault candidate labels. This
round uses small Ridge/Logistic preview models to check leakage risk and
holdout difficulty before any later GCN audit.

```text
preview_only = true
final_performance_conclusion = false
simulink_run = false
labels_exported = false
gcn_trained = false
gcn_usefulness_audit_run = false
formal_reranker_retrained = false
old formal gate = 35 / 33 / 33
candidate count = 42
num_bus_fault_candidates = 2
include_all_42 RMSE = 0.046807699921347506
no_dynamic_measurement RMSE = 0.061163642668586794
label_family_holdout RMSE = 0.16895513293724
bus_fault_holdout RMSE = 0.14967340256432293
B39 holdout absolute error = 0.20370360540758992
B26 holdout absolute error = 0.1357737642351028
B39 unstable probability = 0.9913769399660165
B26 unstable probability = 0.9927567600955874
recommended_next_step = collect more bus-fault candidates before GCN usefulness audit
```

Interpretation: include_all_42 is a leaky upper-bound because compact
post-fault dynamic measurements are used as input while also defining the proxy
target. The no_dynamic_measurement and holdout modes are more important. The
holdout errors remain nontrivial, so this round does not directly validate GCN.

New artifacts:

- `docs/ieee39_v2_plus_b39_b26_preview_no_leakage_comparison.md`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/v2_plus_b39_b26_preview_comparison.json`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/v2_plus_b39_b26_preview_comparison.md`
- `results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview/*/preview_training_metrics.json`

B39 and B26 remain candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.

## Round 68: All-Remaining Bus-Fault Batch Smoke Quality Review

This round reviews the output quality of the previous actual-smoke run for 37
IEEE39 bus-fault temporary cases. It does not run Simulink, does not run actual
smoke, does not export labels, does not train GCN, does not retrain the
reranker, and does not run a GCN usefulness audit.

Plain wording: the previous round answered "can these temporary bus-fault cases
run and produce compact measurements?" This round answers "are those already
generated measurements complete enough to enter a later candidate-only export
round?" Passing this review is still not a label export.

```text
quality review scope = smoke_output_quality_only
total smoke reports reviewed = 37
quality review passed = 37
quality review failed = 0
candidate export eligible next round = 37
unstable_flag true count = 36
unstable_flag false buses = B1
B16 quality review passed = true
current candidate count = 42
old formal gate = 35 / 33 / 33
labels_exported = false
candidate_labels_exported = false
gcn_trained = false
reranker_retrained = false
gcn_usefulness_audit_run = false
```

New artifacts:

- `docs/ieee39_all_remaining_bus_fault_batch_smoke_quality_review.md`
- `scripts/gcn_search/review_ieee39_all_remaining_bus_fault_batch_smoke_quality.py`
- `tests/test_ieee39_all_remaining_bus_fault_batch_smoke_quality_review.py`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/batch_smoke_quality_review_summary.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/batch_smoke_quality_review_summary.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/batch_smoke_quality_review_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/buses_eligible_for_candidate_export.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/smoke_quality_review_<BUS>.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_quality_review/smoke_quality_review_<BUS>.md`

B16 special handling remains preserved, and the old B16 fault was not moved.
B39/B26 remain existing candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection. Post-fault
compact dynamic measurements should not be used as primary GCN input features,
otherwise target-feature leakage can occur.

Next step: perform candidate-only export for quality-passed buses in a separate
round, without training GCN and without retraining the reranker.

## Round 69: All-Remaining Bus-Fault Candidate-Only Label Export

This round exports candidate labels for the 37 IEEE39 all-remaining bus-fault
temporary smoke samples that passed batch smoke quality review. It does not run
Simulink, does not run actual smoke, does not train GCN, does not retrain the
reranker, and does not run a GCN usefulness audit.

Plain wording: the previous quality review said "these 37 smoke outputs are
complete enough to be registered later." This round does that registration as
candidate-only labels. It still does not turn them into formal labels, and it
still does not justify training before a no-training composition review.

```text
export_scope = candidate_only
previous candidate count = 42
new all-remaining bus-fault candidates = 37
combined candidate count = 79
total bus-fault candidates = 39
all IEEE39 buses have bus-fault candidate = true
unstable_flag false buses = B1
old formal gate = 35 / 33 / 33
L12 excluded = true
NF06 provenance warning preserved = true
gcn_trained = false
reranker_retrained = false
gcn_usefulness_audit_run = false
```

New artifacts:

- `docs/ieee39_all_remaining_bus_fault_candidate_label_export.md`
- `scripts/gcn_search/export_ieee39_all_remaining_bus_fault_candidate_labels.py`
- `tests/test_ieee39_all_remaining_bus_fault_candidate_label_export.py`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/batch_candidate_label_export_summary.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/batch_candidate_label_export_summary.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/batch_candidate_label_export_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/v2_plus_all_bus_fault_training_readiness.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/all_bus_fault_candidate_coverage_report.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/all_bus_fault_candidate_coverage_report.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/candidate_label_<BUS>.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export/candidate_label_<BUS>.csv`

B1 has `unstable_flag=false`, but it remains exportable because quality pass
does not depend on the compact unstable marker. B39/B26 remain existing
candidate labels, not formal labels. All bus-fault labels remain
`candidate_not_formal_label=true`. The model remains `phasor_RMS`, not EMT.
`generator_speed_proxy` is not direct frequency. Temporary bus-fault injection
is not engineering-grade protection. Post-fault compact dynamic measurements
should not be used as primary GCN input features because target-feature leakage
risk remains.

Next step: run v2-plus-all-bus-fault no-training composition review before any
training. Do not train GCN and do not retrain the reranker yet.

## Round 70: V2 Plus All Bus-Fault No-Training Composition Review

This round reviews the latest 79-row IEEE39 v2-plus-all-bus-fault candidate
dataset. It does not run Simulink, does not run actual smoke, does not export
labels, does not train GCN, does not retrain the reranker, does not run a GCN
usefulness audit, and does not run preview training.

Plain wording: the previous round built the 79-row candidate table. This round
checks whether that table is internally consistent before any model experiment.
It checks row counts, bus-fault coverage, duplicate IDs, schema completeness for
bus-fault rows, leakage risk, and training boundaries.

```text
review_scope = no_training_composition_review
total candidate rows = 79
total bus-fault candidates = 39
all B1-B39 have bus-fault candidate = true
missing bus-fault buses = []
duplicate scenario ids = []
duplicate label ids = []
unstable_flag false buses = B1
old formal gate = 35 / 33 / 33
L12 excluded = true
NF06 provenance warning preserved = true
target-feature leakage risk if compact dynamic measurements are used as inputs = true
gcn_trained = false
reranker_retrained = false
gcn_usefulness_audit_run = false
preview_training_run = false
```

New artifacts:

- `docs/ieee39_v2_plus_all_bus_fault_no_training_composition_review.md`
- `scripts/gcn_search/review_ieee39_v2_plus_all_bus_fault_composition.py`
- `tests/test_ieee39_v2_plus_all_bus_fault_composition_review.py`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/v2_plus_all_bus_fault_composition_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/v2_plus_all_bus_fault_composition_review.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/v2_plus_all_bus_fault_composition_review.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/all_bus_fault_coverage_check.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/schema_and_duplicate_check.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review/leakage_risk_and_training_boundary_check.json`

All bus-fault labels remain `candidate_not_formal_label=true`, not formal
labels. B39/B26 remain existing candidate labels, not formal labels. B1
`unstable_flag=false` is a compact low-risk/stable marker, not a quality
failure. The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is
not direct frequency. Temporary bus-fault injection is not engineering-grade
protection.

Next step: run v2-plus-all-bus-fault preview/no-leakage comparison in a
separate round. Do not train GCN and do not retrain the reranker yet.

## Round 66: All-Remaining Bus-Fault Batch Readiness Dry-Run

This round checks the 37 manually connected IEEE39 bus-fault temporary local
copies at the readiness level only. No simulation was run, this is not actual
smoke, and the round does not export labels, does not train GCN, does not
retrain the reranker, and does not run a GCN usefulness audit.

Plain wording: the user has already wired the fault blocks in the GUI. This
round only asks whether each temporary copy is ready to be used in a later
actual smoke round. It does not turn the 37 new targets into candidate labels
and does not mark them as smoke success.

```text
readiness scope = dry_run_only
total targets = 37
readiness checked = 37
ready for next-round actual smoke = 37
blocked before smoke = 0
current candidate count = 42
old formal gate = 35 / 33 / 33
simulation_run = false
actual_smoke_run = false
labels_exported = false
candidate_labels_exported = false
gcn_trained = false
reranker_retrained = false
gcn_usefulness_audit_run = false
```

B16 special handling is preserved, and the old `Grid/Fault (Three-Phase)` was
not moved. B39/B26 remain existing candidate labels, not formal labels. The
model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.

New artifacts:

- `docs/ieee39_all_remaining_bus_fault_batch_readiness_dry_run.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_readiness_dry_run_summary.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_readiness_dry_run_summary.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_readiness_dry_run_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_actual_smoke_plan_manifest.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/batch_actual_smoke_plan_manifest.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/readiness_dry_run_<BUS>.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/readiness_dry_run/readiness_dry_run_<BUS>.md`

## Round 67: All-Remaining Bus-Fault Batch Actual Smoke

This round ran actual Simulink smoke for the 37 readiness-passed IEEE39
bus-fault temporary local copies. It only ran smoke. It did not export labels,
did not train GCN, did not retrain the reranker, and did not run a GCN
usefulness audit.

Plain wording: this is the first real dynamic smoke run for the 37 remaining
temporary bus faults. All 37 models ran through Simulink and produced compact
voltage, generator-speed-proxy frequency, and rotor-angle measurements. These
results are still temporary smoke evidence only; they are not candidate labels
until a later smoke quality review and label export round.

```text
smoke scope = actual_temporary_smoke_only
total targets = 37
smoke attempted = 37
simulation success = 37
simulation failed = 0
timeout = 0
measurement status = voltage_speed_angle for 37
unstable_flag true count = 36
unstable_flag false count = 1
current candidate count = 42
old formal gate = 35 / 33 / 33
labels_exported = false
candidate_labels_exported = false
gcn_trained = false
reranker_retrained = false
gcn_usefulness_audit_run = false
```

B16 special handling is preserved, and the old B16 fault was not moved. B39/B26
remain existing candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.

New artifacts:

- `docs/ieee39_all_remaining_bus_fault_batch_actual_smoke.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/batch_actual_smoke_summary.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/batch_actual_smoke_summary.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/batch_actual_smoke_summary.csv`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/buses_ready_for_smoke_quality_review.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/batch_smoke_<BUS>_report.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/batch_smoke_<BUS>_report.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs/batch_smoke_<BUS>_summary.csv`

## Round 65: All-Remaining Bus-Fault Manual Wiring Plan

This round prepares a manual GUI wiring batch package for all remaining IEEE39
bus-fault targets. It does not run Simulink, does not run smoke, does not
export labels, does not train GCN, does not run a GCN usefulness audit, and
does not retrain the reranker.

Plain wording: the previous B39+B26 preview/no-leakage comparison showed that
bus-fault holdout is still a small-sample problem. This round therefore moves
to sample collection preparation, not model evaluation. It creates one manual
review template per remaining target bus so the user can wire
`Grid/Fault_<BUS>_TEMP` blocks in independent ignored temporary local copies.

```text
existing completed bus faults = B39, B26
normal targets = B1-B15, B17-B25, B27-B38
special target = B16
excluded targets = B39, B26
total new target count = 37
current candidate count = 42
old formal gate = 35 / 33 / 33
templates generated = 37
should_run_smoke_now = false
should_export_labels_now = false
should_train_now = false
gcn_usefulness_audit_now = false
```

New artifacts:

- `docs/ieee39_all_remaining_bus_fault_manual_wiring_plan.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/ieee39_bus_fault_all_remaining_targets.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/ieee39_bus_fault_all_remaining_targets.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/all_remaining_manual_gui_wiring_commands.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_manual_connection_evidence_schema.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_gate_sequence.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/manual_review_templates/`

B16 is marked as special handling because the old `Grid/Fault (Three-Phase)`
is near B16. The old fault must not be renamed or moved. No new target is human
verified, safe to smoke, smoke success, or candidate-label exported in this
round.

## Round 57: B26 Manual Bus-Fault Review Evidence

This round only records B26 manual GUI review evidence. It does not run
Simulink smoke, does not submit `.slx`, does not modify source `.slx`, does not
export labels, does not train GCN, and does not retrain the reranker.

Checked B26 result:

```text
target_bus = B26
update_diagram_attempted = true
update_diagram_success = true
observed_parallel_fault_block_path = Grid/Fault (Three-Phase)1
expected_fault_block_path = Grid/Fault_B26_TEMP
expected_fault_block_found = false
human_verified_injection_point = false
safe_to_run_smoke_recommendation = false
B26 smoke success = false
B26 candidate label exported = false
old formal gate = 35 / 33 / 33
v2-plus-B39 count = 41
```

Interpretation: the temporary disk copy contains a B26 parallel fault connection
through `Grid/Fault (Three-Phase)1`, and Update Diagram passed. However,
`Grid/Fault_B26_TEMP` was not found, so the explicit B26 manual verification
condition is not satisfied. B26 should not proceed to smoke until the GUI block
name is fixed or confirmed and a separate readiness review is completed.

Artifacts:

- `docs/ieee39_b26_manual_bus_fault_review_result.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_connection_evidence.md`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.json`
- `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_review_consolidation_summary_B26.md`

The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.
## Round 71: IEEE39 v2-plus-all-bus-fault Preview / No-Leakage Comparison

This round ran preview-only lightweight checks on the latest 79-row
`v2_plus_all_bus_fault_candidates` dataset. It did not run Simulink, did not
run actual smoke, did not export labels, did not train GCN, did not retrain
the formal reranker, and did not run a GCN usefulness audit.

Preview metrics:

- `include_all_79_rmse = 0.04779276761418548`
- `no_dynamic_measurement_rmse = 0.0760962611650434`
- `label_family_holdout_rmse = 0.22989473254428716`
- `bus_fault_holdout_rmse = 0.16513213481446426`
- `leave_one_bus_fault_out_rmse = 0.06168389651049481`
- `no_dynamic_measurement_leave_one_bus_fault_out_rmse = 0.08660365983240884`

B1 stayed as `unstable_flag=false` low-risk / stable marker. In the stricter
no-dynamic leave-one-bus-fault-out regression check:

- `b1_true_dynamic_stress_score = 0.19602585950733364`
- `b1_predicted_dynamic_stress_score = 0.3932795323245355`
- `b1_absolute_error = 0.19725367281720185`
- `b1_unstable_probability = 0.8840996130572778`
- `b1_unstable_probability_source = bus_fault_holdout_fallback`

Worst 10 buses by absolute error in the no-dynamic leave-one-bus-fault-out
check:

- `B1, B9, B12, B27, B19, B18, B20, B6, B10, B5`

Interpretation:

- `include_all_79_candidates` is a leaky upper-bound because it includes
  post-fault compact dynamic measurement features.
- `no_dynamic_measurement_features` and
  `no_dynamic_measurement_leave_one_bus_fault_out` are the more important
  no-leakage checks.
- This round cannot directly prove GCN useful or not useful because no GCN
  usefulness audit ran.

Recommended next step:

- `leakage risk confirmed; prepare GCN usefulness audit only with no-leakage features and strict holdouts, not training yet`
## Round 72: IEEE39 GCN Usefulness Audit Plan Preparation

This round only prepared the IEEE39 v2-plus-all-bus-fault GCN usefulness audit
plan.

It did not train GCN.
It did not run the GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.

Plan summary:

- `audit_scope = plan_only`
- `total_candidate_rows = 79`
- `num_total_bus_fault_candidates = 39`
- `all_ieee39_buses_have_bus_fault_candidate = true`
- `include_all_is_forbidden_for_gcn_audit = true`
- `no_dynamic_measurement_features_required = true`
- `old_formal_gate = 35 / 33 / 33`
- `l12_excluded = true`
- `nf06_provenance_warning_preserved = true`
- `unstable_flag_false_buses = ["B1"]`

Required strict holdouts:

- `random_candidate_split_baseline`
- `label_family_holdout`
- `bus_fault_holdout`
- `leave_one_bus_fault_out`
- `no_dynamic_measurement_leave_one_bus_fault_out`
- `existing_vs_new_bus_fault_holdout`
- `nf06_provenance_sensitivity`
- `l12_exclusion_check`

The feature policy explicitly forbids post-fault compact dynamic measurement
features such as `min_voltage_pu`, `max_voltage_pu`, `min_frequency_hz`,
`max_frequency_hz`, `max_speed_deviation`, `max_rotor_angle_separation_deg`,
`measurement_extraction_status`, `unstable_flag`, and
`dynamic_stress_score` from future GCN inputs.

The plan also generated baseline comparison rules, including Ridge Regression,
Logistic Regression, RandomForest or GradientBoosting if available, simple
ranking baseline, topology-only baseline, and target-bus-only baseline.

Recommended next step:

- `run audit dry-run validator before any GCN training`

## Round 73: IEEE39 GCN Usefulness Audit Dry-Run Validator

This round ran the IEEE39 GCN usefulness audit dry-run validator only.

It did not train GCN.
It did not run the formal GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not save any model.

Dry-run validator command:

- `python scripts/gcn_search/run_ieee39_gcn_usefulness_audit_dry_run_validator.py --strict --dry-run`

Dry-run validator summary:

- `validator_scope = dry_run_only`
- `dry_run_validator_passed = true`
- `total_candidate_rows = 79`
- `num_total_bus_fault_candidates = 39`
- `all_ieee39_buses_have_bus_fault_candidate = true`
- `forbidden_features_detected_in_inputs = []`
- `forbidden_features_absent_from_gcn_inputs = true`
- `strict_holdouts_complete = true`
- `baseline_comparison_complete = true`
- `b1_special_tracking_enabled = true`
- `nf06_sensitivity_enabled = true`
- `l12_exclusion_check_enabled = true`
- `old_formal_gate = 35 / 33 / 33`
- `should_run_formal_gcn_audit_now = false`
- `should_train_gcn_now = false`

Proposed no-leakage GCN input columns:

- `fault_type`
- `duration_s`
- `fault_start_s`
- `fault_clear_s`
- `trip_implementation`
- `line_id`
- `target_bus`
- `target_bus_or_component`
- `source_model_type`

Warning checks kept explicit:

- `target_bus / target_bus_or_component` may cause target-bus memorization, so future audit must compare against a target-bus-only baseline.
- `duration_s / fault_start_s / fault_clear_s` are intervention design variables, not free physical state features.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- temporary bus-fault injection is not engineering-grade protection.

Recommended next step:

- `prepare formal GCN usefulness audit execution in a separate round, still with no-leakage features and strict holdouts`

## Round 74: IEEE39 Strict No-Leakage GCN Usefulness Audit Execution

This round runs the strict no-leakage GCN usefulness audit execution.

It is audit-only, not production training.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not modify RL mitigation.

Audit command:

- `python scripts/gcn_search/run_ieee39_strict_no_leakage_gcn_usefulness_audit.py`

Execution summary:

- `audit_scope = formal_gcn_usefulness_audit_execution`
- `audit_only = true`
- `production_model_saved = false`
- `gcn_trained_for_audit = false`
- `gcn_dependency_status = blocked_by_missing_gcn_dependency`
- `total_candidate_rows = 79`
- `num_total_bus_fault_candidates = 39`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_feature_policy_passed = true`
- `strict_holdouts_executed = ["random_candidate_split_baseline", "label_family_holdout", "bus_fault_holdout", "leave_one_bus_fault_out", "no_dynamic_measurement_leave_one_bus_fault_out", "existing_vs_new_bus_fault_holdout"]`
- `baseline_comparison_executed = true`
- `final_engineering_conclusion = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

Dependency blocker:

- `torch_spec_present = true`
- `torch_geometric_spec_present = false`
- `torch_import_ok = false`
- `torch_import_error = [WinError 87] 参数错误。: 'E:bin'`

Core baseline-only audit evidence:

- `bus_fault_holdout` best baseline: `Ridge Regression / Logistic Regression`, `RMSE = 0.12218041951744671`
- `leave_one_bus_fault_out` best baseline: `Ridge Regression / Logistic Regression`, `RMSE = 0.09590813978527941`
- `no_dynamic_measurement_leave_one_bus_fault_out` best baseline: `Ridge Regression / Logistic Regression`, `RMSE = 0.09590813978527941`
- `B1 true_dynamic_stress_score = 0.19602585950733364`
- `B1 ridge_logistic_predicted_dynamic_stress_score = 0.5201847730493291`
- `B1 ridge_logistic_absolute_error = 0.32415891354199544`
- `NF06 include baseline bus_fault_holdout RMSE = 0.12218041951744671`
- `NF06 exclude baseline bus_fault_holdout RMSE = 0.12743229641231885`
- `L12 excluded = true`

Audit-level conclusion:

- `formal GCN audit blocked by missing dependency; baseline-only audit completed`

Recommended next step:

- `repair the local GCN dependency environment and rerun the strict no-leakage audit; still do not deploy and do not retrain the reranker`

## Round 75: IEEE39 GCN Dependency Blocker Diagnosis

This round is dependency diagnosis only.

It did not train GCN.
It did not rerun the formal GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not save any production model.

Plain wording: the previous round already showed that the no-leakage audit
framework itself can run, but the GCN branch is blocked by the local Python
environment. So this round checks the active Python executable, Python prefix,
PATH / DLL search context, `torch` import behavior, `torch_geometric`
availability, and repo dependency declarations. It only explains why the GCN
branch is stuck; it does not make any GCN usefulness conclusion.

Diagnosis summary:

- `diagnosis_scope = dependency_diagnosis_only`
- `source_commit = 6c89098a2f4a127102b16d1ef990ec66e4b9d16c`
- `current_python_executable = E:\Scripts\python.exe`
- `current_sys_prefix = E:`
- `current_sys_base_prefix = E:`
- `current_sys_exec_prefix = E:`
- `torch_spec_present = true`
- `torch_import_ok = false`
- `torch_import_error = [WinError 87] ... 'E:bin'`
- `torch_geometric_spec_present = false`
- `torch_geometric_import_ok = false`
- `likely_winerror87_path_cause = true`
- `gcn_dependency_blocker_still_present = true`
- `dependency_repair_plan_generated = true`
- `should_train_gcn_now = false`
- `should_rerun_formal_gcn_audit_now = false`

Interpretation:

- the new key clue is not just missing `torch_geometric`
- the active Python environment reports bare drive prefixes such as `E:`
- that can make `torch` assemble an illegal DLL path like `E:bin`
- so the first repair target is the active Python / DLL path context, not blind
  reinstallation inside the broken environment

Repo dependency declaration note:

- `requirements.txt` declares `torch`
- the repo does not currently declare `torch-geometric`
- the repo does not currently declare PyG extension packages

Generated diagnosis artifacts:

- `docs/ieee39_gcn_dependency_blocker_diagnosis.md`
- `results/gcn_search/ieee39_gcn_dependency_diagnosis/gcn_dependency_diagnosis_summary.json`
- `results/gcn_search/ieee39_gcn_dependency_diagnosis/gcn_dependency_diagnosis_summary.md`
- `results/gcn_search/ieee39_gcn_dependency_diagnosis/gcn_dependency_diagnosis_summary.csv`
- `results/gcn_search/ieee39_gcn_dependency_diagnosis/python_environment_probe.json`
- `results/gcn_search/ieee39_gcn_dependency_diagnosis/torch_import_probe.json`
- `results/gcn_search/ieee39_gcn_dependency_diagnosis/torch_geometric_import_probe.json`
- `results/gcn_search/ieee39_gcn_dependency_diagnosis/windows_path_dll_probe.json`
- `results/gcn_search/ieee39_gcn_dependency_diagnosis/gcn_dependency_repair_plan.json`

Boundary notes remain unchanged:

- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Round 79: IEEE39 GCN Audit Evidence Gap Diagnosis

This round diagnoses why the previous strict no-leakage GCN audit evidence does
not support GCN usefulness over simpler baselines yet.

It did not train GCN.
It did not rerun the formal audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not save a production model.

Plain wording: the previous round already produced the GCN-vs-baseline numbers.
This round only reads those outputs and explains where the gap appears to come
from.

Diagnosis summary:

- `diagnosis_scope = gcn_audit_evidence_diagnosis`
- `gcn_training_run = false`
- `formal_gcn_audit_rerun = false`
- `simulink_run = false`
- `labels_exported = false`
- `reranker_retrained = false`
- `production_model_saved = false`
- `final_engineering_conclusion = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

GCN-baseline gaps:

- `bus_fault_holdout`: `0.5811123249978067`
- `leave_one_bus_fault_out`: `0.023432265101873434`
- `no_dynamic_measurement_leave_one_bus_fault_out`: `0.023432265101873434`

Main diagnosis:

- B1 is an overconfident stable-marker failure case: true stress `0.1960258595`, GCN prediction `0.5078984499`, probability `1.0`
- NF06 sensitivity reduces GCN RMSE when excluded but does not change the conclusion
- the current dense GCN uses candidate rows as graph nodes
- adjacency is based on categorical equality, not physical bus-branch electrical topology
- no-leakage inputs are mostly tabular categorical encodings
- current priority should be graph / feature construction and sample-size diagnosis, not deployment or reranker retraining

New artifacts:

- `docs/ieee39_gcn_audit_evidence_diagnosis.md`
- `results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/gcn_audit_evidence_diagnosis_summary.json`
- `results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/gcn_vs_baseline_gap_analysis.json`
- `results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/b1_and_classification_diagnosis.json`
- `results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/nf06_sensitivity_diagnosis.json`
- `results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/graph_construction_diagnosis.json`
- `results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/next_gcn_improvement_plan.json`

Boundary notes remain unchanged:

- this is not a final proof against GCN
- do not deploy
- do not retrain the reranker
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Round 78: IEEE39 Strict No-Leakage GCN Audit Rerun After Dependency Repair

This round reruns the IEEE39 strict no-leakage GCN usefulness audit inside the
repaired `.venv-gcn-audit` environment.

It runs audit-only GCN training/evaluation.
It does not run Simulink.
It does not export labels.
It does not retrain the reranker.
It does not run RL mitigation.
It does not save a production model.

Plain wording: the dependency blocker is gone, so the audit can finally compare
the GCN branch against simpler baselines under strict no-leakage holdouts. The
result is still only audit-level evidence, not a deployment decision.

Dependency verification:

- `torch_version = 2.12.0+cpu`
- `torch_geometric_version = 2.8.0`
- `gcn_dependency_status = torch_and_torch_geometric_available`

Execution summary:

- `gcn_trained_for_audit = true`
- `total_candidate_rows = 79`
- `num_total_bus_fault_candidates = 39`
- `forbidden_features_detected_in_inputs = []`
- `final_engineering_conclusion = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

Strict holdout results:

- `bus_fault_holdout`: GCN RMSE `0.7032927445`; best baseline `Ridge Regression / Logistic Regression` RMSE `0.1221804195`
- `leave_one_bus_fault_out`: GCN RMSE `0.1193404049`; best baseline `Ridge Regression / Logistic Regression` RMSE `0.0959081398`
- `no_dynamic_measurement_leave_one_bus_fault_out`: GCN RMSE `0.1193404049`; best baseline `Ridge Regression / Logistic Regression` RMSE `0.0959081398`

Special checks:

- B1 true stress `0.1960258595`, GCN prediction `0.5078984499`, absolute error `0.3118725904`, unstable probability `1.0`
- NF06 included: GCN bus-fault holdout RMSE `0.7032927445`; best baseline RMSE `0.1221804195`; row count `79`
- NF06 excluded: GCN bus-fault holdout RMSE `0.4857115424`; best baseline RMSE `0.1274322964`; row count `78`
- L12 exclusion confirmed: `l12_excluded = true`, `present_l12_entries = []`

Audit-level conclusion:

`audit evidence does not support GCN usefulness over simpler baselines yet`

Validation:

- dependency import probes passed for `torch` and `torch_geometric`
- audit command: `python scripts/gcn_search/run_ieee39_strict_no_leakage_gcn_usefulness_audit.py`
- pytest result: `25 passed`
- artifact self-check result: `PASS: GCN Simulink dynamic validation artifacts are review-ready.`
- `git diff -- src/rl_mitigation scripts/rl_mitigation` remained empty

Boundary notes remain unchanged:

- no Simulink run
- no label export
- no production model saved
- no reranker retraining
- no deployment conclusion
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
- current round does not support any GCN usefulness conclusion

## Round 76: IEEE39 Local GCN Dependency Environment Repair

This round is local dependency environment repair.

It did not train GCN.
It did not run the formal GCN audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not save any production model.

Plain wording: the diagnosis round already showed that the old interpreter was
broken because `sys.prefix` collapsed to bare `E:` and `torch` tried to load
DLLs from illegal `E:bin`. So this round stops using that broken interpreter,
creates a clean repository-local `.venv-gcn-audit`, installs CPU-only `torch`,
installs `torch_geometric`, reruns dependency diagnosis inside the clean
environment, and checks whether the blocker is truly gone.

Repair summary:

- `repair_scope = local_dependency_environment_repair`
- `previous_python_executable = E:\Scripts\python.exe`
- `previous_sys_prefix = E:`
- `new_python_executable = .venv-gcn-audit\Scripts\python.exe`
- `new_sys_prefix = absolute repository-local path`
- `new_python_prefix_is_absolute = true`
- `new_python_prefix_is_not_bare_drive = true`
- `torch_install_attempted = true`
- `torch_import_ok = true`
- `torch_version = 2.12.0+cpu`
- `torch_cuda_version = None`
- `torch_cuda_available = false`
- `torch_geometric_install_attempted = true`
- `torch_geometric_import_ok = true`
- `torch_geometric_version = 2.8.0`
- `dependency_blocker_resolved = true`
- `remaining_blockers = []`
- `should_train_gcn_now = false`
- `should_rerun_formal_gcn_audit_now = false`

New repair artifacts:

- `docs/ieee39_gcn_dependency_repair.md`
- `results/gcn_search/ieee39_gcn_dependency_repair/gcn_dependency_repair_summary.json`
- `results/gcn_search/ieee39_gcn_dependency_repair/venv_creation_report.json`
- `results/gcn_search/ieee39_gcn_dependency_repair/torch_install_verify_report.json`
- `results/gcn_search/ieee39_gcn_dependency_repair/torch_geometric_install_verify_report.json`
- `results/gcn_search/ieee39_gcn_dependency_repair/post_repair_dependency_diagnosis_report.json`

Boundary notes remain unchanged:

- `.venv-gcn-audit` is local only and not committed
- wheel / DLL / site-packages / torch cache / model files are not committed
- this round still does not support any GCN usefulness conclusion
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

Final verification note:

- some Python subprocess tests originally called bare `python`, which could fall
  back to the broken `E:` interpreter
- the repair round updates those test entry points to use `sys.executable`, so
  the subprocess inherits the repaired repository-local environment
- `pytest` result after this fix: `42 passed`
- artifact self-check result: `PASS: GCN Simulink dynamic validation artifacts are review-ready.`
- `git diff -- src/rl_mitigation scripts/rl_mitigation` remained empty

## Round 77: IEEE39 GCN Dependency Repair Consistency Check

This round fixes documentation and metadata consistency after dependency
repair. It does not train GCN, does not rerun the formal strict no-leakage GCN
audit, does not run Simulink, does not export labels, and does not retrain the
reranker.

Plain wording: dependency repair says the local `torch` and `torch_geometric`
imports are fixed. The old formal audit execution summary is still the earlier
baseline-only artifact from before that repair. These are two different facts,
so the execution document must not say that the post-repair formal GCN audit has
already been rerun.

Consistency result:

- `dependency_blocker_resolved = true`
- `formal_audit_rerun_after_repair = false`
- `execution_summary_still_baseline_only = true`
- `execution_doc_matches_execution_summary = true`
- `premature_gcn_conclusion_removed = true`
- `final_engineering_conclusion = false`
- `should_rerun_strict_no_leakage_audit_next = true`
- `should_deploy_model = false`
- `should_retrain_reranker_now = false`

New consistency artifacts:

- `docs/ieee39_gcn_dependency_repair_consistency_check.md`
- `results/gcn_search/ieee39_gcn_dependency_repair_consistency_check/dependency_repair_consistency_check.json`
- `results/gcn_search/ieee39_gcn_dependency_repair_consistency_check/dependency_repair_consistency_check.md`

Boundary notes remain unchanged:

- no GCN usefulness conclusion yet
- next step is rerunning the strict no-leakage audit in a separate round
- do not deploy
- do not retrain the reranker
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Round 80: IEEE39 Paper-Aligned Branch GCN Redesign Dry-Run

This round prepares a paper-aligned branch GCN redesign dry-run based on `Searching for Critical Power System Cascading Failures With Graph Convolutional Network`. It does not train GCN, does not rerun the formal audit, does not run Simulink, does not export labels, does not retrain the reranker, and does not save a production model.

The important correction is methodological. The paper GCN is not a candidate-row graph. In the paper, each original power-system branch or line is one graph node, and two graph nodes are connected when the two original branches share one bus. The output is a branch vulnerability vector: the kth value means whether disconnecting branch k from the current operational state leads to load shedding.

Dry-run artifacts:

- `scripts/gcn_search/prepare_ieee39_paper_aligned_branch_gcn_redesign_dry_run.py`
- `docs/ieee39_paper_aligned_branch_gcn_redesign_dry_run.md`
- `results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_method_mapping_summary.json`
- `results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/ieee39_branch_topology_source_inventory.json`
- `results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/ieee39_branch_as_node_graph_manifest.json`
- `results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_feature_manifest.json`
- `results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_label_plan.json`
- `results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/hybrid_search_policy_plan.json`
- `results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/paper_aligned_branch_gcn_dry_run_validator_summary.json`

Current dry-run result:

- `paper_graph_node_type = branch`
- `paper_graph_edge_rule = shared_endpoint_bus`
- `previous_repo_graph_type = candidate_similarity_graph`
- `proposed_graph_type = branch_as_node_physical_line_graph`
- detected bus list = B1-B39
- detected branch map = L01-L34 from the existing IEEE39 wrapper line map
- `can_build_branch_line_graph = true`
- `can_build_required_paper_features = false`
- `can_build_paper_labels_from_existing_data = false`
- `bus_fault_labels_directly_paper_aligned = false`
- `line_trip_labels_first_priority = true`
- `forbidden_features_detected_in_inputs = []`
- `final_engineering_conclusion = false`

The branch graph can be constructed from the verified wrapper line map, but the paper input features are not fully ready. The missing items are verified pre-fault/current-state branch flow, relay threshold or line limit, and bus load sources. The paper-style branch vulnerability labels are also not ready because the current IEEE39 dynamic labels are scenario-level `dynamic_stress_score` and `unstable_flag`, not a per-state vector over all candidate branches.

This means the next step is still not deployment and not reranker retraining. The next step is to add verified static/prefault flow, limit, and bus-load sources, then build a paper-style branch vulnerability label generator for line-trip labels first. Bus-fault labels should remain a separate extension.

`phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Round 81: IEEE39 Paper-Aligned Branch GCN Redesign Consistency Check

This round fixes documentation consistency after the paper-aligned branch GCN
redesign dry-run. It does not train GCN, does not rerun the formal strict
no-leakage audit, does not run Simulink, does not export labels, does not
retrain the reranker, and does not save a production model.

The strict no-leakage execution summary is a post-repair audit:

- `gcn_trained_for_audit = true`
- `gcn_dependency_available = true`
- `gcn_dependency_status = torch_and_torch_geometric_available`
- `bus_fault_holdout` GCN RMSE = `0.7032927445152551`
- `bus_fault_holdout` best baseline RMSE = `0.12218041951744846`
- audit-level conclusion = current audit evidence does not support GCN usefulness over simpler baselines yet
- `final_engineering_conclusion = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

The stale baseline-only wording was removed from the current execution
document. The paper-aligned dry-run is preserved:

- `can_build_branch_line_graph = true`
- `can_build_required_paper_features = false`
- `can_build_paper_labels_from_existing_data = false`
- `bus_fault_labels_directly_paper_aligned = false`
- `line_trip_labels_first_priority = true`

New consistency artifacts:

- `docs/ieee39_paper_aligned_branch_gcn_redesign_consistency_check.md`
- `results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_consistency_check/paper_aligned_redesign_consistency_check.json`
- `results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_consistency_check/paper_aligned_redesign_consistency_check.md`

Next step remains adding verified pre-fault/current-state branch flow, line
limit or relay threshold, bus load sources, and a branch vulnerability label
generator. This is not deployment and not reranker retraining. `phasor_RMS` is
not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault
injection is not engineering-grade protection.

## Round 82: IEEE39 Paper-Aligned Feature Source Dry-Run

This round inventories verified static/pre-fault/current-state feature sources
needed for the paper-aligned IEEE39 branch GCN input. It does not train GCN,
does not rerun the formal audit, does not run Simulink, does not export labels,
does not retrain the reranker, and does not save a production model.

The original paper input is `X_GCN = L x 4`:

- `x_t`: topology status, meaning whether the current branch is already disconnected.
- `x_p`: relay ratio, meaning `|branch_flow| / relay_threshold`.
- `x_b`: branch flow, meaning current-state branch power flow.
- `x_l`: endpoint load, meaning the larger load at the two endpoint buses.

Dry-run artifacts:

- `scripts/gcn_search/prepare_ieee39_paper_aligned_feature_source_dry_run.py`
- `docs/ieee39_paper_aligned_feature_source_dry_run.md`
- `results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/feature_source_inventory.json`
- `results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/l01_l34_feature_readiness_matrix.json`
- `results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/paper_feature_mapping_plan.json`
- `results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/no_leakage_feature_source_audit.json`
- `results/gcn_search/ieee39_paper_aligned_feature_source_dry_run/feature_source_dry_run_validator_summary.json`

Current dry-run result:

- `dry_run_scope = paper_aligned_feature_source_dry_run`
- `branch_line_graph_ready = true`
- `num_branch_nodes = 34`
- `branch_flow_source_ready = false`
- `line_limit_source_ready = false`
- `relay_threshold_source_ready = false`
- `bus_load_source_ready = false`
- `can_build_required_paper_features = false`
- `can_build_l01_l34_feature_matrix = false`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_feature_source_policy_passed = true`
- `l12_special_case_preserved = true`
- `final_engineering_conclusion = false`
- `should_train_gcn_now = false`
- `should_rerun_formal_audit_now = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

The L01-L34 topology feature can be constructed from the current outaged branch
set and the existing wrapper line map. The remaining paper features are still
blocked because verified current-state branch flow, verified line limit or
relay threshold, and verified current-state endpoint bus load sources are not
ready. Post-fault dynamic measurement cannot replace these inputs.

Recommended next step: add or generate verified current-state PF/OPF branch
flow, line limit, and bus load sources before building the paper-style branch
vulnerability label generator. This is not deployment and not reranker
retraining. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.

## Round 83: IEEE39 Static Operating Point Feature Source Dry-Run

This round prepares a static operating point feature source dry-run for the
paper-aligned IEEE39 branch GCN input. It does not train GCN, does not rerun the
formal audit, does not run Simulink, does not export labels, does not retrain
the reranker, and does not save a production model.

The dry-run found a local standard static case loader, `pypower.case39`, and
ran DC PF only for static/pre-fault operating point feature generation. It did
not use post-fault dynamic measurements.

Artifacts:

- `scripts/gcn_search/prepare_ieee39_static_operating_point_feature_source_dry_run.py`
- `docs/ieee39_static_operating_point_feature_source_dry_run.md`
- `results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/static_case_source_inventory.json`
- `results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/dc_power_flow_generation_plan.json`
- `results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/l01_l34_static_feature_source_matrix.json`
- `results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/relay_threshold_proxy_proposal.json`
- `results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/no_leakage_static_feature_audit.json`
- `results/gcn_search/ieee39_static_operating_point_feature_source_dry_run/static_feature_source_dry_run_validator_summary.json`

Current result:

- `dry_run_scope = ieee39_static_operating_point_feature_source_dry_run`
- `selected_case_source = pypower.case39`
- `selected_case_source_trust_level = standard_installed_case_loader_static_pre_fault`
- `dc_pf_run_this_round = true`
- `branch_flow_source_ready = true`
- `line_limit_source_ready = true`
- `relay_threshold_source_ready = false`
- `relay_threshold_proxy_proposed = true`
- `relay_threshold_proxy_allowed_for_training_now = false`
- `bus_load_source_ready = true`
- `can_build_l01_l34_static_feature_matrix = false`
- `can_build_required_paper_features_without_proxy = false`
- `can_build_required_paper_features_with_documented_proxy = true`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_static_feature_policy_passed = true`
- `l12_special_case_preserved = true`
- `final_engineering_conclusion = false`
- `should_train_gcn_now = false`
- `should_rerun_formal_audit_now = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

Interpretation: the static source blocker is mostly resolved for branch flow,
line limit, and bus load. The remaining blocker is relay threshold provenance:
the current dry-run proposes `beta * RATE_A` using project default
`beta = 1.2`, but the proxy is not allowed for training now. It needs explicit
approval and documentation before moving to paper-style branch vulnerability
label generation.

This is not deployment and not reranker retraining. `phasor_RMS` is not EMT.
`generator_speed_proxy` is not direct frequency. Temporary bus-fault injection
is not engineering-grade protection.

## Round 84: IEEE39 Relay Threshold Proxy Approval

This round approves and records the IEEE39 relay threshold proxy for an
audit-only paper-aligned prototype. It does not train GCN, does not rerun the
formal audit, does not run Simulink, does not export labels, does not retrain
the reranker, and does not save a production model.

Decision: approve `relay_threshold_proxy = beta * RATE_A` only for an
audit-only paper-aligned prototype. `beta = 1.2` is the project default, and
`RATE_A` comes from the `pypower.case39` branch `RATE_A` field. This proxy is
not a real protection setting, not an engineering-grade relay threshold, and
not allowed for production.

Artifacts:

- `scripts/gcn_search/approve_ieee39_relay_threshold_proxy.py`
- `docs/ieee39_relay_threshold_proxy_approval.md`
- `results/gcn_search/ieee39_relay_threshold_proxy_approval/relay_threshold_proxy_approval_summary.json`
- `results/gcn_search/ieee39_relay_threshold_proxy_approval/l01_l34_approved_paper_feature_source_matrix.json`
- `results/gcn_search/ieee39_relay_threshold_proxy_approval/no_leakage_proxy_feature_audit.json`
- `results/gcn_search/ieee39_relay_threshold_proxy_approval/relay_threshold_proxy_limitations.md`

Current result:

- `approval_scope = relay_threshold_proxy_approval`
- `relay_threshold_source_ready = false`
- `relay_threshold_proxy_approved = true`
- `relay_threshold_proxy_allowed_for_audit_only_prototype = true`
- `relay_threshold_proxy_allowed_for_production = false`
- `proxy_formula = beta * RATE_A`
- `beta_value = 1.2`
- `branch_flow_source_ready = true`
- `line_limit_source_ready = true`
- `bus_load_source_ready = true`
- `can_build_required_paper_features_with_approved_proxy = true`
- `can_build_l01_l34_paper_feature_matrix_with_proxy = true`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_policy_passed = true`
- `l12_special_case_preserved = true`
- `final_engineering_conclusion = false`
- `should_train_gcn_now = false`
- `should_rerun_formal_audit_now = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

Interpretation: the L01-L34 paper feature source matrix can now be built with
the approved audit-only proxy, but branch vulnerability labels have not been
generated. Any future GCN audit using this proxy must be marked proxy-based.

This is not deployment and not reranker retraining. It provides no GCN
usefulness conclusion. `phasor_RMS` is not EMT. `generator_speed_proxy` is not
direct frequency. Temporary bus-fault injection is not engineering-grade
protection.

## Round 85: IEEE39 Paper-Style Branch Vulnerability Label Generator Dry-Run

This round prepares the IEEE39 paper-style branch vulnerability label generator
dry-run for line-trip labels. It does not train GCN, does not rerun the formal
audit, does not run Simulink, does not export formal labels, does not retrain
the reranker, and does not save a production model.

The paper label is a state x branch vulnerability vector. In a current
operational state, `y_GCN[k]` means whether disconnecting branch `k` causes
load shedding or a documented proxy critical event. This differs from the
current scenario-level `dynamic_stress_score` / `unstable_flag` artifacts.

Artifacts:

- `scripts/gcn_search/prepare_ieee39_paper_style_branch_vulnerability_label_generator_dry_run.py`
- `docs/ieee39_paper_style_branch_vulnerability_label_generator_dry_run.md`
- `results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/branch_vulnerability_label_semantics.json`
- `results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/state_space_manifest.json`
- `results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/state_branch_label_generation_plan.json`
- `results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/existing_label_reuse_audit.json`
- `results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/no_leakage_label_generator_audit.json`
- `results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/label_generator_blocker_report.json`
- `results/gcn_search/ieee39_paper_style_branch_vulnerability_label_generator_dry_run/branch_vulnerability_label_generator_dry_run_summary.json`

Current result:

- `dry_run_scope = paper_style_branch_vulnerability_label_generator_dry_run`
- `feature_matrix_with_proxy_ready = true`
- `relay_threshold_is_proxy = true`
- `proxy_allowed_for_audit_only_prototype = true`
- `proxy_allowed_for_production = false`
- `label_shape_target = num_states x num_branches`
- `num_states_planned = 35`
- `num_state_branch_pairs_planned = 1156`
- `can_generate_full_state_branch_label_matrix_now = false`
- `can_generate_base_state_single_line_labels_now = false`
- `can_generate_single_outage_next_branch_labels_now = false`
- `bus_fault_labels_directly_paper_aligned = false`
- `line_trip_labels_first_priority = true`
- `l12_special_case_preserved = true`
- `nf06_warning_preserved = true`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_label_generator_policy_passed = true`
- `final_engineering_conclusion = false`
- `should_train_gcn_now = false`
- `should_rerun_formal_audit_now = false`
- `should_export_labels_now = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

Interpretation: the dry-run can plan the label matrix, but it cannot generate
real 0/1 paper labels yet. Unknown, timeout, islanding special, and
not-simulated entries remain null/planned/blocked/excluded. The next step is
to implement a controlled line-trip label generation loop for paper-style
branch vulnerability labels.

This is not deployment and not reranker retraining. It provides no GCN
usefulness conclusion. `beta * RATE_A` is still an audit-only proxy, not a real
protection setting. `phasor_RMS` is not EMT. `generator_speed_proxy` is not
direct frequency. Temporary bus-fault injection is not engineering-grade
protection.

## Round 86: IEEE39 Base-State Branch Vulnerability Label Pilot

This round generates a base-state label pilot only. It does not train GCN, does
not rerun the formal audit, does not run Simulink, does not export formal
labels, does not retrain the reranker, and does not save a production model.

Scope:

- `pilot_scope = base_state_branch_vulnerability_label_pilot`
- `state_id = base_state`
- `prior_outaged_branches = []`
- only `base_state x L01-L34`
- does not generate `single_outage_state x next_branch` labels
- does not use bus-fault labels

Artifacts:

- `scripts/gcn_search/generate_ieee39_base_state_branch_vulnerability_label_pilot.py`
- `docs/ieee39_base_state_branch_vulnerability_label_pilot.md`
- `results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_pilot_summary.json`
- `results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/base_state_branch_vulnerability_label_matrix.json`
- `results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/existing_line_trip_label_reuse_report.json`
- `results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot/no_leakage_base_state_label_pilot_audit.json`

Current result:

- `num_candidate_branches = 34`
- `num_label_slots = 34`
- `num_labels_available = 33`
- `num_labels_unknown = 0`
- `num_labels_excluded = 1`
- `l12_special_case_preserved = true`
- `feature_matrix_with_proxy_ready = true`
- `relay_threshold_is_proxy = true`
- `proxy_allowed_for_audit_only_prototype = true`
- `proxy_allowed_for_production = false`
- `bus_fault_labels_used = false`
- `line_trip_labels_first_priority = true`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_policy_passed = true`
- `pilot_labels_are_formal_training_labels = false`
- `final_engineering_conclusion = false`
- `should_train_gcn_now = false`
- `should_rerun_formal_audit_now = false`
- `should_export_formal_labels_now = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

Interpretation: 33 existing training-ready handwired line-trip dynamic rows can
be reused for the base-state pilot matrix. L12 remains special/excluded because
it is an islanding-timeout case and is not forced to 0 or 1. Unknown or missing
sources remain null by rule; in this base-state pilot, no non-L12 slot is
unknown.

This is not deployment and not reranker retraining. It provides no GCN
usefulness conclusion. `beta * RATE_A` is still an audit-only proxy, not a real
relay setting. Pilot labels are not formal training labels. `phasor_RMS` is not
EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault
injection is not engineering-grade protection. The next step is a controlled
single-outage state label generation loop dry-run.

## Round 87: IEEE39 Single-Outage Label Loop Dry-Run

This round prepares the controlled `single_outage_state x next_branch` label
loop as a dry-run only. It does not train GCN, does not rerun formal audit,
does not run new Simulink, does not export formal labels, does not retrain the
reranker, and does not save a production model.

Plain-language meaning: the base-state pilot only asked what happens when one
line is tripped from the original system. Its 33 available non-L12 labels were
all negative, so it cannot train a useful branch-risk classifier by itself.
This round therefore plans the next controlled task list: after branch `i` is
already outaged, evaluate candidate next branch `k`.

Artifacts:

- `scripts/gcn_search/prepare_ieee39_single_outage_label_loop_dry_run.py`
- `docs/ieee39_single_outage_label_loop_dry_run.md`
- `results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_state_manifest.json`
- `results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_state_branch_label_loop_plan.json`
- `results/gcn_search/ieee39_single_outage_label_loop_dry_run/base_state_label_distribution_review.json`
- `results/gcn_search/ieee39_single_outage_label_loop_dry_run/existing_artifact_reuse_for_single_outage_audit.json`
- `results/gcn_search/ieee39_single_outage_label_loop_dry_run/no_leakage_single_outage_label_loop_audit.json`
- `results/gcn_search/ieee39_single_outage_label_loop_dry_run/single_outage_label_loop_dry_run_summary.json`

Current result:

- `dry_run_scope = single_outage_label_loop_dry_run`
- `base_state_all_available_labels_negative = true`
- `base_state_should_not_be_used_alone_for_training = true`
- `num_single_outage_states_planned = 34`
- `num_state_branch_pairs_planned = 1122`
- `num_pairs_excluded_due_to_same_branch = 34`
- `num_pairs_excluded_due_to_l12_special = 66`
- `num_pairs_planned_for_future_generation = 1056`
- `num_pairs_available_from_existing_artifacts = 0`
- `can_generate_single_outage_labels_now = false`
- `can_export_formal_single_outage_labels_now = false`
- `bus_fault_labels_used = false`
- `line_trip_labels_first_priority = true`
- `l12_special_case_preserved = true`
- `nf06_warning_preserved = true`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_policy_passed = true`
- `final_engineering_conclusion = false`
- `should_train_gcn_now = false`
- `should_rerun_formal_audit_now = false`
- `should_export_formal_labels_now = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

Boundary notes:

- `beta * RATE_A` remains an audit-only proxy, not a real relay setting.
- Bus-fault labels are unused in the branch vulnerability loop.
- L12 stays special/excluded.
- NF06 warning is preserved.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.
- Unknown, timeout, not simulated, or special cases remain null/excluded; no
  0/1 label is fabricated.

Recommended next step: implement a controlled generation runner for selected
single-outage pilot pairs in a separate round.

## Round 88: IEEE39 Selected Single-Outage Pilot Pair Runner Dry-Run

This round prepares a selected single-outage pilot pair generation runner
dry-run. It does not train GCN, does not rerun formal audit, does not run new
Simulink, does not export formal labels, does not retrain the reranker, and
does not save a production model.

Plain-language meaning: the previous loop planned 1056 eligible non-L12
`single_outage_state x next_branch` pairs. This round does not run all 1056
pairs. It selects a small pilot set and writes a future run plan that still
requires manual approval before execution.

Artifacts:

- `scripts/gcn_search/prepare_ieee39_single_outage_pilot_pair_generation_runner_dry_run.py`
- `docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md`
- `results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/pilot_pair_selection_summary.json`
- `results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/selected_single_outage_pilot_pairs.json`
- `results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/future_controlled_generation_run_plan.json`
- `results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/no_leakage_pilot_pair_runner_audit.json`
- `results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/single_outage_pilot_pair_runner_dry_run_summary.json`

Current result:

- `dry_run_scope = single_outage_pilot_pair_runner_dry_run`
- `num_candidate_pairs_available = 1056`
- `num_pilot_pairs_selected = 32`
- `num_high_relay_ratio_pairs = 10`
- `num_shared_bus_neighbor_pairs = 10`
- `num_non_neighbor_control_pairs = 12`
- `label_values_fabricated = false`
- `selected_pairs_label_status = planned`
- `can_execute_future_generation_runner_after_approval = true`
- `bus_fault_labels_used = false`
- `line_trip_labels_first_priority = true`
- `l12_special_case_preserved = true`
- `nf06_warning_preserved = true`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_policy_passed = true`
- `final_engineering_conclusion = false`
- `should_train_gcn_now = false`
- `should_rerun_formal_audit_now = false`
- `should_run_simulink_now = false`
- `should_export_formal_labels_now = false`
- `should_retrain_reranker_now = false`
- `should_deploy_model = false`

Selection strategy: high relay ratio pairs, shared bus neighbor pairs, and
non-neighbor control pairs. `beta * RATE_A` remains an audit-only proxy, not a
real relay setting. Bus-fault labels are not used. L12 remains
special/excluded. NF06 warning is preserved. `phasor_RMS` is not EMT.
`generator_speed_proxy` is not direct frequency. Temporary bus-fault injection
is not engineering-grade protection.

Recommended next step: approve and execute selected single-outage pilot pair
generation in a separate round.

## Round 89: IEEE39 Selected Single-Outage Pilot Pair Execution

This round approves selected 32 single-outage pilot pair execution and writes
audit-level evidence. It does not train GCN, does not rerun formal audit, does
not export formal labels, does not retrain the reranker, and does not save a
production model.

Plain-language meaning: the previous dry-run selected 32
`single_outage_state x next_branch` rows. This round tried to move from a plan
to controlled evidence collection, but the repository currently has no safe
controlled Simulink execution backend for these selected pair rows. Therefore
all rows are recorded as `blocked`, and no 0/1 `pilot_label_value` is
fabricated.

Artifacts:

- `scripts/gcn_search/execute_ieee39_selected_single_outage_pilot_pairs.py`
- `docs/ieee39_selected_single_outage_pilot_pair_execution.md`
- `results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_approval.json`
- `results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_summary.json`
- `results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_results.json`
- `results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_label_distribution.json`
- `results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/no_leakage_selected_pair_execution_audit.json`
- `results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/large_file_and_artifact_safety_check.json`

Current result:

- `execution_scope = selected_single_outage_pilot_pair_execution`
- `selected_pair_count = 32`
- `executed_pair_count = 0`
- `succeeded_pair_count = 0`
- `failed_pair_count = 0`
- `timeout_pair_count = 0`
- `unknown_pair_count = 32`
- `pilot_label_available_count = 0`
- `pilot_positive_count = 0`
- `pilot_negative_count = 0`
- `pilot_unknown_count = 32`
- `pilot_blocked_count = 32`
- `gcn_training_run = false`
- `formal_gcn_audit_rerun = false`
- `simulink_run = false`
- `new_simulink_run = false`
- `formal_labels_exported = false`
- `reranker_retrained = false`
- `bus_fault_labels_used = false`
- `line_trip_labels_first_priority = true`
- `l12_special_case_preserved = true`
- `nf06_warning_preserved = true`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_policy_passed = true`
- `pilot_labels_are_formal_training_labels = false`
- `final_engineering_conclusion = false`

Boundary notes:

- This is not full 1056 generation.
- Raw trajectories, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv,
  wheel, DLL, and model files are not committed.
- Timeout, unknown, blocked, and failed cases are not converted to 0/1.
- `beta * RATE_A` remains an audit-only proxy, not a real relay setting.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- NF06 warning is preserved.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.
- No deployment is claimed.

Blocker: controlled Simulink execution backend is not available in this audit
runner; no pilot labels were generated.

Recommended next step: fix controlled execution environment or run selected
pair execution locally, then rerun evidence collection.

## Round 90: IEEE39 Controlled Execution Backend Diagnosis

This round diagnoses the controlled execution backend blocker. It does not train
GCN, does not rerun formal audit, does not execute selected 32 pairs, does not
run full 1056 generation, does not export formal labels, does not retrain the
reranker, and does not save a production model.

Plain-language meaning: the previous selected pair execution was blocked because
there was no safe callable controlled Simulink execution backend. This round
checks what pieces already exist and what pieces are missing. It does not try to
run the selected pairs.

Artifacts:

- `scripts/gcn_search/diagnose_ieee39_controlled_execution_backend.py`
- `docs/ieee39_controlled_execution_backend_diagnosis.md`
- `results/gcn_search/ieee39_controlled_execution_backend_diagnosis/backend_readiness_summary.json`
- `results/gcn_search/ieee39_controlled_execution_backend_diagnosis/backend_component_inventory.json`
- `results/gcn_search/ieee39_controlled_execution_backend_diagnosis/selected_pair_execution_mapping_diagnosis.json`
- `results/gcn_search/ieee39_controlled_execution_backend_diagnosis/safe_execution_repair_plan.json`
- `results/gcn_search/ieee39_controlled_execution_backend_diagnosis/no_leakage_backend_diagnosis_audit.json`
- `results/gcn_search/ieee39_controlled_execution_backend_diagnosis/large_file_safety_backend_diagnosis.json`

Current diagnosis:

- `diagnosis_scope = controlled_execution_backend_diagnosis`
- `matlab_available = true`
- `simulink_available = unknown`
- `ieee39_wrapper_model_found = true`
- `selected_pair_mapping_found = true`
- `two_step_line_trip_injection_supported = false`
- `batch_runner_found = false`
- `timeout_policy_found = true`
- `result_parser_found = false`
- `evidence_writer_found = true`
- `safe_no_raw_artifact_policy_found = true`
- `can_execute_selected_32_pairs_now = false`
- `can_execute_without_full_1056 = true`
- `graceful_blocked_mode_available = true`

Blocker: selected-pair controlled execution backend is incomplete; the missing
pieces are an approved two-step line-trip sequence injection, a selected-32-only
batch runner, and a selected-pair result parser contract.

Boundary notes:

- This round does not execute selected 32 pairs.
- This round does not run full 1056 generation.
- This round does not commit raw trajectory, full timeseries, `.mat`, `.slx`,
  `.slxc`, `slprj`, venv, wheel, DLL, or model files.
- `beta * RATE_A` remains an audit-only proxy, not a real relay setting.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- NF06 warning is preserved.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.
- No deployment and no GCN usefulness conclusion are claimed.

Recommended next step: add a selected-32-only controlled execution backend or
write local manual execution instructions before rerunning evidence collection.

## Round 91: IEEE39 Controlled Execution Backend Repair Skeleton

This round repairs the controlled execution backend skeleton. It does not train
GCN, does not rerun formal audit, does not execute selected 32 pairs, does not
run full 1056 generation, does not export formal labels, does not retrain the
reranker, and does not save a production model.

Plain-language meaning: the previous diagnosis found that selected-pair branch
mapping exists, but the backend lacked a safe two-step execution path. This
round adds the guarded pieces needed for a future approved run: a selected-32-only
Python runner, a MATLAB two-step line-trip entrypoint skeleton, a compact result
parser contract, an evidence-only writer, and a manual instruction pack.

Artifacts:

- `scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py`
- `matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m`
- `scripts/gcn_search/parse_ieee39_selected_pair_execution_evidence.py`
- `docs/ieee39_controlled_execution_backend_repair.md`
- `results/gcn_search/ieee39_controlled_execution_backend_repair/backend_repair_summary.json`
- `results/gcn_search/ieee39_controlled_execution_backend_repair/backend_execution_contract.json`
- `results/gcn_search/ieee39_controlled_execution_backend_repair/manual_execution_instruction_pack.md`
- `results/gcn_search/ieee39_controlled_execution_backend_repair/selected_pair_backend_readiness_matrix.json`
- `results/gcn_search/ieee39_controlled_execution_backend_repair/no_leakage_backend_repair_audit.json`
- `results/gcn_search/ieee39_controlled_execution_backend_repair/large_file_safety_backend_repair.json`

Current result:

- `repair_scope = controlled_execution_backend_repair`
- `python_runner_added = true`
- `matlab_entrypoint_added = true`
- `result_parser_contract_added = true`
- `evidence_writer_added = true`
- `manual_instruction_pack_added = true`
- `selected_32_only_guard_added = true`
- `full_1056_guard_added = true`
- `no_formal_label_export_guard_added = true`
- `no_training_guard_added = true`
- `no_raw_artifact_policy_added = true`
- `can_execute_selected_32_pairs_after_manual_approval = true`
- `can_execute_selected_32_pairs_now = false`

Boundary notes:

- This round does not execute selected 32 pairs.
- The new runner rejects `--max-pairs > 32`.
- The new runner rejects `--execute` in this repair round.
- The MATLAB entrypoint is a guarded skeleton, not an automatic full-generation
  runner.
- Raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv,
  wheel, DLL, and model files are not committed.
- `beta * RATE_A` remains an audit-only proxy, not a real relay setting.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- NF06 warning is preserved.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.
- No deployment and no GCN usefulness conclusion are claimed.

Recommended next step: approve execution of selected 32 pairs using the repaired
backend in a separate round.

## Round 92: IEEE39 Selected 32 Pair Controlled Execution Evidence

This round uses the repaired backend after manual approval to collect compact
evidence for only the selected 32 single-outage pilot pairs. It does not train
GCN, does not rerun formal audit, does not run full 1056 generation, does not
export formal labels, does not retrain the reranker, and does not save a
production model.

Plain-language meaning: this step tried to move from "backend skeleton exists"
to "selected 32 evidence collection". Because the current MATLAB entrypoint is
still a guarded skeleton and not a real automatic Simulink execution backend,
the runner records all 32 pairs as blocked/null evidence. It does not fabricate
0/1 labels.

Artifacts:

- `docs/ieee39_selected_32_pair_controlled_execution_evidence.md`
- `results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_approval.json`
- `results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_summary.json`
- `results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_execution_results.json`
- `results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/selected_32_label_distribution.json`
- `results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/no_leakage_selected_32_execution_audit.json`
- `results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence/large_file_safety_selected_32_execution.json`

Current result:

- `execution_scope = selected_32_controlled_execution_evidence`
- `selected_pair_count = 32`
- `executed_pair_count = 0`
- `succeeded_pair_count = 0`
- `failed_pair_count = 0`
- `timeout_pair_count = 0`
- `blocked_pair_count = 32`
- `pilot_label_available_count = 0`
- `pilot_positive_count = 0`
- `pilot_negative_count = 0`
- `pilot_unknown_count = 32`
- `has_positive_pilot_label = false`

Boundary notes:

- Only selected 32 pairs are in scope.
- Full 1056 generation is not approved and was not run.
- Formal label export is not approved and was not run.
- GCN training and reranker retraining were not run.
- Timeout, failed, blocked, and unknown cases remain null and are not converted
  to 0/1.
- Raw trajectories, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv,
  wheel, DLL, and model files are not committed.
- `beta * RATE_A` remains an audit-only proxy, not a real relay setting.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- NF06 warning is preserved.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.
- No deployment and no GCN usefulness conclusion are claimed.

Recommended next step: inspect the local MATLAB/Simulink execution entrypoint
and repair it before rerunning selected 32 compact evidence collection.

## Round 93: IEEE39 MATLAB Selected-Pair Entrypoint Repair

This round repairs the MATLAB selected-pair execution entrypoint. It does not
train GCN, does not rerun formal audit, does not execute selected 32 pairs, does
not run full 1056 generation, does not export formal labels, does not retrain
the reranker, and does not save a production model.

Plain-language meaning: the previous selected-32 evidence round produced 32
blocked/null rows because the MATLAB entrypoint was still a guarded skeleton.
This round adds a single-pair smoke mode so a future separately approved round
can try at most one selected pair, such as SPP001, without opening the door to
batch 32 or full 1056 execution.

Artifacts:

- `matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m`
- `docs/ieee39_matlab_selected_pair_entrypoint_repair.md`
- `results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/matlab_entrypoint_repair_summary.json`
- `results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/single_pair_smoke_execution_contract.json`
- `results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/entrypoint_component_reuse_report.json`
- `results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/single_pair_smoke_candidate.json`
- `results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/no_leakage_entrypoint_repair_audit.json`
- `results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair/large_file_safety_entrypoint_repair.json`

Current result:

- `repair_scope = matlab_selected_pair_entrypoint_repair`
- `matlab_entrypoint_updated = true`
- `python_runner_updated = true`
- `parser_contract_updated = true`
- `selected_32_guard_preserved = true`
- `single_pair_smoke_mode_added = true`
- `batch_32_execution_allowed_now = false`
- `full_1056_execution_allowed_now = false`
- `can_attempt_single_pair_smoke_after_manual_approval = true`
- `can_attempt_selected_32_after_single_pair_smoke = false`

Boundary notes:

- This round does not execute selected 32 pairs.
- The next round may approve at most one selected pair smoke execution.
- Raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv,
  wheel, DLL, and model files are not committed.
- The source `.slx` is not modified.
- `beta * RATE_A` remains an audit-only proxy, not a real relay setting.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- NF06 warning is preserved.
- Pilot labels are not formal training labels.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.
- No deployment and no GCN usefulness conclusion are claimed.

Recommended next step: approve one selected pair smoke execution in a separate
round.

## Round 94: IEEE39 SPP001 Single-Pair Smoke Execution

This round executes only the manually approved SPP001 smoke path. It does not
train GCN, does not rerun formal audit, does not execute the selected 32 batch,
does not run full 1056 generation, does not export formal labels, does not
retrain the reranker, and does not save a production model.

Plain-language meaning: this is a one-pair channel check for `L15 -> L04`. The
run is allowed to try the repaired MATLAB/Simulink single-pair path, but any
blocked, failed, timeout, or unknown result remains null and is not converted to
a 0/1 training label.

Artifacts:

- `docs/ieee39_spp001_single_pair_smoke_execution.md`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_approval.json`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_summary.json`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_smoke_execution_result.json`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_no_leakage_smoke_audit.json`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_execution/spp001_large_file_safety_check.json`

Current result:

- `execution_scope = spp001_single_pair_smoke_execution`
- `pair_id = SPP001`
- `prior_outaged_branch = L15`
- `candidate_next_branch = L04`
- `execution_attempted = true`
- `execution_status = blocked`
- `pilot_label_value = null`
- `pilot_label_status = blocked`
- `blocker_if_any = single-pair smoke not ready: validation missing for L15; L04 validation passed`

Boundary notes:

- SPP001 is the only approved pair in this round.
- The selected 32 batch is not executed.
- Full 1056 generation is not approved and was not run.
- Formal label export is not approved and was not run.
- GCN training and reranker retraining were not run.
- Pilot labels are not formal training labels.
- Raw trajectories, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv,
  wheel, DLL, and model files are not committed.
- The source `.slx` is not modified.
- Bus-fault labels are not used.
- Line-trip labels remain first priority.
- L12 remains special/excluded.
- This is not a final project conclusion.

Recommended next step: repair the MATLAB/Simulink single-pair readiness path for
L15 in the combined handwired validation evidence, then rerun one-pair smoke
after repair. Do not train yet.

## Round 95: IEEE39 L15 Handwired Validation Readiness Repair

This round repairs the L15 handwired validation readiness path using existing
evidence only. It does not train GCN, does not rerun formal audit, does not run
SPP001 smoke, does not execute selected 32 batch, does not run full 1056
generation, does not export formal labels, does not retrain the reranker, and
does not save a production model.

Plain-language meaning: the previous SPP001 smoke was blocked because the
single-pair runner saw `L15` as missing while `L04` had passed. This round
searched existing line-trip, handwired, and clean breaker artifacts and found
that L15 already has clean-lab handwired validation evidence with a trip command
path. The result is a repaired readiness preview, not a pilot 0/1 label.

Artifacts:

- `scripts/gcn_search/repair_ieee39_l15_handwired_validation_readiness.py`
- `docs/ieee39_l15_handwired_validation_readiness_repair.md`
- `results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/l15_readiness_repair_summary.json`
- `results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/l15_evidence_inventory.json`
- `results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/repaired_combined_validation_preview.csv`
- `results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/spp001_rerun_readiness_gate.json`
- `results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/no_leakage_l15_readiness_repair_audit.json`
- `results/gcn_search/ieee39_l15_handwired_validation_readiness_repair/large_file_safety_l15_readiness_repair.json`

Current result:

- `repair_scope = l15_handwired_validation_readiness_repair`
- `target_line_id = L15`
- `paired_next_line_id = L04`
- `l15_existing_evidence_found = true`
- `l15_trip_command_path_found = true`
- `l15_validation_passed = true`
- `l15_readiness_status = ready`
- `l04_validation_still_passed = true`
- `repaired_combined_validation_written = true`
- `can_rerun_spp001_smoke_after_manual_approval = true`
- `no_label_value_generated = true`

Boundary notes:

- This round only repairs readiness evidence.
- SPP001 smoke was not rerun.
- Selected 32 batch was not executed.
- Full 1056 generation was not run.
- Formal labels were not exported.
- GCN and reranker were not trained.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- Pilot labels are not formal training labels.
- Raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv,
  wheel, DLL, and model files are not committed.
- The source `.slx` is not modified.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.

Recommended next step: approve rerun of SPP001 single-pair smoke in a separate
round. Do not train yet.

## Round 96: IEEE39 SPP001 Single-Pair Smoke Rerun

This round reruns only the manually approved SPP001 pair `L15 -> L04` after the
L15 readiness repair. It does not train GCN, does not rerun formal audit, does
not execute the selected 32 batch, does not run full 1056 generation, does not
export formal labels, does not retrain the reranker, and does not save a
production model.

Plain-language meaning: the previous blocker was that the selected-pair runner
could not see L15 readiness. This round uses the repaired readiness preview, so
both L15 and L04 pass the readiness gate. The one-pair execution then fails at
the model path stage because the L15 trip command still points to the clean-lab
model path, while the execution wrapper loads the handwired breaker model. The
result remains a null pilot label and is not converted into a 0/1 label.

Artifacts:

- `docs/ieee39_spp001_single_pair_smoke_rerun.md`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_rerun_approval.json`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_rerun_summary.json`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_rerun_result.json`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_rerun_label_distribution.json`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_no_leakage_rerun_audit.json`
- `results/gcn_search/ieee39_spp001_single_pair_smoke_rerun/spp001_large_file_safety_rerun.json`

Current result:

- `execution_scope = spp001_single_pair_smoke_rerun`
- `pair_id = SPP001`
- `prior_outaged_branch = L15`
- `candidate_next_branch = L04`
- `l15_ready = true`
- `l04_ready = true`
- `execution_attempted = true`
- `execution_status = failed`
- `single_pair_executed = false`
- `simulink_run = false`
- `pilot_label_value = null`
- `pilot_label_status = failed`
- `blocker_if_any = L15 TripCommand path belongs to the clean-lab L15 model, not the loaded handwired breaker wrapper`

Boundary notes:

- Selected 32 batch was not executed.
- Full 1056 generation was not run.
- Formal labels were not exported.
- GCN and reranker were not trained.
- Pilot labels are not formal training labels.
- Raw trajectories, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv,
  wheel, DLL, and model files are not committed.
- The source `.slx` is not modified.
- Bus-fault labels are not used.
- Line-trip labels remain first priority.
- L12 remains special/excluded.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.

Recommended next step: repair the remaining single-pair execution blocker by
placing L15 and L04 trip command paths in one executable wrapper, or by creating
an approved one-pair model provenance bridge. Do not run broader pair execution,
export labels, train GCN, or retrain the reranker yet.

## Round 97: IEEE39 SPP001 Model Provenance Bridge Repair

This round diagnoses and repairs the SPP001 model provenance bridge evidence
only. It does not train GCN, does not rerun formal audit, does not execute
SPP001 smoke, does not execute selected 32 batch, does not run full 1056
generation, does not export formal labels, does not retrain the reranker, and
does not save a production model.

Plain-language meaning: the previous SPP001 rerun showed that L15 readiness is
available, but the L15 trip command belongs to the clean-lab L15 model while L04
belongs to the handwired breaker wrapper. The same-wrapper check therefore
fails. This round writes a provenance manifest and rerun gate, but it does not
fabricate a trip command path and does not create an SPP001 0/1 label.

Artifacts:

- `scripts/gcn_search/repair_ieee39_spp001_model_provenance_bridge.py`
- `docs/ieee39_spp001_model_provenance_bridge_repair.md`
- `results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/spp001_provenance_bridge_repair_summary.json`
- `results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/spp001_trip_command_provenance_inventory.json`
- `results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/spp001_repaired_provenance_manifest.json`
- `results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/spp001_rerun_provenance_gate.json`
- `results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/no_leakage_spp001_provenance_bridge_audit.json`
- `results/gcn_search/ieee39_spp001_model_provenance_bridge_repair/large_file_safety_spp001_provenance_bridge.json`

Current result:

- `repair_scope = spp001_model_provenance_bridge_repair`
- `pair_id = SPP001`
- `prior_outaged_branch = L15`
- `candidate_next_branch = L04`
- `l15_trip_command_model_source = IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15`
- `l04_trip_command_model_source = IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker`
- `loaded_execution_wrapper_source = results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx`
- `same_wrapper_trip_commands_available = false`
- `repaired_provenance_manifest_written = true`
- `can_rerun_spp001_after_manual_approval = false`
- `no_label_value_generated = true`

Boundary notes:

- SPP001 smoke was not executed.
- Selected 32 batch was not executed.
- Full 1056 generation was not run.
- Formal labels were not exported.
- GCN and reranker were not trained.
- Raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv,
  wheel, DLL, and model files are not committed.
- The source `.slx` is not modified.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- Pilot labels are not formal training labels.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.

Recommended next step: build or validate an SPP001-only same-wrapper bridge
locally before any rerun. Do not execute broader pair smoke, export labels,
train GCN, or retrain the reranker yet.

## Round 98: IEEE39 SPP001 Same-Wrapper Bridge Dry-Run

This round prepares an SPP001-only same-wrapper bridge dry-run for `L15 -> L04`.
It does not train GCN, does not rerun formal audit, does not execute SPP001
smoke, does not execute selected 32 batch, does not run full 1056 generation,
does not export formal labels, does not retrain the reranker, and does not save
a production model.

Plain-language meaning: the previous round proved that the current L15 and L04
TripCommand paths are not in the same wrapper. This round does not build a
bridge `.slx`; it only prepares a guarded local-lab-copy plan, a candidate
manifest, and a readiness gate. If a bridge `.slx` is built later, it must be a
local lab copy and must not be committed.

Artifacts:

- `scripts/gcn_search/prepare_ieee39_spp001_same_wrapper_bridge_dry_run.py`
- `matlab/simulink_ieee39/prepare_ieee39_spp001_same_wrapper_bridge_lab.m`
- `docs/ieee39_spp001_same_wrapper_bridge_dry_run.md`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/spp001_same_wrapper_bridge_dry_run_summary.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/spp001_bridge_component_plan.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/spp001_same_wrapper_candidate_manifest.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/spp001_bridge_readiness_gate.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/no_leakage_spp001_bridge_dry_run_audit.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_dry_run/large_file_safety_spp001_bridge_dry_run.json`

Current result:

- `dry_run_scope = spp001_same_wrapper_bridge_dry_run`
- `pair_id = SPP001`
- `same_wrapper_bridge_planned = true`
- `same_wrapper_bridge_built_this_round = false`
- `local_lab_copy_required = true`
- `local_lab_copy_committed = false`
- `source_slx_modified = false`
- `can_build_same_wrapper_bridge_locally = true`
- `can_confirm_same_wrapper_now = false`
- `can_rerun_spp001_after_manual_approval = false`
- `no_label_value_generated = true`

Boundary notes:

- SPP001 smoke was not executed.
- Selected 32 batch was not executed.
- Full 1056 generation was not run.
- Formal labels were not exported.
- GCN and reranker were not trained.
- Raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv,
  wheel, DLL, and model files are not committed.
- The source `.slx` is not modified.
- Bus-fault labels are not used.
- L12 remains special/excluded.
- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- Temporary bus-fault injection is not engineering-grade protection.

Recommended next step: approve local SPP001 same-wrapper bridge build/validation
in a separate round. Do not run SPP001 smoke yet.

## Round 99: IEEE39 SPP001 Same-Wrapper Bridge Local Validation

This round performed SPP001 same-wrapper bridge local validation only. It does not train GCN, does not rerun formal audit, does not execute SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

Plain-language result: a local bridge `.slx` copy was created for inspection, but only `L04_TripCommand` was found in that copy. `L15_TripCommand` was still not present, so L15 and L04 are not yet validated in the same local wrapper. Therefore this round does not generate a 0/1 label and does not allow an SPP001 smoke rerun yet.

Artifacts:

- `scripts/gcn_search/validate_ieee39_spp001_same_wrapper_bridge_local.py`
- `docs/ieee39_spp001_same_wrapper_bridge_local_validation.md`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_local_validation/spp001_local_bridge_validation_summary.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_local_validation/spp001_local_bridge_build_report.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_local_validation/spp001_validated_same_wrapper_manifest.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_local_validation/spp001_local_bridge_rerun_gate.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_local_validation/no_leakage_spp001_local_bridge_validation_audit.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_local_validation/large_file_safety_spp001_local_bridge_validation.json`

Key fields:

- `validation_scope = spp001_same_wrapper_bridge_local_validation`
- `pair_id = SPP001`
- `local_bridge_build_attempted = true`
- `local_bridge_validation_attempted = true`
- `local_bridge_built = false`
- `local_bridge_committed = false`
- `source_slx_modified = false`
- `l15_trip_command_found_in_bridge = false`
- `l04_trip_command_found_in_bridge = true`
- `same_wrapper_confirmed = false`
- `repaired_provenance_manifest_written = true`
- `can_rerun_spp001_after_manual_approval = false`
- `no_label_value_generated = true`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_policy_passed = true`
- `blocker_if_any = L15_TripCommand is not present in the local bridge copy`

Boundary notes: no raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, production model, venv, wheel, DLL, or local bridge `.slx` file is committed. Bus-fault labels are not used. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

Next step: repair local same-wrapper bridge builder before any SPP001 smoke rerun.

## Round 100: IEEE39 SPP001 Same-Wrapper Bridge Builder Repair

This round repaired the SPP001 same-wrapper bridge builder only. It does not train GCN, does not rerun formal audit, does not execute SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

Plain-language result: the previous local bridge copy was missing `L15_TripCommand`. This round updated the guarded builder so the local bridge copy contains `L15_TripCommand`, `L04_TripCommand`, `L15_HandwiredTimedBreaker`, and `L04_HandwiredTimedBreaker` in the same local wrapper. This only repairs the bridge. It does not generate a 0/1 label and does not run SPP001 smoke.

Artifacts:

- `scripts/gcn_search/repair_ieee39_spp001_same_wrapper_bridge_builder.py`
- `docs/ieee39_spp001_same_wrapper_bridge_builder_repair.md`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/spp001_bridge_builder_repair_summary.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/spp001_bridge_builder_repair_report.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/spp001_repaired_same_wrapper_manifest.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/spp001_bridge_builder_rerun_gate.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/no_leakage_spp001_bridge_builder_repair_audit.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/large_file_safety_spp001_bridge_builder_repair.json`

Key fields:

- `repair_scope = spp001_same_wrapper_bridge_builder_repair`
- `pair_id = SPP001`
- `previous_l15_trip_command_found_in_bridge = false`
- `previous_l04_trip_command_found_in_bridge = true`
- `local_bridge_build_attempted = true`
- `local_bridge_validation_attempted = true`
- `local_bridge_built = true`
- `local_bridge_committed = false`
- `source_slx_modified = false`
- `l15_trip_command_found_in_bridge = true`
- `l04_trip_command_found_in_bridge = true`
- `l15_breaker_found_in_bridge = true`
- `l04_breaker_found_in_bridge = true`
- `same_wrapper_confirmed = true`
- `repaired_provenance_manifest_written = true`
- `can_rerun_spp001_after_manual_approval = true`
- `no_label_value_generated = true`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_policy_passed = true`
- `blocker_if_any = null`

Boundary notes: no raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, production model, venv, wheel, DLL, or local bridge `.slx` file is committed. Bus-fault labels are not used. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

Next step: approve rerun of SPP001 single-pair smoke using repaired same-wrapper bridge in a separate round; do not export labels or train.

## Round 101: IEEE39 SPP001 Same-Wrapper Bridge Smoke Rerun

This round executed only the manually approved SPP001 same-wrapper bridge smoke path `L15 -> L04`. It does not train GCN, does not rerun formal audit, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

Plain-language result: the repaired manifest confirms that L15 and L04 trip commands are in the same local wrapper, so the provenance problem is fixed. The actual Simulink execution did not finish within the controlled Python timeout window, so the compact result is `execution_status = timeout`. This is not a positive or negative label: `pilot_label_value` remains null, and no formal training label is exported.

Artifacts:

- `docs/ieee39_spp001_same_wrapper_bridge_smoke_rerun.md`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_smoke_rerun/spp001_bridge_smoke_rerun_approval.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_smoke_rerun/spp001_bridge_smoke_rerun_summary.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_smoke_rerun/spp001_bridge_smoke_rerun_result.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_smoke_rerun/spp001_bridge_smoke_label_distribution.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_smoke_rerun/no_leakage_spp001_bridge_smoke_audit.json`
- `results/gcn_search/ieee39_spp001_same_wrapper_bridge_smoke_rerun/large_file_safety_spp001_bridge_smoke.json`

Key fields:

- `execution_scope = spp001_same_wrapper_bridge_smoke_rerun`
- `pair_id = SPP001`
- `prior_outaged_branch = L15`
- `candidate_next_branch = L04`
- `planned_contingency_sequence = L15;L04`
- `same_wrapper_confirmed = true`
- `execution_attempted = true`
- `execution_status = timeout`
- `single_pair_executed = false`
- `simulink_run = false`
- `pilot_label_value = null`
- `pilot_label_status = timeout`
- `pilot_labels_are_formal_training_labels = false`
- `selected_32_batch_executed = false`
- `full_1056_generation_run = false`
- `labels_exported = false`
- `formal_labels_exported = false`
- `gcn_training_run = false`
- `formal_gcn_audit_rerun = false`
- `reranker_retrained = false`
- `production_model_saved = false`
- `raw_trajectories_committed = false`
- `full_timeseries_committed = false`
- `mat_files_committed = false`
- `slx_files_committed = false`
- `local_bridge_committed = false`
- `source_slx_modified = false`
- `bus_fault_labels_used = false`
- `forbidden_features_detected_in_inputs = []`
- `no_leakage_policy_passed = true`

Boundary notes: no raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, production model, venv, wheel, DLL, or local bridge `.slx` file is committed. Bus-fault labels are not used. Line-trip labels remain first priority. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

Next step: inspect the SPP001 bridge smoke timeout before any broader selected-pair execution. Do not export formal labels or train GCN from this timeout result.
