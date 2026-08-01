# IEEE118 Robust Global Rank Fusion

## Remaining defect

The frozen `PaperStyleRts79Gcn` plus pair-interaction head improved aggregate
prospective discovery in PR #27, but one of five untouched scenarios regressed.
The head can over-correct candidates that the frozen GCN ranked well. The next
question was therefore robustness under scenario shift, not additional model
capacity.

## Literature and transfer hypothesis

[Cormack, Clarke, and Buettcher (SIGIR 2009)](https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/)
introduced Reciprocal Rank Fusion (RRF) to combine complementary rankings while
avoiding dependence on incompatible raw score calibration. The paper establishes
the information-retrieval mechanism, not power-grid performance.

The local transfer hypothesis was that the frozen GCN and relation head recover
partly different critical paths, so rank fusion could provide a deployment-time
guardrail. No outcome label is read when constructing the fused ranking.

## Failed local fusion

An initial implementation fused the two rankings separately inside every S1
state. It failed strongly: the operation made conditional ranks comparable
within an S1 but destroyed the calibrated risk scale between different first
outages. Across development seeds, local RRF weights 0.70 and 0.85 produced only
244 and 242 fallback critical hits, respectively, versus 409 for the frozen GCN.
This failure is retained rather than hidden.

## Selected method

The corrected method independently constructs two global candidate-path pools
with the same lazy best-first search and applies weighted RRF at path level.
This avoids claiming that all 34,410 paths are materialized. The GCN core and
relation head remain frozen. Development used seeds 20261201 through 20261205
only.

The frozen selection rule was:

1. reject any method that falls below the frozen GCN on any development seed;
2. maximize aggregate fallback critical hits;
3. tie-break by relay hits and captured load shed.

| Method | Fallback critical | Fallback relay | Seeds below baseline |
|---|---:|---:|---:|
| Frozen GCN | 409 | 386 | 0 |
| Pair relation | 448 | 425 | 2 |
| Global RRF, pair weight 0.50 | 443 | 418 | 1 |
| **Global RRF, pair weight 0.70** | **460** | **424** | **0** |
| Global RRF, pair weight 0.85 | 452 | 420 | 0 |

The selected pair weight was fixed at 0.70 before prospective evaluation.

## Untouched prospective result

Seeds 20261211 through 20261215 were not used for diagnosis, method selection,
or weight selection. Every method used 2,100 N-2 queries with a 500-query
fallback reserve and constructed 186 N-1 states per seed.

| Method | Critical | Relay | Captured shed (MW) | Fallback critical |
|---|---:|---:|---:|---:|
| Frozen GCN | 7,259 | 6,809 | 235,229.210 | 385 |
| Pair relation | 7,283 | 6,832 | 236,202.406 | 409 |
| **Global RRF 0.70** | **7,293** | **6,839** | **236,494.701** | **419** |

Relative to the frozen GCN, global fusion found 34 more critical paths, 30 more
relay-cascade paths, and 1,265.491 MW more load shed. It did not regress critical
hits on any of the five prospective seeds and produced zero simulation errors.
Relative to the pure relation head, it found 10 more critical and 7 more relay
paths, correcting the regression on seed 20261214.

## Cost and claim boundary

The method uses no additional N-2 training labels and does not increase the N-2
search budget. It evaluates both frozen scorers and can activate more candidate
prefixes while forming their global lists, but the observed N-1 construction
count remained exactly 186 per scenario.

This is evidence across five untouched synthetic IEEE118 load scenarios. It is
not a worst-case guarantee, a real utility-grid validation, or evidence that
all future scenarios improve.

## Reproduction

```bash
python src/gcn_search/ieee118/run_ieee118_prospective_oracle.py \
  --seed 20261211 \
  --max-n2-queries 2100 \
  --fallback-reserve-queries 500 \
  --interaction-head-checkpoint <local-pair-head> \
  --interaction-fusion-mode global_rrf \
  --interaction-fusion-weight 0.70 \
  --output-dir <local-output-dir>

python src/gcn_search/ieee118/summarize_ieee118_global_rank_fusion.py
```

Full physical query logs, checkpoints, and predictions remain local. Only the
compact frozen-selection and prospective evidence is versioned.
