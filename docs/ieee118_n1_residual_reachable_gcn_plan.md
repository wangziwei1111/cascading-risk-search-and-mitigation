# IEEE118 N-1 Gate + Residual-Reachable GCN Plan

## 1. Objective

Improve IEEE118 ordered N-2 search efficiency without changing the physical
ground truth or replacing the original RTS-79 GCN. The target is not to force
IEEE118 to reproduce the RTS-79 `50/100` counts. IEEE118 has a much larger
search space, so the primary comparison uses normalized search effort:

- search budget `K / N`;
- searches per critical path `K / C`;
- `K90`, `K95`, `K99`, and `Kall` for critical-path recall;
- relay-cascade recall and captured load shed at the same budgets.

The RTS-79 presentation result is a reference point: about 56.6 critical paths
and 68.2 searches on average, or `K / C ~= 1.205`. For the IEEE118 early-stop
truth (`C = 1,754`), the same normalized effort is approximately 2,113 path
evaluations. This is a comparison target, not a promise that the systems have
identical difficulty.

## 2. Non-Negotiable Guardrails

1. Keep the IEEE118 `flow_scaled=8.00`, `min_rate_a=1.0` early-stop full truth
   unchanged.
2. Do not redefine `critical`, remove difficult positives, or use outcome fields
   as model inputs.
3. Use the original RTS-79 model class:
   `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py::PaperStyleRts79Gcn`.
4. Do not report the PR #7 NumPy/logistic `GCN_smoke` as a GCN result.
5. Model-core layers remain unchanged. IEEE118 work may adapt labels, masks,
   data format, graph radius `k_gcn`, training volume, and evaluation protocol.
6. Keep train/validation/test seeds separate. Seed `20260708` is test/full-truth
   only and must not be used for fitting or model selection.
7. Do not commit raw full-truth CSVs, large training NPZs, full predictions,
   checkpoints, or Step2-State CSVs.

## 3. Confirmed Structural Facts

The early-stop IEEE118 truth contains:

- 32,560 valid ordered N-2 paths;
- 1,754 critical paths;
- 1,643 relay-cascade paths;
- 111 island-only paths.

Ten lines are already critical as an N-1 event:

`L016, L047, L051, L061, L096, L147, L180, L181, L183, L184`.

Using one physical N-1 prescreen of all 186 lines, paths whose second outage is
one of these ten lines form a deterministic high-risk tier:

- 1,760 paths;
- 1,556 critical paths;
- 88.409% tier precision;
- 88.7% of all critical paths captured.

After removing this tier from the learned residual ranking problem:

- 30,800 residual paths remain;
- 198 are critical (0.6429%);
- 154 are relay cascades;
- 44 are island-only;
- 114 first lines can reach a residual critical second outage;
- 62 first lines cannot reach one in this truth table.

The previous S0 target was degenerate because every valid first line had at
least one critical continuation before N-1 masking. The residual-reachable S0
target restores a meaningful binary question.

## 4. Receptive-Field Hypothesis

`PaperStyleRts79Gcn` has two graph-convolution blocks, each aggregating
`A^0 ... A^k`. Its approximate maximum receptive field is therefore `2k` hops.

- RTS-79 line-graph diameter: 6; `k=3` covers all line pairs.
- IEEE118 line-graph diameter: 15.
- IEEE118 line pairs within 6 hops: 58.24%.
- within 10 hops: 93.70%.
- within 12 hops: 99.07%.

Therefore compare `k_gcn = 3, 5, 6, 8` while keeping the original model class
and channel structure. The expected useful range is `k=5` or `k=6`; `k=8` is
included to detect oversmoothing.

## 5. Data and Target Construction

### S1 target

For a state after first outage `f`, retain the original critical label of each
candidate second line except lines already identified as N-1 critical. Those
N-1 lines are masked from the learned residual loss and handled by Tier A.

### S0 target

For candidate first line `f`, label whether its corresponding S1 state has any
positive residual second-line continuation. If the active first outage cannot
be recovered unambiguously from an older pilot artifact, mark the target
unknown and exclude it from loss; never silently assign zero.

### Features

Use only the paper-aligned physical features already consumed by the original
RTS-79 model. Ground-truth outcomes, critical flags, relay outcomes, load shed,
and final-event statistics are forbidden inputs.

## 6. Training Protocol

1. Convert the existing paper-aligned pilot NPZ without rerunning OPA.
2. Preserve seed-based splits from the source dataset.
3. Train the original `PaperStyleRts79Gcn` with weighted cross entropy.
4. Select the checkpoint with the highest validation average precision; test
   labels never select epochs or hyperparameters.
5. Run the controlled `k=3/5/6/8` sweep using identical data and optimization
   settings.
6. Treat the 2,000-state run as a pilot only. A final claim requires a much
   larger multi-seed training set. RTS-79 had roughly 821 states per line;
   IEEE118 pilot-2000 has only about 10.8 states per line.

## 7. Ranking Protocol

The production ranking is hierarchical:

1. Physically evaluate all 186 N-1 lines once.
2. Rank Tier A paths first because their second outage is N-1 critical.
3. Rank remaining paths with the reused RTS-79 GCN residual score.

Report both:

- candidate N-2 evaluations `K`;
- total physical evaluations `186 + K`.

Report full-system and residual-only results for:

- `K90`, `K95`, `K99`, `Kall`;
- critical and relay-cascade hit counts;
- precision and recall;
- captured total load shed;
- fixed and percentage budgets;
- cumulative critical-path-found curve points.

Baselines remain random (10 seeds), line order, and the physically implemented
LODF_yP baseline. The same truth universe and budgets must be used by every
method.

## 8. Implementation Artifacts

- `analyze_ieee118_n1_residual_n2.py`: structural and diagnostic audit.
- `build_ieee118_residual_reachable_dataset.py`: residual labels and masks.
- `train_ieee118_residual_reachable_gcn.py`: wrapper around the original model.
- `evaluate_ieee118_n1_gated_search.py`: hierarchical ranking evaluation.
- `tests/test_ieee118_n1_residual_reachable.py`: focused regression tests.

Large local artifacts stay under:

`results/gcn_search/ieee118_n1_residual_reachable_gcn/`

Only compact summaries, curves, top-path samples, and documentation may be
committed.

## 9. Current Status (2026-07-12)

- Branch: `feature/ieee118-n1-residual-reachable-gcn`.
- N-1/residual audit: complete.
- Residual dataset conversion: complete for the 2,000-state pilot.
- Original-model training wrapper: complete.
- Best-validation-AP checkpoint selection: complete.
- Controlled `k=3/5/6/8` pilot sweep: complete.
- Selected radius by validation AP: `k=6` (approximately 12 hops).
- Fair N-1-gated random, line-order, and LODF_yP baselines: complete.
- Focused tests: 9 passed.
- Selected `k=6` primary path-probability total K90: 2,189 evaluations.
- Selected `k=6` second-only ablation total K90: 2,125 evaluations.
- N-1-gated line-order / LODF_yP / random total K90: 3,879 / 4,617 /
  5,129.6 respectively.
- Compact sweep, comparison, threshold, and curve tables: complete.
- Full-scale training-data generation: not yet complete.
- Final paper-level GCN claim: not yet permitted.

## 10. Decision Gate

Choose the graph radius using validation AP and frozen test search-efficiency
curves, not a single `Recall@100` number. Proceed to large-scale data generation
only if the hierarchical method shows stable improvement over the existing GCN
ranking and physical baselines. If it does not, audit data coverage and target
calibration before changing any model architecture.
