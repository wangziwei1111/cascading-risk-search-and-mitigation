# IEEE118 Mechanism-Aware GCN and Negative-Transfer Audit

## Objective

This phase tested whether the unchanged RTS-79 `PaperStyleRts79Gcn` backbone
could recover more difficult IEEE118 critical paths by learning three physical
severity signals:

- `log1p(num_relay_trips)` for overload-cascade severity;
- `log1p(island_load_shed_mw)` for island severity;
- `log1p(total_load_shed_mw)` for consequence severity.

The graph layers, primary classifier, input features, and deployment interface
were not replaced. Auxiliary heads existed only during training. Formal
checkpoints contain ordinary `PaperStyleRts79Gcn` member states.

## Mechanism Target Construction

The paper-8000 dataset stored critical labels but not mechanism outcomes. The
target builder therefore replayed only already-queried S1 positives:

| Item | Count |
|---|---:|
| Original Phase-3 queries | 61,973 |
| Label-free tail queries | 6,197 |
| Known queried S1 mechanism labels | 63,903 |
| Positive paths requiring replay | 4,604 |
| Successful positive replays | 4,604 |
| Critical-label inconsistencies | 0 |
| Relay-cascade positives | 4,562 |
| Positive island-shed paths | 4,596 |

Unqueried outcomes never enter an auxiliary loss. No full-truth CSV is read by
the mechanism builder. Checkpoint/resume prevents completed physical replay
from being repeated.

Binary relay and island labels were nearly identical to the critical label, so
the final experiment used continuous severity targets instead of pretending
those binary targets supplied substantial new information.

## Weighted Multi-Task Result

Validation selected the three-severity objective:

| Metric | Tail GCN | Weighted mechanisms |
|---|---:|---:|
| Validation K95 | 99,415 | **95,909** |
| Held-out test K95 | 11,844 | **11,140** |
| Formal path K90 | 1,843 | **1,829** |
| Formal path K95 | 4,026 | **3,869** |
| Formal path K99 | 21,083 | **21,019** |
| Residual second K95 | **23,278** | 24,556 |

Despite better offline K95, five new prospective seeds produced `-7` critical,
`-8` relay, and `-471.10 MW` load-shed capture. This is negative transfer, so
the weighted checkpoint was rejected.

## PCGrad Correction

PCGrad projects conflicting task gradients rather than allowing one task to
undo another task's update. The reference is Yu et al., *Gradient Surgery for
Multi-Task Learning*, NeurIPS 2020:
https://papers.nips.cc/paper_files/paper/2020/hash/3fe78a8acf5fda99de95303940a2420c-Abstract.html

This implementation is deliberately asymmetric: the critical-retrieval
gradient is preserved, and only an opposing auxiliary shared-backbone gradient
is projected. The primary/auxiliary gradient conflict ratio was approximately
49% in epoch 1 and 61% in epoch 5. This empirically confirms the conflict that
the plain weighted loss exposed. GradNorm is a related magnitude-balancing
alternative, but was not claimed as implemented:
https://proceedings.mlr.press/v80/chen18a.html

PCGrad improved offline retrieval relative to tail GCN:

| Metric | Tail GCN | PCGrad mechanisms |
|---|---:|---:|
| Validation K95 | 99,415 | **96,530** |
| Held-out test K95 | 11,844 | **11,394** |
| Formal path K90 | 1,843 | **1,826** |
| Formal path K95 | 4,026 | **3,820** |
| Formal path K99 | 21,083 | **20,724** |
| Residual second K95 | **23,278** | 24,247 |

Across ten untouched prospective seeds, only six reached the GCN fallback.
The aggregate change was `+2` critical, `-9` relay, and `-183.97 MW`. Among the
six informative seeds, critical discovery had three wins, one tie, and two
losses. The mixed result does not satisfy the promotion criterion.

## GCN-UCB Application Ablation

The deployment-only score was:

```text
score = ensemble_mean_probability + lambda * ensemble_standard_deviation
```

Validation K95 selected `lambda=0.25` from the frozen grid
`0, 0.1, 0.25, 0.5, 1, 2, 4`. No outcome labels are read during ranking and no
extra physical query is added.

Across five new prospective seeds, three reached fallback. Aggregate critical
discovery was unchanged, relay discovery increased by two, and load-shed
capture increased by 142.44 MW. One informative seed still lost four critical
paths, so UCB is retained as a mixed ablation rather than the primary policy.

## Decision

The formal model remains the PR #24 tail hard-pairwise GCN. The full adaptive
policy's recall is still not a standalone GCN score. Mechanism-aware weighted
training, primary-protected PCGrad, and GCN-UCB each rescue some difficult paths
but exchange others; none is stable enough to support a stronger claim.

The next model experiment should not add more correlated terminal labels. A
defensible next target is an audited cascade-trajectory representation (relay
generation sequence or next-outage target) with a pre-registered multi-seed
evaluation, because terminal mechanism labels provide too little diversity.
