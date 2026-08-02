# IEEE118 Uncertainty-Aware Global Fusion Ablation

## Hypothesis

The unchanged `PaperStyleRts79Gcn` already contains an ensemble of independently
initialized members. [Deep Ensembles (Lakshminarayanan, Pritzel, and Blundell,
NeurIPS 2017)](https://papers.neurips.cc/paper_files/paper/2017/hash/9ef2ed4b7fd2c810847ffa5fa85bce38-Abstract.html)
motivate using member disagreement as a predictive-uncertainty signal,
particularly under distribution shift. The application hypothesis was that
adding a small uncertainty ranking to the PR #28 global rank fusion would rescue
hard paths missed by both risk scores.

## Controlled change

The GCN backbone, pair-interaction head, physical oracle, N-2 budget, and
training labels remain unchanged. The candidate ranking is a three-way global
RRF:

```text
0.70 pair-interaction risk + 0.20 frozen-GCN risk + 0.10 ensemble disagreement
```

The uncertainty signal is the standard deviation of the frozen GCN ensemble
member probabilities. No critical labels, load shed, relay outcomes, or
full-truth data are read during ranking.

## Development ablation

Development seeds were 20261216–20261220.

| Method | Critical | Relay | Captured shed (MW) | Fallback critical |
|---|---:|---:|---:|---:|
| Global RRF 0.70 | 6,375 | 5,867 | 218,667.12 | 352 |
| Uncertainty 0.10 | 6,392 | 5,883 | 219,592.48 | 369 |
| Uncertainty 0.05 | 6,382 | 5,877 | 219,025.04 | 359 |
| Uncertainty 0.02 | 6,382 | 5,878 | 218,822.84 | 359 |

The gain is real in aggregate, but uncertainty 0.10 still lost one critical hit
on one development seed. Lower weights did not remove this instability.

## Untouched prospective evaluation

Seeds 20261221–20261225 were not used for weight selection.

| Method | Critical | Relay | Captured shed (MW) | Fallback critical |
|---|---:|---:|---:|---:|
| Global RRF 0.70 | 6,642 | 6,212 | 233,130.63 | 405 |
| Uncertainty 0.10 | 6,653 | 6,222 | 233,308.66 | 416 |

Uncertainty fusion added 11 critical paths, 10 relay-cascade paths, and 178.03
MW in aggregate, but regressed critical discoveries on 2 of 5 seeds. It is
therefore retained as an optional exploration ablation, not promoted to the
main method. PR #28 global RRF 0.70 remains the default because it had no
critical-path regression on its five untouched validation seeds.

## Interpretation

Uncertainty is useful as a small exploration signal, but disagreement alone is
not a reliable proxy for cascade severity. The next model improvement should
learn or estimate trajectory-level risk, rather than increasing the weight of
terminal uncertainty. This experiment is not evidence of real-grid deployment
readiness.

## Reproduction

```bash
python src/gcn_search/ieee118/run_ieee118_prospective_oracle.py \
  --seed 20261221 \
  --max-n2-queries 2100 \
  --fallback-reserve-queries 500 \
  --interaction-head-checkpoint <local-pair-head> \
  --interaction-fusion-mode global_rrf_uncertainty \
  --interaction-fusion-weight 0.70 \
  --interaction-uncertainty-weight 0.10 \
  --output-dir <local-output-dir>
```
