# IEEE118 Groupwise Supervision and Tail-Ranking GCN

## Scope

This phase improves the IEEE118 search model without changing the core
`PaperStyleRts79Gcn` architecture inherited from RTS-79. It does not introduce
Simulink/MATLAB, regenerate full truth, or treat the earlier NumPy
`GCN_smoke` scorer as a formal GCN.

The experiment addresses a specific deployment question: under the same
number of training-time N-2 physical queries, can labels be organized so that
the GCN ranks difficult second outages more accurately within each first-step
state?

## Baseline Diagnosis

The Phase-3 checkpoint provides sparse queried labels across 7,091 training
states. The PR24 tail acquisition then adds 6,197 label-free-selected physical
queries.

| Acquisition | Extra queries | S1 states touched | Median extra queries per selected S1 | Extra positives |
|---|---:|---:|---:|---:|
| Scattered round-robin | 6,197 | 6,197 | 1 | 236 |
| Dense-state | 6,197 | 37 | 168 | 49 |

The original selector therefore gives exactly one additional candidate label
to each of 6,197 different S1 states. Deployment, however, ranks roughly 185
second-line candidates inside one S1 state. The diagnosis is a mismatch between
the geometry of supervision and the geometry of the ranking task, rather than
simply an insufficient number of labels.

Selection remains label-free. Critical labels are read only after selection to
audit what the fixed query budget revealed.

## Literature Basis

- [ListNet (ICML 2007)](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2007-40.pdf?file=tr-2007-40.pdf)
  treats a complete ranked list as the learning instance instead of reducing
  ranking entirely to independent points or pairs.
- [Smooth-AP (ECCV 2020)](https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123540647.pdf)
  replaces nondifferentiable average precision with a smooth ranking surrogate.
- [LambdaLoss (CIKM 2018)](https://research.google/pubs/the-lambdaloss-framework-for-ranking-metric-optimization/)
  formalizes metric-driven ranking losses.
- [BADGE (ICLR 2020)](https://iclr.cc/virtual_2020/poster_ryghZJBKPS.html)
  motivates combining uncertainty and diversity in batch active learning.

These papers support the transfer hypothesis, but they do not by themselves
prove effectiveness for cascade search. The controlled IEEE118 experiments
below provide that evidence.

## Controlled Improvements

### Core improvement: dense S1 supervision

`select_groupwise_dense_batch` uses the existing label-free combination of
physics disagreement, model uncertainty, and missed-risk evidence. It selects
high-value S1 states with load-scenario diversity, then queries nearly all
remaining valid second-line candidates in a selected state before moving on.

The physical query budget remains 6,197. The original
`PaperStyleRts79Gcn`, graph powers, input features, Phase-3 initialization, and
hard-pairwise loss remain unchanged.

### Tested ranking extension: Smooth-AP

A Smooth-AP-style loss was added only for S1 rows with at least 128 queried
candidates. Sparse active-learning rows are skipped. This extension improved
the audit-only formal-seed K95, but validation K95 selected ordinary
hard-pairwise training instead. Smooth-AP is retained as a documented negative
ablation and is not the formal selected model.

### Application improvement: reserved GCN search budget

The prospective policy previously allowed promoted physical expansions to use
the entire N-2 budget. In three of five new scenarios, a 2,100-query run never
reached the GCN fallback. `--fallback-reserve-queries` now optionally reserves
part of the budget for difficult candidates ranked by the learned model.

The default is zero, preserving historical behavior. The controlled evaluation
uses a total N-2 budget of 2,100 and explicitly reserves 500 queries for GCN.
The budget and reserve are now included in the configuration fingerprint.

## Offline Ablation

All methods use `PaperStyleRts79Gcn`. Model selection uses validation K95;
formal seed 20260708 is audit-only.

| Method | Validation K95 | Test K95 | Formal path K95 | Residual second-only K95 |
|---|---:|---:|---:|---:|
| Phase-3 checkpoint | 101,458 | 12,413 | 4,294 | 24,405 |
| Scattered + hard pairwise (PR24) | 99,415 | 11,844 | 4,026 | 23,278 |
| Dense S1 + hard pairwise (selected) | **97,822** | **11,707** | **3,800** | 23,859 |
| Dense S1 + Smooth-AP (rejected) | 98,827 | 11,741 | 3,705 | 24,281 |

Dense supervision improves the validation-selected and formal overall K95, but
does not beat PR24 on residual second-only K95. This is a real limitation, not
a metric to omit.

## Prospective Physical-Oracle Results

Seeds 20261201 through 20261205 were not used for training, validation, or
hyperparameter selection. Search did not read full truth. Both models received
the same 2,100 N-2 query budget and the same 500-query GCN reserve per seed.

| Seed | Critical delta | Relay-cascade delta | Captured shed delta (MW) |
|---:|---:|---:|---:|
| 20261201 | +4 | +4 | +174.474 |
| 20261202 | +3 | +4 | +40.308 |
| 20261203 | -4 | -3 | -200.005 |
| 20261204 | +7 | +1 | +114.867 |
| 20261205 | +19 | +22 | +479.935 |
| **Total** | **+29** | **+28** | **+609.579** |

Across the 2,500 candidates actually ranked by GCN, the PR24 model found 380
critical paths and the dense-supervision model found 409. Critical precision
increased from 15.20% to 16.36%. There were no simulation errors.

The improvement is aggregate, not uniform: one of five seeds regressed. The
claim supported by this phase is therefore that groupwise supervision improves
mean prospective tail retrieval under the tested setting, not that it dominates
on every load scenario.

## Reproduction

```bash
python src/gcn_search/ieee118/diagnose_ieee118_groupwise_supervision.py

python src/gcn_search/ieee118/train_ieee118_tail_aware_gcn.py \
  --objectives hard_pairwise groupwise_smooth_ap \
  --epochs 5 \
  --tail-acquisition-fraction 0.005 \
  --tail-acquisition-mode dense_state \
  --output-dir results/gcn_search/ieee118_groupwise_listwise_gcn/dense005_ablation_e5

python src/gcn_search/ieee118/run_ieee118_prospective_oracle.py \
  --seed 20261201 \
  --max-n2-queries 2100 \
  --fallback-reserve-queries 500 \
  --gcn-checkpoint <local-checkpoint> \
  --output-dir <local-output-dir>

python src/gcn_search/ieee118/summarize_ieee118_groupwise_listwise_experiment.py
```

Large NPZ files, checkpoints, physical query logs, and full predictions remain
local. Only compact diagnosis, ablation, and cross-seed summaries are versioned.

## Next Research Step

The next controlled hypothesis should target explicit first-line/second-line
interaction for the residual hard tail. It should be tested only after freezing
this groupwise baseline and should not be reported as an improvement unless it
beats the selected model on validation, formal K95/K99, residual second-only
K95, and multiple untouched prospective seeds.
