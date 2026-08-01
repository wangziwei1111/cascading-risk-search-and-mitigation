# IEEE118 Pair-Interaction GCN Reranker

## Research Question

PR #26 improved aggregate IEEE118 tail retrieval by reorganizing the same
physical-label budget into dense S1 candidate lists. Two limitations remained:

- residual second-only K95 was 23,859, worse than the PR #24 value 23,278;
- one of five prospective development seeds lost four critical discoveries.

This phase asks whether the unchanged RTS-79 `PaperStyleRts79Gcn` is missing an
explicit representation of the relation between the first active outage and a
candidate second outage.

## Diagnosis and Literature

The failed seed did not support a simple insufficient-receptive-field story.
The ten critical paths uniquely selected by the older model had mean line-graph
distance 2.0 and were all within six hops. Increasing GCN depth was therefore
not justified.

The selected transfer mechanism comes from graph pair prediction:

- [SEAL (NeurIPS 2018)](https://github.com/muhanzhang/SEAL) represents a target
  pair using its enclosing graph structure and attributes rather than two
  unrelated node scores.
- [NBFNet (NeurIPS 2021)](https://papers.neurips.cc/paper/2021/hash/f6a673f09493afcd8b129a0bcf1cd5bc-Abstract.html)
  explicitly defines pair representations through paths between graph nodes.
- [Decoupled long-tail training (ICLR 2020)](https://arxiv.org/abs/1910.09217)
  motivates freezing a learned representation and correcting the downstream
  classifier under imbalance.

The literature facts do not establish cascade-search performance. The local
transfer hypothesis is that first-line/candidate structural interaction is
missing from the decision head and can be added without replacing the GCN.

## Method

The original `PaperStyleRts79Gcn` checkpoint from PR #26 is frozen. A weighted
linear head receives 18 deployable features for each S1 candidate:

- frozen GCN logit;
- normalized line-graph distance between first and candidate lines;
- four candidate state features;
- four first-line state features;
- four absolute feature differences;
- four elementwise interaction products.

The head has no cascade-outcome inputs. In particular, `critical`, load shed,
relay trips, mechanism labels, and all label aliases are excluded. It trains on
63,903 S1 candidate labels that were already physically queried by Phase 3 plus
the fixed 6,197-query dense acquisition. No additional training-time N-2
simulation is introduced.

## Controlled Ablation

Selection uses validation K95 only. Formal seed 20260708 is audit-only.

| Method | Validation K95 | Test K95 | Formal path K95 | Residual second-only K95 |
|---|---:|---:|---:|---:|
| Frozen PR #26 GCN | 97,822 | 11,707 | 3,800 | 23,859 |
| Refit GCN logit only | 99,445 | 12,152 | 5,035 | 23,859 |
| GCN + candidate features only | 100,478 | 11,704 | 5,331 | 24,827 |
| **GCN + first/candidate relation** | **85,298** | **8,815** | **3,604** | **22,226** |

Simple calibration and candidate-only features failed. The improvement appears
only when the first-line/candidate relation is represented, supporting the
stated mechanism. A separate probability blend of PR #24 and PR #26
checkpoints was also rejected because validation selected the pure PR #26 model.

The formal-seed result is a Pareto tradeoff rather than uniform dominance. The
relation head improved path K95 from 3,800 to 3,604, but path K90 changed from
1,819 to 1,843 and path K99 from 21,323 to 22,007. The defensible claim is
better middle-tail retrieval and prospective aggregate yield, not improvement
at every search budget.

## Untouched Prospective Evaluation

Seeds 20261206 through 20261210 were not used for training, validation,
feature selection, or the preceding diagnosis. Search did not read full truth.
Both methods used a 2,100-query N-2 budget and a nominal 500-query learned
fallback reserve per seed.

| Seed | Critical delta | Relay delta | Captured shed delta (MW) |
|---:|---:|---:|---:|
| 20261206 | +8 | +2 | +209.345 |
| 20261207 | +1 | +5 | +30.743 |
| 20261208 | +20 | +22 | +657.598 |
| 20261209 | +15 | +11 | +408.328 |
| 20261210 | -9 | -10 | -130.530 |
| **Total** | **+35** | **+30** | **+1,175.484** |

The fallback stages evaluated 2,611 candidates in each method. Critical hits
increased from 382 to 417, so observed fallback precision increased from
14.63% to 15.97%. There were no physical-simulation errors.

The result is not uniform: seed 20261210 regressed. The supported claim is an
aggregate improvement across the five untouched scenarios, not worst-case
dominance or a complete solution to cross-scenario robustness.

## Reproduction

```bash
python src/gcn_search/ieee118/train_ieee118_pair_interaction_reranker.py \
  --output-dir results/gcn_search/ieee118_pair_interaction_gcn/formal_e250

python src/gcn_search/ieee118/run_ieee118_prospective_oracle.py \
  --seed 20261206 \
  --max-n2-queries 2100 \
  --fallback-reserve-queries 500 \
  --gcn-checkpoint <local-pr26-checkpoint> \
  --interaction-head-checkpoint <local-pair-head> \
  --output-dir <local-output-dir>

python src/gcn_search/ieee118/summarize_ieee118_pair_interaction_gcn.py
```

The relation-head checkpoint, GCN checkpoints, full predictions, full truth,
and physical query logs remain local. Only compact evidence is versioned.
