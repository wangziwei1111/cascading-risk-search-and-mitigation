# IEEE118 N-1 Gate + Residual-Reachable GCN Pilot Results

## Result Scope

This experiment uses the IEEE118 early-stop ordered N-2 truth generated with:

- `flow_scaled=8.00`;
- `min_rate_a=1.0`;
- held-out truth seed `20260708`;
- 32,560 valid ordered N-2 paths;
- 1,754 critical paths, including 1,643 relay cascades.

The GCN is the original RTS-79
`PaperStyleRts79Gcn`. Its core layers and loss family were not replaced. The
IEEE118 changes are data targets/masks, a configurable graph radius, checkpoint
selection, and hierarchical search evaluation.

This is a 2,000-state training pilot, not a final full-scale model result.

## Why the Earlier IEEE118 Result Was Weak

Three mismatches were identified.

1. Ten lines are already critical under a single N-1 outage. They should be
   found once with a 186-line physical prescreen instead of relearned separately
   in every ordered N-2 path.
2. Before masking those lines, every valid first line had at least one critical
   continuation. The old S0 `any-critical` target was therefore all-positive
   and could not rank first-line fragility.
3. RTS-79 has line-graph diameter 6, whereas IEEE118 has diameter 15. The RTS-79
   setting `k_gcn=3` reaches about 6 hops through two layers and covers only
   58.24% of IEEE118 line pairs.

The correction uses an N-1 Tier A followed by a residual ordered N-2 ranking.
The new S0 label asks whether a first line can reach a critical continuation
outside Tier A; the S1 label remains the unchanged full-truth critical label.

## Structural Audit

The ten N-1-critical lines are:

`L016, L047, L051, L061, L096, L147, L180, L181, L183, L184`.

Paths ending at one of these lines form Tier A:

| Quantity | Value |
|---|---:|
| Tier A paths | 1,760 |
| Tier A critical paths | 1,556 |
| Tier A precision | 88.409% |
| Fraction of all critical paths in Tier A | 88.7% |
| Residual paths | 30,800 |
| Residual critical paths | 198 |
| Residual critical ratio | 0.6429% |

The gate is not an N-2 label shortcut. It is obtained by running each of the 186
single-line contingencies once, and those 186 physical evaluations are added to
the reported total cost.

## Controlled Graph-Radius Sweep

All runs use the same 2,000 states, seed split, weighted cross entropy, channel
counts, learning rate, and original model class. The checkpoint with maximum
validation average precision is restored before test evaluation.

| k | Approx. max hops | Best epoch | Validation AP | Test AP | S1 AP | Candidate K90 (second-only) | Total physical K90 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 6 | 17 | 0.1325 | 0.1328 | 0.1318 | 2,050 | 2,236 |
| 5 | 10 | 18 | 0.2088 | 0.3121 | 0.2984 | 1,877 | 2,063 |
| 6 | 12 | 20 | **0.3416** | **0.4463** | **0.3167** | 1,939 | 2,125 |
| 8 | 16 | 12 | 0.2473 | 0.2167 | 0.1160 | 2,100 | 2,286 |

`k=6` is selected because it has the best validation AP. The held-out threshold
for `k=5` happens to be smaller, but selecting it after inspecting test K90 would
be test-set leakage. The `k=8` degradation is consistent with oversmoothing.

## Fair Hierarchical Comparison

Every hierarchical baseline receives the same N-1 gate. Thus the comparison
isolates the residual ranking rather than giving the GCN exclusive access to
the physical prescreen.

| Method | Candidate K90 | Total physical K90 | Candidate K95 | Total physical K95 |
|---|---:|---:|---:|---:|
| N-1 + GCN second-only ablation | **1,939** | **2,125** | **3,033** | **3,219** |
| N-1 + GCN path probability | 2,003 | 2,189 | 3,176 | 3,362 |
| N-1 + line order | 3,693 | 3,879 | 16,118 | 16,304 |
| N-1 + LODF_yP | 4,431 | 4,617 | 15,845 | 16,031 |
| N-1 + random, 10 seeds | 4,943.6 +/- 398.6 | 5,129.6 +/- 398.6 | 18,535.2 | 18,721.2 |
| LODF_yP without gate | 29,142 | 29,142 | 30,773 | 30,773 |
| random without gate, 10 seeds | 29,353.7 +/- 245.1 | 29,353.7 +/- 245.1 | 30,903.2 | 30,903.2 |

The path-probability row is the primary RTS-79-compatible ranking protocol. The
second-only row is a diagnostic ablation and must remain labeled as such.

At practical candidate budgets, the selected `k=6` second-only ablation gives:

| K | Critical hits | Critical recall | Relay hits | Relay recall | Precision@K |
|---:|---:|---:|---:|---:|---:|
| 2,000 | 1,583 | 90.25% | 1,515 | 92.21% | 79.15% |
| 3,000 | 1,665 | 94.93% | 1,582 | 96.29% | 55.50% |
| 5,000 | 1,716 | 97.83% | 1,628 | 99.09% | 34.32% |

The primary path-probability method reaches K90 after 2,189 total physical
evaluations. The second-only ablation reaches K90 after 2,125. It does not find
all 1,754 paths at that point: K95 and K99 remain 3,219 and 10,386 total physical
evaluations for the ablation.

## Comparison With the RTS-79 Presentation

The RTS-79 slide reports 56.6 critical paths and 68.2 searches on average:

`68.2 / 56.6 = 1.205 searches per critical path`.

For IEEE118:

- primary path-probability K90: `2,189 / 1,754 = 1.248` total evaluations per
  critical path;
- second-only K90: `2,125 / 1,754 = 1.212`;
- second-only candidate budget: `1,939 / 32,560 = 5.96%` of the search space.

The normalized K90 cost is therefore close to the RTS-79 reference. This is not
an exact reproduction: the RTS-79 slide discusses finding all critical paths on
smaller scenarios, while this IEEE118 pilot reports 90% recall and explicitly
charges 186 N-1 prescreen evaluations.

## Limitations and Next Step

1. Training has only 2,000 states, about 10.8 states per IEEE118 line, far below
   the RTS-79 training density of roughly 821 states per line.
2. The full truth uses one held-out load seed. Multi-seed testing is still needed.
3. The N-1 gate explains most early recall; the learned residual model should be
   judged against equally gated baselines, as done here.
4. K99 remains much larger than K90, so the residual tail is not solved.
5. `second_only` is an ablation, not a replacement for the original RTS-79 path
   probability unless a later method section explicitly justifies that change.

The next high-value experiment is to generate a substantially larger multi-seed
residual-reachable training dataset, keep `k=6` fixed from this pilot, retrain the
same model class, and evaluate on untouched seeds. No new GCN architecture is
needed before that data-scale test.

## Reproduction

```powershell
& '.venv\Scripts\python.exe' src/gcn_search/ieee118/build_ieee118_residual_reachable_dataset.py

& '.venv\Scripts\python.exe' src/gcn_search/ieee118/train_ieee118_residual_reachable_gcn.py `
  --k-gcn 6 --epochs 20 --positive-weight 20 `
  --output-dir results/gcn_search/ieee118_n1_residual_reachable_gcn/training_k6

& '.venv\Scripts\python.exe' src/gcn_search/ieee118/evaluate_ieee118_n1_gated_search.py `
  --model-path results/gcn_search/ieee118_n1_residual_reachable_gcn/training_k6/ieee118_residual_reachable_gcn_k6_model.pt `
  --first-step-probabilities-csv results/gcn_search/ieee118_n1_residual_reachable_gcn/training_k6/base_state/ieee118_rts79_gcn_first_step_probabilities.csv `
  --feature-normalizer-json results/gcn_search/ieee118_n1_residual_reachable_gcn/pilot_2000_dataset/ieee118_residual_reachable_feature_normalizer.json `
  --include-lodf `
  --output-dir results/gcn_search/ieee118_n1_residual_reachable_gcn/eval_k6

& '.venv\Scripts\python.exe' src/gcn_search/ieee118/summarize_ieee118_n1_residual_gcn.py
```
