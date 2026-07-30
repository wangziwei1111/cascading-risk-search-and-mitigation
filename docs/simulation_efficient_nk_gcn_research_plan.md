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

## 14. Current Boundary

Phase 1 code and one same-budget smoke comparison are complete. Existing full
truth is used only as a hidden retrospective oracle. The next valid claim
requires at least five acquisition seeds over the planned label budgets,
followed by a prospective builder that invokes the physical simulator only for
selected candidates. No current result is a final real-grid or N-k deployment
result.
