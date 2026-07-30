# Simulation-Efficient N-k GCN Literature Review

## Research Question

How can the current cascading-failure GCN find rare critical N-k paths without
first generating an exhaustive high-fidelity N-k training table, while keeping
a physical simulator in the loop for safety-critical decisions?

This review uses primary papers only. The proposed method at the end is a
cascade-specific synthesis of the cited ideas. It is not presented as an
already-published algorithm.

## 1. Reproduced Baseline

### Liu et al.: GCN-guided cascading-failure search

- Paper: [Searching for Critical Power System Cascading Failures With Graph
  Convolutional Network](https://doi.org/10.1109/TCNS.2021.3063333)
- Preprint: [arXiv:2001.11553](https://arxiv.org/abs/2001.11553)
- Repository implementation:
  `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`
- Model class: `PaperStyleRts79Gcn`

The paper maps transmission branches to line-graph nodes, uses two polynomial
graph-convolution layers, and predicts one vulnerability label per branch. It
then orders physical cascade-search attempts with the predicted vulnerability.
The paper generated 8,000 RTS-79 training states and 50,000 Henan-grid training
states.

The current IEEE118 paper-aligned dataset contains:

- 8,000 graph states;
- 1,398,103 active high-fidelity labels after N-1 residual masking;
- 22,045 positive labels;
- 1,239,452 training labels.

The main cost is therefore not GCN inference. It is the nested physical oracle
used to label almost every candidate next outage for every training state.

## 2. Literature That Directly Addresses the Cost

### Zhang et al.: active learning for expensive simulation labels

- Paper: [A power system transient stability assessment method based on active
  learning](https://doi.org/10.1049/tje2.12068)

The paper first creates inexpensive short-time simulations, labels only a
subset with expensive long-time simulations, and repeatedly queries unlabeled
samples with high information entropy. This directly supports replacing
exhaustive cascade labeling with an active physical-oracle loop.

Gap relative to this project:

- it studies transient-stability classification, not ordered cascading paths;
- it uses a random forest, not a topology-aware GCN;
- entropy-only batches can contain redundant candidates;
- it does not exploit LODF/DC low-fidelity physics or rare-positive targeting.

### Yang et al.: multi-fidelity contingency learning

- Paper: [Multi-fidelity power flow solver](https://arxiv.org/abs/2205.13362)

The method trains a low-fidelity network on DC power-flow data and couples it
to a residual high-fidelity network trained with scarce high-fidelity data. It
tests N-k contingencies on IEEE118 and reports that low-fidelity data can
substitute for a large fraction of high-fidelity power-flow labels.

Gap relative to this project:

- the target is post-contingency power flow, not relay propagation, island
  shedding, redispatch shedding, or ordered-path criticality;
- it does not decide which expensive cascade labels should be queried next;
- it does not provide a simulator-abstention policy for deployment.

### Gal et al., Sener and Savarese, and BADGE: uncertainty plus diversity

- [Deep Bayesian Active Learning with Image Data](https://arxiv.org/abs/1703.02910)
- [Active Learning for Convolutional Neural Networks: A Core-Set
  Approach](https://arxiv.org/abs/1708.00489)
- [Deep Batch Active Learning by Diverse, Uncertain Gradient Lower
  Bounds](https://arxiv.org/abs/1906.03671)

These papers establish complementary acquisition principles:

- epistemic uncertainty identifies samples the model does not understand;
- core-set selection prevents a small labeled set from covering only one
  region of feature space;
- BADGE combines uncertain and diverse batch selection.

Gap relative to this project:

- none of these methods encodes power-system severity;
- generic class accuracy is not enough for rare critical-path retrieval;
- they do not count high-fidelity cascade simulations as the primary budget.

### Active-learning sampling bias and unbiased risk

- [Importance Weighted Active
  Learning](https://arxiv.org/abs/0812.4952) uses importance weighting to
  correct the sampling bias introduced by adaptive label queries.
- [Optimal sampling in unbiased active
  learning](https://proceedings.mlr.press/v108/imberg20a.html) shows that
  uncertainty-proportional sampling can be suboptimal and can lose to random
  sampling on some tasks.
- [Asymptotic optimality for active learning
  processes](https://proceedings.mlr.press/v180/zhan22a.html) analyzes
  sampling bias and dataset shift in active learning and combines
  generalization error with an importance-weighted training loss.
- [Margin-based sampling in high
  dimensions](https://proceedings.mlr.press/v202/tifrea23a.html) gives
  theoretical and empirical settings where active sampling is less efficient
  than passive random labeling.

These results are directly relevant to rare cascading-path labels. A query
policy may discover many positives yet train on a distribution unlike the
complete candidate pool. Random-label sampling is therefore a required
baseline, and a representative random component or principled query-propensity
correction is part of the proposed method rather than an optional convenience.

The Phase-2 queried-label prior correction in this repository is only a
label-prior adjustment estimated from an initial random anchor set. It is not
the rigorous per-query importance weighting of IWAL and must not be described
as such.

## 3. Physics and Topology Generalization

### Narimani et al.: graph and LODF N-x screening

- Paper: [Generalized Contingency Analysis Based on Graph Theory and Line
  Outage Distribution Factor](https://arxiv.org/abs/2007.07009)

The method combines group betweenness centrality and LODF to rank influential
component groups. It supplies an inexpensive physics-based severity prior for
initial sampling and active-query tie breaking.

Gap relative to this project:

- LODF is a linearized proxy;
- it cannot by itself reproduce protection trips, island handling, redispatch,
  or load-shed mechanisms;
- it should be used as low fidelity, not as high-fidelity ground truth.

### Liu et al.: Markov search and line-status dictionary

- Paper: [Fast Power System Cascading Failure Path Searching with High Wind
  Power Penetration](https://arxiv.org/abs/1911.09848)

This work treats cascade evolution as a Markov search and caches repeated
DCPF/DCOPF results in a line-status dictionary. It supports state caching and
best-first expansion for N-k paths instead of repeatedly simulating identical
prefixes.

Gap relative to this project:

- it accelerates individual simulations but still needs a search policy;
- dictionary growth can itself become large for high k;
- it does not learn uncertainty or control missed-critical-path risk.

### LEAP and topology-aware contingency models

- [LEAP nets for power grid perturbations](https://arxiv.org/abs/1908.08314)
- [Topology-Aware Neural Networks for Fast Contingency Analysis of Power
  Systems](https://arxiv.org/abs/2310.04213)
- [Topology-aware Graph Neural Networks for Learning Feasible and Adaptive
  AC-OPF Solutions](https://arxiv.org/abs/2205.10129)

These papers show that explicit line-status/topology conditioning and
physics-aware regularization improve transfer to unseen topologies and N-k
configurations. LEAP also evaluates transfer on historical French-grid data.

Gap relative to this project:

- their main targets are flows, setpoints, or OPF feasibility;
- they do not model the complete ordered OPA-style cascade outcome;
- fast surrogate inference alone does not solve expensive high-fidelity label
  generation or safe abstention.

## 4. Safety-Critical Screening

### Christianson et al.: reliable N-k screening

- Paper: [Fast and Reliable N-k Contingency Screening with Input-Convex Neural
  Networks](https://arxiv.org/abs/2410.00796)

This paper emphasizes that false negatives are the operationally dangerous
failure mode and develops a DC-contingency classifier with a certifiable
zero-false-negative property. It is an important reliability baseline, even
though its ICNN model and static DC-feasibility target differ from this
project's GCN cascade target.

### Angelopoulos et al. and Xu et al.: risk-controlled selective prediction

- [Conformal Risk Control](https://arxiv.org/abs/2208.02814)
- [Active, anytime-valid risk controlling prediction
  sets](https://arxiv.org/abs/2406.10490)

Conformal risk control calibrates a model-dependent selection rule to control a
monotone loss such as false-negative proportion under its statistical
assumptions. The active, anytime-valid extension addresses adaptively queried
labels and explicit label budgets.

Gap relative to this project:

- exchangeability or the stated sequential assumptions must be audited under
  load and topology shift;
- calibration does not make an incorrect physical surrogate correct;
- out-of-distribution operation still needs drift detection, recalibration,
  and a physical fallback.

## 5. Real-Scale Evaluation References

- [A Physics-Informed Graph Neural Network Framework for N-2 Contingency
  Screening: A Real-World Texas Grid
  Study](https://doi.org/10.1109/OAJPE.2025.3626699) reports a physics-informed
  N-2 GNN study on a large operational network and motivates near-real-time
  screening.
- [ACTIVSg2000](https://electricgrids.engr.tamu.edu/electric-grid-test-cases/activsg2000/)
  is a public 2,000-bus synthetic Texas-footprint case with several engineering
  data formats. It must be described as synthetic, not as the actual ERCOT
  network.

## 6. Evidence-Based Design Decision

The most useful first improvement is not a deeper GCN. It is a
**Physics-Guided Multi-Fidelity Batch Active GCN**:

1. retain the current graph-state representation and GCN baseline;
2. compute cheap DC/LODF/topological severity for the unlabeled path pool;
3. query a small, diverse, uncertain, physics-stratified batch;
4. run the high-fidelity cascade simulator only for that batch;
5. update the sparse loss mask and retrain;
6. stop when retrieval performance per oracle call plateaus.

The application improvement is **Risk-Controlled Selective Verification**:

1. calibrate a candidate set for a target missed-critical-path risk;
2. prioritize high-risk candidates;
3. route uncertain or shifted cases to the physical simulator;
4. update calibration and the active learner with newly observed labels.

The papers support the individual ingredients. Whether their cascade-specific
combination reduces oracle calls without sacrificing rare-path recall is the
hypothesis that the systematic experiments must test.

## 7. Phase-3 Literature Reproduction and Gap Audit

Phase 3 implements literature-derived components as controlled ablations. It
does not claim to reproduce each paper's complete task, because the final
target here is OPA-style ordered cascade criticality rather than generic
classification or static power-flow feasibility.

### 7.1 Probabilistic active learning and unbiased risk

- [UPAL](https://proceedings.mlr.press/v22/ganti12.html) motivates randomized
  uncertainty sampling with non-zero support over the pool and an unbiased
  risk estimator.
- [On Statistical Bias in Active Learning](https://openreview.net/forum?id=JiYq3eqTKY)
  develops levelled unbiased risk estimation and reports that bias correction
  may be ineffective or harmful for overparameterized neural networks.

Repository reproduction:

- every sampled candidate records its conditional proposal probability;
- the queried loss can use levelled unbiased risk weights;
- pure, blended, entropy, and unweighted controls use five paired seeds and
  identical 5% high-fidelity budgets.

Observed gap:

- pure correction lowers mean test AP from 0.5579 for the Phase-2 active model
  to 0.3602 and worsens K90 from 1,891.2 to 2,046.6;
- the effective weighted sample fraction is 0.5697;
- unweighted and blended propensity samples improve over pure correction but
  still do not beat the Phase-2 active model at K90.

This negative result is consistent with the cited deep-network caveat. It
means that a formally corrected loss is not automatically a better retrieval
model for this rare-path task.

### 7.2 DC/LODF multi-fidelity transfer

The [multi-fidelity power-flow solver](https://arxiv.org/abs/2205.13362) couples
DC low-fidelity data with scarce high-fidelity data and evaluates N-k
contingencies on IEEE118. The repository adapts only this fidelity principle:

1. run base DCOPF and compute LODF-based next-outage severity;
2. create a label-free per-state proxy target;
3. pretrain the unchanged `PaperStyleRts79Gcn`;
4. fine-tune on the same 5% high-fidelity queried labels.

The present retrospective builder reads pre-existing S0/S1 graph states and
branch flows. Its zero additional cascade-call count applies to proxy-target
construction only and does not erase the source states' historical physical
cost. IEEE118's nine non-unity transformer taps are included in branch
susceptance, and the finite LODF entries are regression-tested against
PYPOWER `makePTDF/makeLODF`.

The adaptation improves S1 AP from 0.4713 to 0.4927 and exact-gated K90 from
1,891.2 to 1,842.2. Its exact-gated K99 remains poor at 21,148.2. Direct proxy
AP is only 0.0573,
confirming the literature gap: a DC power-flow surrogate does not encode
relay propagation, islands, redispatch, or load shedding.

### 7.3 Markovian tree search and state dictionaries

[Risk Assessment of Multi-timescale Cascading Outages based on Markovian Tree
Search](https://arxiv.org/abs/1603.03935) uses risk-guided tree expansion to
avoid duplicated prefix simulations. [Fast Power System Cascading Failure
Path Searching with High Wind Power
Penetration](https://arxiv.org/abs/1911.09848) adds a line-status dictionary for
repeated DCPF/DCOPF calculations.

Repository adaptation:

- a stabilized first-outage prefix is keyed and constructed once;
- the low-fidelity gate chooses second-line families to probe;
- five real N-2 feedback outcomes per gated second line decide promotion;
- unpromoted paths fall back to the unchanged GCN ranking;
- N-2 verification and S1 construction costs are recorded separately.

This is the application-oriented improvement. It removes the requirement for
an upfront exhaustive exact N-1 criticality screen, but it does not make S1
physics free: all 176 valid S1 states have been reached and cached by K90 in
the current test scenario.

### 7.4 Safety-first selection versus formal guarantees

[Fast and Reliable N-k Contingency Screening with Input-Convex Neural
Networks](https://arxiv.org/abs/2410.00796) motivates prioritizing false
negative control. Its guarantee is for a different DC-feasibility target and
cannot be transferred to OPA-style cascading outcomes.

The repository therefore uses a weaker, explicit claim:

- select probe count and promotion threshold only on eight validation
  scenarios;
- sort feasible rules by worst-scenario gate recall, then mean recall, then
  estimated physical cost;
- audit but do not tune on deployment seed `20260708`.

The selected rule has mean validation gate recall 0.9801 and minimum recall
0.9307 on 108,410 labels from fully labeled validation S1 states. That subset
covers 39.38% of all first-line candidates on average. These are subset-level
empirical statistics, not global IEEE118 recall or a zero-false-negative
certificate. The labels are a subset of the 141,119 validation labels already
used for model selection and calibration, so they are disclosed but not
double-counted.

## 8. Core and Application Improvements After Experimentation

The evidence-supported method is now more specific than the initial proposal.

### Core improvement

**Multi-fidelity active pretraining with an unchanged GCN**:

- use cheap DC/LODF targets to initialize topology and loading representations;
- fine-tune on 5% physics-stratified high-fidelity labels;
- preserve a random-label model as an optional representative tail anchor;
- do not use pure LURE correction as the primary training objective.

### Application improvement

**Validation-frozen feedback prefix search**:

- rank second-line families with a label-free iterative LODF proxy;
- query a small number of physical N-2 outcomes;
- expand only families with observed positives;
- construct and cache S1 states on demand;
- fall back to the original GCN over the remaining candidates.

At K90 this method needs 1,897.0 N-2 candidate evaluations on average, versus
1,793 for the full-label model with an exact N-1 gate. Including 176 cached S1
states gives 2,073.0 physical operations versus 1,979 for the full-label
baseline. The head of the curve is close; K95/K99 are not.

The 5% label statement applies to queried training labels. Counting complete
validation/model-selection data, the method uses 203,092 unique development
labels versus 1,380,571 for the full-label reference, an 85.29% reduction.

## 9. Remaining Literature Gap

The next contribution cannot be another retrospective ranking tweak. It must
connect the frozen query policy to the real cascade callback on unseen
operating scenarios and show that unqueried labels are never generated.

For N-3/N-4, the natural next experiment combines the implemented prefix cache
with sampled Markovian tree expansion. Nonlocal or sequence-aware cascade GNNs
may later be compared, but they must be treated as new model ablations rather
than silently replacing the reproduced RTS-79 architecture.
