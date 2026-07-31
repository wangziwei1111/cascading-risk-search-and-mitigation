# IEEE118 Tail-Critical GCN Improvement Plan

## Research Question

Can the unchanged RTS-79 `PaperStyleRts79Gcn` backbone recover more of the
critical IEEE118 ordered N-2 tail without restoring exhaustive high-fidelity
training labels or reading unqueried outcomes during deployment?

The Phase-4 prospective result found 86.44% of critical paths in 2,100 N-2
queries, but stage attribution showed that promoted-family expansion supplied
1,548 of the 1,613 hits. The unchanged-GCN fallback found only 14 critical
paths in 104 remaining queries. This phase targets that residual tail.

## Literature Basis

1. Liu et al. map transmission branches to graph nodes and combine GCN output
   with physical search rules. Their weighted NLL addresses imbalance but is
   still a pointwise classification objective. This is the reproduced
   baseline, not a new architecture:
   https://arxiv.org/abs/2001.11553
2. Focal Loss reduces the influence of easy examples and concentrates gradient
   on hard mistakes under severe foreground/background imbalance:
   https://openaccess.thecvf.com/content_iccv_2017/html/Lin_Focal_Loss_for_ICCV_2017_paper.html
3. Top-of-list accuracy and top-k ranking work show that ordinary whole-list
   classification is not aligned with retrieval quality at a limited search
   budget:
   https://proceedings.neurips.cc/paper/2012/hash/7fe1f8abaad094e0b5cb1b01d712f708-Abstract.html
   and
   https://proceedings.neurips.cc/paper_files/paper/2009/hash/ba2fd310dcaa8781a9a652a31baf3c68-Abstract.html
4. GALAXY treats extreme class imbalance as an active-learning problem and
   queries near graph decision boundaries, supporting targeted acquisition of
   rare, uncertain outcomes rather than random labels:
   https://proceedings.mlr.press/v162/zhang22k.html
5. Reciprocal Rank Fusion combines complementary retrieval rankings without
   requiring comparable score calibration. It is a suitable deployment-only
   ablation for GCN, iterative LODF, and uncertainty rankings:
   https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/
6. Recent cascade-prediction work predicts cascade generations rather than
   only a terminal binary label, motivating a later multi-task extension once
   non-leaking sequence targets are available:
   https://arxiv.org/abs/2404.16134

## Identified Gap

The current weighted cross-entropy asks whether each candidate is critical in
isolation. The actual deployment objective is ordered retrieval under a small
physical-query budget. Easy negatives dominate the candidate pool, while a
low-scored positive far down the list receives no stronger ranking penalty
than an already well-ranked positive.

The tail also contains multiple physical mechanisms. A single GCN probability
can be uncertain where topology-induced islanding and overload-relay stress
disagree. This motivates a separate deployment fusion rather than silently
folding physical proxy outputs into training labels.

## Core Improvement: Hard Tail Pairwise Fine-Tuning

Keep `PaperStyleRts79Gcn`, its graph layers, features, and classifier unchanged.
Starting from the Phase-3 5%-label checkpoint, fine-tune with:

```text
loss = focal weighted cross entropy
     + lambda_tail * softplus(score_hard_negative
                              - score_hard_positive + margin)
```

For every S1 state, hard positives are the lowest-scored queried critical
lines and hard negatives are the highest-scored queried non-critical lines.
Only the existing query mask can participate. Unqueried labels and formal test
truth are forbidden from the loss.

This directly trains the model to lift missed critical candidates above the
false alarms that currently occupy the search head.

## Application Improvement: Tail Rank Fusion

After promoted-family expansion, rank the untouched candidates using a
validation-frozen reciprocal-rank fusion of:

- tail-aware GCN probability;
- transformer-tap-aware iterative LODF severity;
- ensemble uncertainty;
- optional family-diversity rank.

The fusion uses no critical labels at deployment. It must be reported as a
combined application policy, not as standalone GCN accuracy.

## Experiments

### Training ablation

- Phase-3 checkpoint without continuation;
- weighted CE continuation control;
- focal CE only;
- hard pairwise only;
- focal CE plus hard pairwise.

The architecture, 5% high-fidelity query mask, split, and model seeds stay
fixed. Model selection uses validation data only.

### Ranking ablation

- original GCN score;
- tail-aware GCN score;
- iterative LODF;
- GCN + LODF reciprocal-rank fusion;
- GCN + LODF + uncertainty fusion;
- frozen Phase-4 adaptive policy with each fallback.

### Metrics

- validation and held-out average precision;
- critical and relay Recall@K;
- K90, K95, and K99;
- missed-critical count after 2,100 queries;
- load-shed capture;
- N-1 constructions and N-2 physical queries;
- mean and worst result across prospective seeds.

## Guardrails

- Do not create a replacement GCN architecture for the primary experiment.
- Do not use `critical`, load shed, relay outcomes, or full-truth ranks as
  inference features.
- Do not tune on seed `20260709`; it remains prospective audit data.
- Keep model improvement and adaptive search-policy improvement separately
  attributed.
- A single-seed gain is exploratory, not a real-grid claim.

## Acceptance Criteria

The core improvement is retained only if it improves validation AP and either
formal K95/K99 or the prospective fallback hit rate without materially
worsening K90. The application fusion is retained only if it improves the
remaining-tail recall at equal physical-query budget on multiple unseen seeds.
