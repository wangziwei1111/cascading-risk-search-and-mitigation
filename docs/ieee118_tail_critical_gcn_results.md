# IEEE118 Tail-Critical GCN Results

## What Changed

The formal model remains the RTS-79 `PaperStyleRts79Gcn`. Its graph layers,
input features, and classifier were not replaced. This phase changed two
things around that model:

1. **Core training improvement:** queried hard positives are explicitly pushed
   above queried hard negatives with a pairwise retrieval loss. Validation K95,
   rather than only average precision, selects the checkpoint.
2. **Application ablation:** a fixed Reciprocal Rank Fusion (RRF) combines GCN,
   iterative DC/LODF severity, and ensemble uncertainty after S1. It uses no
   cascade labels during ranking.

The hard examples were acquired using only model probability, ensemble
disagreement, and low-fidelity physics. Critical labels were read only after a
candidate had been selected for physical simulation.

## Literature-to-Implementation Trace

- The reproduced cascade GCN maps lines to graph nodes and uses weighted
  classification: https://arxiv.org/abs/2001.11553
- Focal Loss motivated the hard-example classification ablation:
  https://openaccess.thecvf.com/content_iccv_2017/html/Lin_Focal_Loss_for_ICCV_2017_paper.html
- Top-list and top-k ranking work motivated direct retrieval selection rather
  than AP-only selection:
  https://proceedings.neurips.cc/paper/2012/hash/7fe1f8abaad094e0b5cb1b01d712f708-Abstract.html
  and
  https://proceedings.neurips.cc/paper_files/paper/2009/hash/ba2fd310dcaa8781a9a652a31baf3c68-Abstract.html
- GALAXY motivated targeted rare-example acquisition under extreme imbalance:
  https://proceedings.mlr.press/v162/zhang22k.html
- RRF motivated calibration-free combination of complementary rankings:
  https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/

## Training Results

The selected hard-pairwise model used the original 61,973 queried labels plus
6,197 additional label-free-selected queries. Those new queries revealed 236
positives after simulation.

| Metric | Phase-3 GCN | Tail GCN | Change |
|---|---:|---:|---:|
| Held-out test K95 | 12,413 | 11,844 | 4.58% fewer candidates |
| Formal path K95 | 4,294 | 4,026 | 6.24% fewer candidates |
| Formal path K99 | 21,382 | 21,083 | 1.40% fewer candidates |
| Residual second-line K95 | 24,405 | 23,278 | 4.62% fewer candidates |
| Formal path K90 | 1,838 | 1,843 | 5 more candidates |

The improvement is concentrated near K95. K90 became slightly worse and K99
improved only modestly, so the difficult tail is not solved.

## Prospective Equal-Budget Results

Every run used 186 S1 constructions and exactly 2,100 N-2 physical queries.
Seeds 20260709 and 20260710 were not used for training or checkpoint selection.

| Seed | Method | Critical found | Relay found | Captured shed MW |
|---:|---|---:|---:|---:|
| 20260709 | Phase-3 GCN policy | 1,613 | 1,487 | 53,443.71 |
| 20260709 | Tail-GCN policy | **1,614** | **1,489** | **53,538.49** |
| 20260710 | Phase-3 GCN policy | 1,414 | 1,312 | **45,460.71** |
| 20260710 | Tail-GCN policy | **1,415** | 1,312 | 45,451.59 |

The tail model gained one critical path on both seeds. This is reproducible in
direction but small in magnitude. On audited seed 20260709, critical recall
rose from 86.4416% to 86.4952%; relay recall rose from 86.1530% to 86.2688%.

Most of that 86% recall is **not a standalone GCN result**. On seed 20260709,
probe and promoted-family expansion found 1,599 of the 1,614 critical paths;
the tail-GCN fallback found 15. The fair GCN claim is the fallback/ranking
increment, not the whole policy total.

## RRF Ablation

Fixed RRF (`k=60`, uncertainty weight `0.25`) on seed 20260709 found 1,614
critical and 1,487 relay-cascade paths, capturing 53,571.01 MW. Compared with
tail-GCN alone it kept critical count unchanged, lost two relay hits, and added
32.52 MW load-shed capture. It is therefore recorded as a mixed, non-winning
application ablation and is not promoted as the primary method.

## Conclusion and Next Experiment

Hard-pairwise retrieval training is more effective than focal loss for this
dataset, but the practical gain is still incremental. The next defensible core
experiment is mechanism-aware multi-task supervision on already queried data:
separate critical, relay-cascade, and islanding heads sharing the unchanged GCN
encoder, followed by validation-frozen tail ranking. It should be compared over
at least five untouched prospective seeds. Sequence-level cascade targets are
also supported by recent generation-prediction work, but require a separately
audited non-leaking target builder: https://arxiv.org/abs/2404.16134

No claim is made here that IEEE118 has reproduced the large RTS-79 presentation
gap, nor that the method is ready for direct deployment on a real grid.
