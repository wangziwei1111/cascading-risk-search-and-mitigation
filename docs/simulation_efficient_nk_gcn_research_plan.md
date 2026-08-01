# Simulation-Efficient N-k GCN Research Plan

## 1. Goal

Develop a cascading-failure search method that can approach real-grid scale
without exhaustively simulating and labeling every N-k candidate.

The study follows this order:

1. reproduce the published baseline;
2. quantify the baseline gap;
3. test one core algorithmic improvement;
4. add one deployment-oriented improvement;
5. run controlled, leakage-free system experiments.

The work starts with ordered N-2 because complete truth is available for
auditing. Claims about N-3 or larger k require separate labels and experiments.

## 2. Baseline Reproduction

### B0: Published RTS-79 GCN

- Source paper: Liu et al., IEEE TCNS 2021,
  [DOI 10.1109/TCNS.2021.3063333](https://doi.org/10.1109/TCNS.2021.3063333)
- Model source:
  `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`
- Model class: `PaperStyleRts79Gcn`
- Input: one line-graph node per branch with topology, relay ratio, branch
  flow, and terminal-load features
- Output: two-class vulnerability logits for every candidate branch
- Loss: class-weighted cross entropy over the valid candidate mask
- Search score: conditional next-outage critical probability
- Physical baselines: random, line order, and LODF_yP

Reproduction gates:

- retain the reported RTS-79 workflow and existing artifacts;
- use the same model implementation for the IEEE118 baseline;
- report fixed and percentage search budgets;
- count N-1 state construction separately from ranked N-2 verification;
- never use outcome or load-shed fields as input features.

### B1: Full-label IEEE118 baseline

- Setting: `flow_scaled=8.00`, `min_rate_a=1.0`
- Frozen test scenario: seed `20260708`
- Training data: paper-aligned 8,000 graph states
- Active high-fidelity labels: 1,398,103
- Training high-fidelity labels: 1,239,452
- Existing main-model result: K90 = 1,793 ranked N-2 candidates, plus 186
  separately reported N-1 state constructions

This is the performance ceiling for the first label-efficiency experiment, not
a deployable data-generation protocol.

## 3. Confirmed Baseline Gaps

### G1: Exhaustive offline labels

For each S1 state, the builder physically opens nearly every remaining line and
runs the complete relay, island, redispatch, and load-shed process. N-k growth
is combinatorial.

### G2: No value-of-information policy

All labels cost the same in the current builder even though most are easy
negatives. The model does not choose which physical result would improve it
most.

### G3: One fidelity level for truth generation

LODF/DC indicators are evaluated only as ranking baselines. They are not used
to reduce expensive cascade labels or to learn a high-fidelity correction.

### G4: Point scores without deployment risk control

A score is treated as a ranking value. There is no calibrated rule that says
which candidates may be deferred and which must fall back to the simulator.

### G5: Limited shift and scale evidence

The current formal result is one case family and a frozen IEEE118 test seed.
Topology, load, renewable, protection-setting, and cross-case shifts remain
deployment risks.

## 4. Core Improvement: PMF-BAL-GCN

Name: **Physics-Guided Multi-Fidelity Batch Active GCN** (`PMF-BAL-GCN`).

This is an algorithm around the current GCN. Phase A deliberately leaves
`PaperStyleRts79Gcn` unchanged so gains can be attributed to oracle selection.
A later residual-fusion ablation may add the low-fidelity prior to the logits,
but it is not required for the first decision gate.

### 4.1 Candidate pool

Create S0/S1 graph states without N-2 labels. For each valid candidate path
store only non-outcome descriptors:

- current line features used by the GCN;
- candidate line loading and relay margin;
- first/candidate line-graph distance;
- DC/LODF_yP severity;
- topology and operating-scenario identifiers.

### 4.2 Initial batch

Compare:

- uniform random;
- physics-tail stratification;
- k-center core set;
- physics-stratified k-center.

The proposed initializer reserves capacity for both high-severity candidates
and broad state/topology coverage.

### 4.3 Active-query score

Train an ensemble of the unchanged baseline GCN with different random seeds.
For every unlabeled candidate compute:

- mean predicted critical probability;
- predictive entropy;
- ensemble disagreement or mutual-information proxy;
- low-fidelity physics severity.

Shortlist uncertain/high-severity candidates, then use farthest-first or BADGE
selection to remove batch redundancy. Only selected candidates call the
high-fidelity cascade oracle.

### 4.4 Sparse-label training

Use the existing candidate loss mask as a query mask:

- hidden labels never enter training;
- states with no queried labels are excluded from the optimizer loader;
- validation and test scenarios remain frozen;
- model selection uses validation AP and retrieval metrics only.

### 4.5 Stop rule

Stop when all conditions hold for two rounds:

- validation AP improvement is below a configured tolerance;
- validation Recall at the target budget does not improve materially;
- uncertainty mass above the query threshold is stable;
- the high-fidelity oracle budget is exhausted or the marginal gain per 1,000
  labels is below threshold.

## 5. Application Improvement: RCSV

Name: **Risk-Controlled Selective Verification** (`RCSV`).

The trained GCN is not allowed to hard-declare all low-score candidates safe.
Instead:

1. use an independent calibration split;
2. choose a score threshold or candidate set that controls missed-critical
   proportion at target risk `alpha`;
3. physically verify selected high-risk and uncertain candidates;
4. monitor load/topology drift;
5. under detected shift, widen the candidate set or route all cases to the
   simulator until recalibrated;
6. feed verified labels back to PMF-BAL-GCN.

Any finite-sample claim must state the conformal assumptions. Results under
operating-point shift are empirical unless the required assumptions are
satisfied.

## 6. N-k Search Extension

For k greater than two, do not enumerate all complete paths first.

Use cached best-first prefix expansion:

1. represent a prefix by the stabilized physical state after its outages;
2. score possible next outages with the conditional GCN;
3. expand only the top beam and uncertain candidates;
4. physically simulate each expanded prefix once;
5. cache by scenario, ordered prefix, protection setting, and dispatch policy;
6. use a line-status dictionary for reusable DCPF/DCOPF results.

N-3/N-4 experiments must compare against equal physical-oracle budgets. N-2
accuracy alone cannot establish N-k generalization.

## 7. Experiment Matrix

### Stage E0: cost and leakage audit

- datasets: RTS-79 and IEEE118
- output: number of states, valid labels, positive labels, physical-oracle
  calls, label imbalance, wall time, and tracked-large-file check

### Stage E1: retrospective active-learning replay

Hide IEEE118 training labels and reveal only queried labels from the existing
complete dataset. This does not reclaim past compute; it estimates what a
prospective builder would have queried.

Label budgets:

- 0.25%, 0.5%, 1%, 2%, 5%, 10%, 20%, and 100% of training labels

Methods:

- random label sampling;
- entropy-only active learning from Zhang et al.;
- k-center only;
- LODF/physics-tail only;
- uncertainty plus diversity;
- proposed uncertainty plus diversity plus physics.

Repeat each stochastic method with at least five acquisition seeds.

### Stage E2: prospective oracle run

Connect the selected acquisition policy to the real IEEE118 cascade simulator.
Generate a fresh multi-seed training set without computing hidden labels.

Primary result:

- high-fidelity cascade simulations needed to match 95% and 99% of the
  full-label baseline's test K90 performance.

### Stage E3: multi-fidelity ablation

Compare:

- high fidelity only;
- DC proxy as an input feature;
- LODF_yP proxy as an input feature;
- low-fidelity logit plus learned high-fidelity residual;
- proposed residual model plus active acquisition.

### Stage E4: selective deployment

For target missed-critical risk levels `alpha = 0.10, 0.05, 0.02, 0.01`,
measure:

- candidate coverage sent to simulation;
- empirical false-negative rate;
- critical and relay-cascade recall;
- number of exact simulator calls;
- calibration error and risk under in-distribution and shifted operation.

### Stage E5: scale and shift

Cases:

- RTS-79;
- IEEE118;
- IEEE300;
- ACTIVSg2000 as a public synthetic large-grid test.

Shifts:

- unseen load seeds;
- load scale and spatial load redistribution;
- generator availability;
- line topology;
- thermal-limit and relay-threshold settings;
- renewable operating profiles where data are available.

ACTIVSg2000 must always be described as synthetic.

### Stage E6: sampled N-3 and N-4

Use exact simulation on a statistically auditable subset plus adversarial
high-risk paths. Report confidence intervals and oracle budgets. Do not claim
full truth when only a sample is available.

## 8. Metrics

### Search quality

- critical Recall@K and Precision@K;
- relay-cascade Recall@K;
- captured total load shed;
- K90, K95, K99, and K100;
- cumulative critical paths found versus candidate evaluations.

### Label efficiency

- high-fidelity N-k oracle calls;
- high-fidelity calls per discovered positive;
- performance versus fraction of full labels;
- area under the performance-versus-oracle-budget curve.

### Safety and calibration

- false-negative rate;
- Brier score, expected calibration error, and average precision;
- selective risk versus simulator coverage;
- out-of-distribution degradation.

### Engineering cost

- data-generation wall time;
- training and inference wall time;
- peak RAM/VRAM;
- cache hit rate;
- online exact-simulation latency.

## 9. Required Ablations

1. remove uncertainty;
2. remove diversity;
3. remove physics prior;
4. entropy versus ensemble disagreement;
5. random versus k-center initialization;
6. one versus three versus five ensemble members;
7. high-fidelity-only versus multi-fidelity residual;
8. with versus without RCSV;
9. with versus without state/prefix cache;
10. in-distribution versus load/topology shift.

## 10. Statistical Protocol

- split by operating scenario, never by individual path rows;
- freeze seed `20260708` as IEEE118 test truth;
- fit normalization on training scenarios only;
- select hyperparameters on validation scenarios only;
- report mean, standard deviation, and confidence intervals across seeds;
- use paired acquisition seeds for method comparisons;
- count every high-fidelity simulator query, including calibration labels, in
  a second "total data cost" table;
- publish negative results and failed assumptions.

## 11. Decision Gates

### Gate 1: active replay

Proceed only if the proposed acquisition reaches at least 95% of full-label
validation AP and does not materially worsen test K90 while using at most 10%
of training oracle labels.

### Gate 2: prospective generation

Proceed only if replay gains survive real on-demand cascade simulation and the
queried-label distribution is not using hidden outcomes.

### Gate 3: deployment wrapper

Proceed only if RCSV reduces simulator coverage while meeting its empirical
missed-critical risk target on unseen scenarios and degrades conservatively
under shift.

### Gate 4: real-scale claim

Permit a scalability claim only after IEEE300 or ACTIVSg2000 demonstrates lower
total oracle cost and acceptable latency. Permit a real-grid claim only with
actual utility data or operator-grade validation, not from IEEE or synthetic
cases alone.

## 12. Implementation Roadmap

### Phase 1

- oracle-cost audit;
- leakage-safe acquisition library;
- deterministic random, entropy, physics, and k-center selectors;
- risk-control calibration utility;
- small retrospective smoke tests.

### Phase 2

- unchanged-GCN ensemble training;
- iterative active replay on the paper-8,000 dataset;
- compact label-efficiency curves and ablations.

### Phase 3

- on-demand physical cascade oracle;
- checkpoint/resume and query cache;
- prospective IEEE118 multi-seed generation.

### Phase 4

- multi-fidelity residual fusion;
- RCSV online simulator-routing evaluation;
- operating-point and topology-shift experiments.

### Phase 5

- IEEE300/ACTIVSg2000 scale tests;
- sampled N-3/N-4 best-first search;
- paper figures, tables, and reproducibility package.

## 13. Phase 1 Status

### E0 oracle-cost audit

The 8,000-state IEEE118 residual dataset contains:

- 1,398,103 active target high-fidelity labels;
- 1,239,452 active training labels;
- 22,045 positive target labels (1.5768%);
- an estimated 1,455,583 N-2 physical-oracle calls used by the source builder;
- 14,880 separately estimated N-1 calls used for S0 labels.

This confirms that exhaustive target generation, rather than GCN inference, is
the dominant scaling problem.

### E1 same-budget smoke

The first hidden-label replay used 120 training, 80 validation, and 80 test
states. Every method received exactly 300 queried labels from 20,823 available
training candidates (1.4407%).

| Acquisition | Queried positives | Final validation AP | Final test AP |
|---|---:|---:|---:|
| random | 3 | 0.0185 | 0.0117 |
| entropy | 3 | 0.0150 | 0.0106 |
| physics-k-center | 5 | 0.1969 | 0.0799 |
| PMF-BAL | 9 | 0.1969 | 0.0799 |

The scalable physics-stratified initializer found 5 positives in its first 200 queries,
compared with 2 for random initialization. PMF-BAL found 4 additional
positives in the next 100 queries, while physics-k-center found none.

These results support running the planned multi-seed label-efficiency study,
but they do not pass Gate 1. Training used only two epochs per round, the
absolute AP remains low, and incremental training after the second acquisition
did not improve the retained validation checkpoint.

Five paired acquisition seeds were then run with the same smoke subset and
budget:

| Acquisition | Queried positives | Validation AP | Test AP |
|---|---:|---:|---:|
| random | 3.8 +/- 2.3 | 0.0321 +/- 0.0157 | 0.0251 +/- 0.0155 |
| entropy | 12.8 +/- 12.3 | 0.0535 +/- 0.0463 | 0.0361 +/- 0.0277 |
| physics-k-center | 5.2 +/- 0.4 | 0.1108 +/- 0.0493 | 0.0540 +/- 0.0137 |
| PMF-BAL | 11.2 +/- 4.0 | 0.1223 +/- 0.0397 | 0.0582 +/- 0.0126 |

PMF-BAL has the highest mean validation and test AP in this pilot. The margin
over physics-k-center is small, and entropy has a highly variable positive-hit
count. No significance or full-dataset conclusion is claimed.

### RCSV smoke

At `alpha=0.05`, final PMF-BAL calibration selected 80.1799% of valid test
candidates for exact verification and empirically captured only 81.6216% of
test positives. The calibration bound applies to the calibration sample under
its assumptions, not automatically to this shifted finite test sample. This is
neither reliable enough nor a useful online simulation reduction. RCSV must be
retested after a stronger active model and under independent operating-point
shifts.

Across the five paired seeds, PMF-BAL selected 81.3050% of test candidates on
average and captured 90.5946% of positives on average. This remains below the
deployment gate.

### Scalability controls implemented

- sparse queried-label masks prevent hidden outcomes from entering training;
- ensemble members warm-start from their retained previous-round checkpoints;
- initial diversity runs on a reproducible candidate pool, not all candidates;
- farthest-first selections are capped and the remaining batch is filled by
  acquisition score;
- local probability/query checkpoints are ignored by git;
- compact audit and comparison summaries contain explicit retrospective
  caveats.

## 14. Phase 2 Result

### Protocol

The paper-8,000 residual dataset was replayed with exact cumulative label
budgets of 0.25%, 0.5%, 1%, 2%, and 5% of the 1,239,452 available training
labels. Each stochastic method used five paired acquisition seeds. Every round
used the unchanged `PaperStyleRts79Gcn`, two ensemble members, three warm-start
epochs, and a frozen validation/test split.

Formal search evaluation no longer relies on classification AP alone. Each
round also predicts the independent 176-state S1 evaluation dataset, aligns it
with the 32,560 valid early-stop ordered N-2 rows, applies the fixed 186-line
N-1 gate, and reports path-level K90/K95/K99/K100. Full-truth outcomes enter
only the post-inference evaluator.

### Acquisition revisions

The first weighted PMF-BAL score was unstable on the complete dataset.
Physics-k-center alone overemphasized geometric coverage and usually found
only tens of positives at 1% budget. Two revisions were therefore tested:

1. quota acquisition separately selects predicted-risk, uncertainty, and
   physics-diversity cohorts;
2. hybrid acquisition adds a fixed random-anchor cohort to reduce adaptive
   sampling bias.

The final diagnostic variant also estimates a positive-label prior from the
initial random queried batch and scales the positive class weight by the ratio
of initial to current queried positive rate. This uses only already queried
labels. It is a prior-shift correction, not rigorous IWAL propensity weighting.

### Five-seed result

The primary diagnostic method is `pmf_hybrid_prior_corrected`.

| Metric | Full labels | 5% queried labels |
|---|---:|---:|
| training oracle labels | 1,239,452 | 61,973 |
| mean test AP | 0.6167 | 0.5579 +/- 0.0150 |
| mean S1 test AP | 0.4743 | 0.4713 +/- 0.0105 |
| gated path-prob K90 | 1,793 | 1,891.2 +/- 26.7 |
| gated path-prob K95 | 2,263 | 3,569.4 |
| gated path-prob K99 | 4,305 | 21,806.2 |
| residual-only path-prob K90 | 2,521 | 19,556.0 |

This uses 95% fewer retrospective training oracle labels and preserves 90.46%
of the full-label test AP. Overall gated K90 is only 98.2 candidates worse on
average. These are useful label-efficiency results, but the high-recall tail is
not preserved.

At 5% budget, the uncorrected hybrid reaches test AP 0.5313 +/- 0.0531 and
gated K90 1,910.6 +/- 28.0. Random labeling reaches test AP
0.3715 +/- 0.1054 and gated K90 1,985.0 +/- 95.1. However, random labeling has
a much better residual-only K90 of 8,287 than the actively biased variants.
This negative result confirms that positive mining and high AP alone do not
guarantee a good complete-pool ranking.

### Dual-anchor diagnostic

The sampling-bias finding motivated a two-model score diagnostic without
changing either GCN:

- a representative random-label model supplies `p_first`;
- the actively trained model supplies the stronger conditional `p_second`;
- mean and geometric-mean `p_second` fusions are also evaluated;
- standalone methods count their own query masks;
- dual methods count the exact union of both masks after mapping through local
  subset source indices.

Mean fusion has the best mean validation S1 AP and is the frozen recommendation
for a new-seed confirmation. Across the existing five test diagnostics:

| Metric | Active alone | Validation-selected mean fusion |
|---|---:|---:|
| training oracle labels | 61,973 | 118,034.6 |
| oracle fraction | 5.00% | 9.52% |
| gated path-prob K90 | 1,891.2 | 1,901.0 |
| gated path-prob K95 | 3,569.4 | 3,122.4 |
| gated path-prob K99 | 21,806.2 | 11,544.8 |
| residual-only path-prob K90 | 19,556.0 | 8,578.4 |

The fusion recovers much of the representative model's residual ranking while
retaining the active model's conditional discrimination. It still misses the
full-label K99 of 4,305 and residual K90 of 2,521. Random standalone is also
slightly better at K99 (11,351.8), so this is not a universal win.

The diagnostic code was developed during a stage that inspected the frozen
test truth. Therefore mean fusion is only a recommendation to freeze and
confirm on independent operating scenarios, not a new formal test claim.

### Gate 1 decision

Gate 1 does **not** pass:

- label use is within the 10% ceiling;
- overall gated K90 is not materially worse;
- mean validation AP is below 95% of the full-label value;
- K95/K99 and residual-only retrieval remain materially worse.

The next core experiment must record or estimate randomized query propensities
and train a debiased representative loss, or retain a stronger passive anchor
model for residual ranking. It must compare against random labeling at equal
oracle cost.

## 15. Phase 3: Multi-Fidelity Feedback Search

### 15.1 Literature-driven hypotheses

Phase 3 tested three ideas without changing `PaperStyleRts79Gcn`:

1. propensity-recorded active sampling, motivated by UPAL and LURE-style
   unbiased risk estimation;
2. DC/LODF low-fidelity pretraining, motivated by multi-fidelity power-flow
   learning;
3. cached ordered-prefix expansion with a small physical-feedback probe set,
   motivated by Markovian tree search and line-status dictionaries.

Every high-fidelity training label and every online N-2 probe is counted. A
low-fidelity DCOPF or LODF calculation is reported separately and is never
called cascade ground truth.

### 15.2 Propensity correction result

The active learner records a non-zero proposal probability for every queried
candidate and implements levelled unbiased risk weights. Five paired 5% runs
gave the following results:

| Training rule | Test AP | Gated K90 | Gated K99 |
|---|---:|---:|---:|
| Phase-2 active, unweighted | 0.5579 | 1,891.2 | 21,806.2 |
| propensity sampled, unweighted | 0.4285 | 1,954.0 | 14,099.6 |
| pure LURE correction | 0.3602 | 2,046.6 | 12,066.6 |
| 25% LURE blend | 0.4129 | 1,945.4 | 13,416.4 |
| entropy LURE | 0.3344 | 1,985.2 | 11,492.0 |

The correction is statistically better founded than the Phase-2 prior
heuristic, but it did not improve this overparameterized GCN. This is a
published negative-result pattern for deep active learning and is retained as
an ablation, not promoted as the core method.

### 15.3 Low-fidelity pretraining result

A label-free builder computes DC/LODF next-outage proxies for 1,480,080
candidate positions over 8,000 pre-existing states. Incremental proxy-target
construction requires 80 base DCOPF calls and no new high-fidelity N-1 or N-2
cascade calls. The source NPZ already contains S0/S1 states and branch flows,
so this count does not reclaim their historical physical construction cost.
The DC model includes all nine IEEE118 non-unity transformer taps and matches
PYPOWER `makePTDF/makeLODF` on finite reference entries.
Pretraining the unchanged GCN on the per-state top-5% proxy target and then
fine-tuning on 5% high-fidelity active labels gave:

- test AP `0.5617 +/- 0.0163`;
- S1 test AP `0.4927 +/- 0.0119`, versus `0.4713` without pretraining;
- exact-N1-gated K90 `1,842.2`;
- exact-N1-gated K99 `21,148.2`.

Low fidelity improves the S1 conditional representation and K90, but it does
not repair the high-recall tail by itself. Direct S1 proxy AP is only 0.0573,
so the proxy must not replace the physical cascade oracle.

### 15.4 Label-free N-1 proxy and validation-frozen policy

An iterative LODF relay proxy was selected using eight validation operating
scenarios. Its inputs contain no high-fidelity outcome fields. On deployment
seed `20260708`, post-selection truth audit gives N-1 AP `0.5673` for ten
N-1-critical lines. Validation selected:

- primary second-line gate: 26 lines, the median K needed for 90% validation
  N-1 recall;
- conservative gate: 76 lines, the maximum K needed for 90% validation N-1
  recall;
- feedback rule: five N-2 probes per gated second line and promotion after one
  positive probe.

The feedback rule was selected by worst-scenario validation recall before
cost. Mean validation gate recall is 0.9801 and worst-scenario recall is
0.9307. These figures cover 108,410 labels from fully labeled validation S1
states. That subset covers 39.38% of all first-line candidates on average, so
the figures are not global IEEE118 recall. No frozen-test outcome is used to
choose the rule.

### 15.5 Main adaptive-prefix result

The main method combines:

1. cheap DC/LODF pretraining;
2. 61,973 high-fidelity labels, exactly 5% of the available training pool;
3. 130 online N-2 feedback probes;
4. on-demand S1 construction with an ordered-prefix cache;
5. fallback to the unchanged original GCN ranking.

| Method | Training HF labels | Critical K90 | K95 | K99 | Total physical K90 |
|---|---:|---:|---:|---:|---:|
| full-label GCN + exact N-1 gate | 1,239,452 | 1,793.0 | 2,263.0 | 4,305.0 | 1,979.0 |
| no gate, 5% multi-fidelity GCN | 61,973 | 25,231.6 | 27,701.2 | 31,084.2 | 25,407.6 |
| static proxy gate-26 | 61,973 | 4,529.2 | 5,450.8 | 19,109.0 | 4,699.8 |
| adaptive feedback gate-26 | 61,973 | **1,897.0** | 3,608.8 | 19,039.6 | **2,073.0** |
| adaptive Phase-2 model control | 61,973 | 1,918.8 | 3,877.4 | 21,167.8 | 2,094.8 |
| adaptive random-label control | 61,973 | 1,952.4 | 4,158.0 | 11,193.4 | 2,128.4 |
| adaptive multi-fidelity + random anchor | 118,075.0 | 1,918.2 | 3,678.2 | **11,320.2** | 2,094.2 |

The primary result queries 95% fewer retrospective high-fidelity training
labels. Complete model-selection/calibration validation adds 141,119 labels;
the 108,410 policy-selection labels are a subset of those validation labels.
Unique development-data cost is therefore 203,092 versus 1,380,571 for the
full-label reference, an 85.29% reduction. The 17,532 held-out graph labels
and 32,560 full-truth path rows are audit-only and excluded from development
cost. Its N-2 K90 is 5.80% above the
full-label ceiling, and its total K90 physical cost is 4.75% above the
full-label exact-gate cost. Relative to no gate it reduces K90 by 92.48%;
relative to a static low-fidelity gate it reduces K90 by 58.12%.

The representative random anchor is a separate tail-oriented operating point.
It cuts K99 by 7,719.4 candidates relative to the primary method, at the cost
of 21.2 extra K90 candidates and roughly twice the queried training labels. It is
not reported as a universal improvement.

### 15.6 What the N-1 cost statement means

The adaptive method does not run an exhaustive exact N-1 criticality prescreen
before ranking. It constructs and caches S1 states only when an ordered prefix
is reached. Nevertheless, promoted second lines span all 176 valid first-line
states by K90, so the audit reports:

- ranked N-2 candidate verifications at K90: `1,897.0`;
- cached S1 constructions at K90: `176`;
- total physical operations under this accounting: `2,073.0`.

For a PPT-style search count, use the first number and display the S1 cost next
to it. Do not silently subtract S1 construction from total physical cost.

### 15.7 Decision gates

- Gate 1 remains failed because K95/K99 and validation AP do not match the
  full-label baseline, even though K90 and label cost are favorable.
- Gate 2 remains open because Phase 3 replays already generated hidden labels.
  It demonstrates the query policy but does not reclaim historical simulation
  cost.
- No real-grid, IEEE300, ACTIVSg2000, N-3, or N-4 scalability claim is made.

## 16. Current Boundary and Next Experiment

Phase 1, Phase 2, and the retrospective Phase-3 ablations are complete. The
next valid experiment is a prospective simulator callback on new operating
scenarios:

1. build only label-free S0 and low-fidelity proxy data;
2. request high-fidelity N-2 outcomes only when selected by the frozen policy;
3. cache each stabilized S1 and longer prefix once;
4. evaluate on independent load/topology scenarios;
5. then extend the same budgeted tree search to sampled N-3/N-4 paths.

The target for the next gate is to retain the present K90 gain while reducing
the K95/K99 gap with validation-selected tail anchoring or risk-controlled
fallback. Until that prospective experiment passes, this is an IEEE118
retrospective study, not evidence of deployment on a real utility grid.
# Latest controlled extension

The groupwise-supervision experiment and its prospective results are documented
in [ieee118_groupwise_listwise_gcn.md](ieee118_groupwise_listwise_gcn.md).
It reallocates the existing tail-label budget to nearly complete S1 candidate
lists, keeps `PaperStyleRts79Gcn` unchanged, and adds an optional deployment
budget reserve for the learned fallback. The Smooth-AP ablation was not selected
by validation and remains a recorded negative result.

The next frozen-baseline extension is documented in
[ieee118_pair_interaction_gcn.md](ieee118_pair_interaction_gcn.md). It keeps
`PaperStyleRts79Gcn` unchanged and adds a small, leakage-free relation head for
the active first outage and candidate second outage. Simple calibration,
candidate-only features, and checkpoint probability blending are retained as
negative controls.
