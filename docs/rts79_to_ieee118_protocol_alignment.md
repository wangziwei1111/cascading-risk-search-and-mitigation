# RTS-79 to IEEE118 Protocol Alignment

This document audits the original RTS-79 GCN search protocol and records how it is migrated to IEEE118. The goal is not to introduce a new method. The goal is to keep the RTS-79 protocol fixed while changing only the benchmark system, line labels, and thermal limit calibration.

## Audited RTS-79 Files

- `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`
- `src/gcn_search/legacy_rts79/evaluate_rts79_paper_gcn_search.py`
- `src/gcn_search/legacy_rts79/train_rts79_physics_gcn.py`
- `src/gcn_search/legacy_rts79/evaluate_rts79_pio_gcn_topk.py`

## Paper-Style GCN Model

Original model:

- `PaperStyleRts79Gcn`
- located in `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`

Architecture:

- `PaperGraphConvolution`
- `PaperGraphConvolution`
- linear classifier

Training configuration copied for IEEE118:

- `epochs = 20`
- `batch_size = 32`
- `learning_rate = 0.005`
- `k_gcn = 3`
- `first_layer_channels = 16`
- `second_layer_channels = 4`
- `positive_weight = 20.0`
- `validation_fraction = 0.2`
- `random_seed = 20260708` for the IEEE118 run

## Paper-Style Input Features

RTS-79 paper-style GCN uses four branch features:

- `x_t`: branch is open = 1, online = 0
- `x_p`: relay index, `abs(PF) / (beta * RATE_A)`
- `x_b`: absolute branch flow
- `x_l`: larger load of the two terminal buses

IEEE118 protocol alignment uses the same 4 feature fields through:

- `src/gcn_search/ieee118/convert_ieee118_step2_to_rts79_gcn_format.py --feature-mode paper`

The previous 9-feature physics tensor from PR #9 remains useful as an ablation/preparation artifact, but it is not the strict paper-style protocol main result.

## Training Data Structure

RTS-79 does not train one independent graph per ordered path. It trains one state sample per first-line outage:

- one `S1(first_line)` state sample
- GCN outputs a length-`num_lines` probability vector for candidate second outages
- `y_GCN` is a line-label vector
- `loss_mask` excludes the already-open first line

IEEE118 aligned dataset:

- 186 `S1(first_line)` state samples
- 186 line outputs per sample
- valid ordered path labels: `186 * 185 = 34,410`
- critical labels: 1,859
- relay-cascade labels: 1,659

## RTS-79 Path Scoring Formula

The main RTS-79 search score is `GCN_path_prob` in `evaluate_rts79_paper_gcn_search.py`:

```text
score(Li -> Lj) = p_shed(Li | S0) * p_shed(Lj | S1(i))
```

where:

- `p_shed(Li | S0)` is the GCN output on the initial base state
- `p_shed(Lj | S1(i))` is the GCN output after first outage `Li`

IEEE118 main protocol method:

- `RTS79_GCN_path_prob_reused_on_IEEE118`

PR #9's previous second-step-only score is retained only as:

- `RTS79_GCN_second_only_reused_on_IEEE118`

It is an ablation, not the main RTS-79 protocol.

## Search Methods

RTS-79 original evaluation includes:

- `GCN_yP`
- `GCN_filter_yP`
- `GCN_prob`
- `GCN_prob_yP`
- `GCN_path_prob`
- `LODF_yP`
- `line_order`
- `random`
- `oracle`

IEEE118 aligned implementation currently includes:

- `RTS79_GCN_prob_reused_on_IEEE118`
- `RTS79_GCN_prob_yP_reused_on_IEEE118`
- `RTS79_GCN_path_prob_reused_on_IEEE118`
- `RTS79_GCN_second_only_reused_on_IEEE118` as ablation
- `LODF_yP`
- `line_order`
- `random`

Not implemented in this stage:

- `GCN_yP`
- `GCN_filter_yP`
- `oracle`

Reason: this PR focuses on the core path-probability protocol and baseline comparison. `oracle` also requires a separate full-cascade-path oracle ordering decision for IEEE118 and should be added in a dedicated follow-up.

## LODF_yP Ordering

The aligned IEEE118 `LODF_yP` follows the RTS-79 two-layer ranking:

1. rank first-line candidates by `y_P` in `S0`
2. for each first-line candidate, enter `S1(first_line)`
3. rank second-line candidates by `y_P`
4. append ordered paths in that nested order

It is not the product `first_yP * second_yP` in this protocol-aligned evaluation.

## Full-Cascade-Path Detection Curve

RTS-79 search curves count discovered full cascade paths after deduplication, not only whether the initial ordered N-2 path row is critical.

IEEE118 full-truth does not currently store the exact `protection_event_table`. The aligned evaluator constructs an approximate comparable field:

```text
full_cascade_path = first_line -> second_line -> relay_trip_labels
```

If `relay_trip_labels` is empty, it falls back to appending labels from `final_outage_labels`. Duplicate labels are removed while preserving order. This is documented as an approximation, not a perfect RTS-79 event-table reconstruction.

The sparse curve output includes both:

- RTS-79-style full-cascade-path deduplicated count: `found_critical_count_full_cascade_dedup`
- IEEE118 path-level counts: `critical_hit_count_path_level`, `relay_cascade_hit_count_path_level`

Sparse sampling keeps all fixed and percentage budget points, samples every 50 attempts up to 1000, then every 500 attempts afterward.

## Output Directory

Protocol-aligned output directory:

- `results/gcn_search/ieee118_flow_scaled_800_rts79_protocol_eval/`

Committed compact outputs:

- `ieee118_rts79_protocol_search_summary.csv`
- `ieee118_rts79_protocol_search_summary.json`
- `ieee118_rts79_protocol_curve_points_sparse.csv`
- `ieee118_rts79_protocol_topk_paths.csv`
- `ieee118_rts79_protocol_first_step_probabilities.csv`
- `ieee118_rts79_protocol_config.json`
- `ieee118_rts79_protocol_readme.md`

Not committed:

- full predictions CSV
- full `fulltruth_with_full_cascade_path` CSV
- raw full-truth CSV
- 2.7GB Step2-State CSV
- model checkpoint
- Simulink/MATLAB artifacts

## Result Note

In this IEEE118 run, strict `RTS79_GCN_path_prob_reused_on_IEEE118` is much stronger than random, line_order, and two-layer LODF_yP. However, the second-only ablation remains stronger than strict path probability. This means the previous PR #9 result should remain labeled as an ablation, but it also reveals that multiplying by the learned S0 first-outage probability may suppress many high-risk IEEE118 paths. This should be analyzed before making a final paper claim.

## First-Step Critical Early-Stop Audit

The current legacy RTS-79 implementation `run_sequential_initial_outages_dcpf` applies the provided `initial_outage_sequence` in order and does not explicitly stop when the first outage already sheds load. The pre-early-stop IEEE118 generator followed the same legacy behavior: once `S1(first_line)` was computed, it expanded every `second_line` even when the first outage was already critical.

That behavior aligns with the current legacy implementation, but it is biased for the formal ordered N-2 search protocol. The formal rule is:

```text
S0 --Li--> load shed
=> Li is first-step / N-1 critical
=> do not generate Li->Lj as valid ordered N-2 rows

S0 --Li--> no load shed
=> enter S1(i)
=> enumerate valid Lj second outages
```

Therefore PR #10 is a no-early-stop protocol result and should be treated as a historical ablation. It should not be described as the final formal IEEE118 ordered N-2 result.

This PR introduces `--first-step-critical-policy skip|expand` in the IEEE118 full-truth generator:

- `skip` is the formal default. First-step critical lines are written to `ieee118_first_step_summary.csv` and their `Li->Lj` rows are not generated as valid N-2 samples.
- `expand` preserves the historical no-early-stop behavior for reproducing PR #10-style results only.

Early-stop full-truth for `flow_scaled=8.00`, `min_rate_a=1.0`, seed `20260708` gives:

- possible ordered N-2 paths without early stop: 34,410
- first-step critical lines: 10
- skipped ordered N-2 paths: 1,850
- valid ordered N-2 paths: 32,560
- valid critical paths: 1,754
- valid relay-cascade paths: 1,643

The formal paper result should use:

- `RTS79_GCN_path_prob_reused_on_IEEE118_earlystop`

and not the no-early-stop PR #10 method:

- `RTS79_GCN_path_prob_reused_on_IEEE118`

## Paper-Aligned Training Protocol

After first-step critical early-stop, the remaining protocol gap is training data construction. The paper-style GCN learns `y_GCN = f(X_GCN)` across many current operating states. IEEE118 therefore needs both:

- S0 base-state samples for learning `p_shed(Li | S0)`.
- S1 first-outage states for learning `p_shed(Lj | S1(i))`.

Training only on Step2-State S1 samples and then using that model to predict S0 first-line probabilities is protocol-incomplete. The paper-aligned IEEE118 training stage adds S0 + S1 multi-state samples, keeps first-step critical lines as positive S0 labels, and still excludes them from valid ordered N-2 S1 expansion.

The new training stage still uses the original RTS-79 `PaperStyleRts79Gcn`, paper-style 4D features, and seed-separated train/validation/test splits. It does not change Algorithm 1 or any other search ordering logic.

## Paper-Aligned Training Scale-Up

The scale-up stage extends the 12-state PR #13 smoke run without changing the model or search logic. It adds medium calibration, pilot-200, pilot-2000, and optional paper-8000 commands for IEEE118. The main baseline remains the original RTS-79 default `positive_weight=20`; `positive_weight={50,100,200,800}` is reported only as sensitivity.

The search evaluator may be rerun with the scale-up model and its train-split feature normalizer. This is preprocessing compatibility for the original `PaperStyleRts79Gcn`, not a new search algorithm. `path_prob`, `second_only`, Algorithm 1, `LODF_yP`, `PFW`, random, and line order remain evaluation methods/ablations and should not be mixed together as one claimed method.
