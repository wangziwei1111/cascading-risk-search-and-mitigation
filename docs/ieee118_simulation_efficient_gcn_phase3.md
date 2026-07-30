# IEEE118 Simulation-Efficient GCN Phase 3

## Scope

This phase asks whether IEEE118 critical ordered N-2 paths can be retrieved
with far fewer high-fidelity training labels and without an upfront exhaustive
exact N-1 criticality screen.

The experiment keeps the original RTS-79 model unchanged:

- model file: `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`;
- model class: `PaperStyleRts79Gcn`;
- formal test setting: IEEE118 `flow_scaled=8.00`, `min_rate_a=1.0`;
- frozen deployment seed: `20260708`;
- valid early-stop ordered N-2 paths: 32,560;
- critical paths: 1,754;
- relay-cascade paths: 1,643.

This is a retrospective experiment. Existing labels are hidden and revealed
through an oracle callback, but their historical generation cost has already
been paid.

## Research Chain

### 1. Reproduced baseline

The full-label IEEE118 reuse of `PaperStyleRts79Gcn` is the performance ceiling:

| Metric | Result |
|---|---:|
| high-fidelity training labels | 1,239,452 |
| test AP | 0.6167 |
| critical K90 | 1,793 |
| critical K95 | 2,263 |
| critical K99 | 4,305 |
| exact N-1 prescreen calls | 186 |
| total physical K90 | 1,979 |

### 2. Baseline gaps

1. The source builder generates nearly every candidate N-2 label for every
   training graph state.
2. The strong K90 result depends on an exact N-1 gate computed before path
   ranking.
3. Active positive mining improves head retrieval but distorts the complete
   candidate-pool tail.
4. Direct DC/LODF ranking does not model relay trips, islands, redispatch, or
   load shedding.
5. A single frozen IEEE118 test scenario cannot support a real-grid claim.

### 3. Core improvement

The core improvement is multi-fidelity active training around the unchanged
GCN:

1. compute label-free DC/LODF candidate severity;
2. pretrain on a per-state top-5% low-fidelity target;
3. fine-tune with 61,973 high-fidelity labels, exactly 5% of the available
   training pool;
4. retain the original class-weighted candidate loss and architecture.

The low-fidelity pool contains 1,480,080 candidate positions over 8,000
pre-existing states. Incremental target construction costs 80 base DCOPF solves
and makes zero new high-fidelity N-1/N-2 cascade calls. The source NPZ already
contains S0/S1 graph states and branch flows, so this count does not reclaim
their historical physical construction cost. The LODF implementation includes
all nine IEEE118 non-unity transformer taps through branch susceptance
`1 / (x * tap)` and is regression-tested against PYPOWER `makePTDF/makeLODF`.

### 4. Application improvement

The application improvement is validation-frozen physical feedback with an
ordered-prefix cache:

1. score second-line families with an iterative LODF relay proxy;
2. retain the top 26 families selected on eight validation scenarios;
3. physically query five N-2 probes per family;
4. promote a family after one observed critical probe;
5. construct each reached S1 state once and cache it;
6. search promoted paths first and then fall back to the unchanged GCN.

The query callback sees an outcome only after selecting that path. Unqueried
full-truth rows are not used by the policy.

Policy selection reads 108,410 N-2 labels from fully labeled validation S1
states. Those labels are a subset of the 141,119 validation labels already
used for model selection and calibration, so they are disclosed separately
but are not double-counted in unique development-data cost. The selected
gate-26 policy has 98.01% mean gate-critical recall and 93.07% worst-scenario
gate-critical recall on that complete subset. The subset covers 39.38% of all
IEEE118 first-line candidates on average, so this is not a global-recall claim.

## Why This Is Not an N-1-Free Method

The method removes the **upfront exhaustive exact N-1 criticality prescreen**.
It does not remove the physical state required to evaluate a selected ordered
N-2 path.

At K90:

- N-2 candidate verifications: 1,897.0;
- unique on-demand S1 state constructions: 176;
- total under the present physical-operation accounting: 2,073.0.

The K value answers, "How many second-outage candidates did the search test?"
The total answers, "How many N-1 state constructions plus N-2 verifications
were physically needed?" Both must be reported.

## System Experiments

### Training ablation at 5% labels

| Experiment | Test AP | S1 AP | Exact-gated K90 | Exact-gated K99 |
|---|---:|---:|---:|---:|
| random labels | 0.3715 | n/a | 1,985.0 | 11,351.8 |
| Phase-2 active | 0.5579 | 0.4713 | 1,891.2 | 21,806.2 |
| pure LURE | 0.3602 | 0.2723 | 2,046.6 | 12,066.6 |
| LURE blend 25% | 0.4129 | 0.3228 | 1,945.4 | 13,416.4 |
| entropy LURE | 0.3344 | 0.2680 | 1,985.2 | 11,492.0 |
| multi-fidelity active | **0.5617** | **0.4927** | **1,842.2** | 21,148.2 |

Pure propensity correction is not the selected method. It increases estimator
correctness but hurts this overparameterized GCN's retrieval performance.

### Search-policy ablation

All adaptive rows below use five probes and one-positive promotion.

| Method | HF labels | K90 | K95 | K99 | Relay K90 | Total physical K90 |
|---|---:|---:|---:|---:|---:|---:|
| full-label GCN + exact N-1 gate | 1,239,452 | 1,793.0 | 2,263.0 | 4,305.0 | n/a | 1,979.0 |
| line order | 0 | 29,277.0 | 30,946.0 | 32,251.0 | n/a | 29,277.0 |
| LODF_yP | 0 | 29,142.0 | 30,773.0 | 32,195.0 | n/a | 29,142.0 |
| random, ten-seed mean | 0 | 29,353.7 | 30,903.2 | 32,174.7 | n/a | 29,353.7 |
| multi-fidelity GCN, no gate | 61,973 | 25,231.6 | 27,701.2 | 31,084.2 | 25,496.0 | 25,407.6 |
| static proxy gate-26 | 61,973 | 4,529.2 | 5,450.8 | 19,109.0 | 4,451.6 | 4,699.8 |
| **adaptive multi-fidelity gate-26** | **61,973** | **1,897.0** | **3,608.8** | 19,039.6 | **1,827.0** | **2,073.0** |
| adaptive Phase-2 active control | 61,973 | 1,918.8 | 3,877.4 | 21,167.8 | 1,827.0 | 2,094.8 |
| adaptive random-label control | 61,973 | 1,952.4 | 4,158.0 | 11,193.4 | 1,827.0 | 2,128.4 |
| adaptive gate-76 sensitivity | 61,973 | 2,254.0 | 3,582.4 | 19,244.8 | 2,244.0 | 2,430.0 |
| adaptive multi-fidelity + random anchor | 118,075.0 | 1,918.2 | 3,678.2 | **11,320.2** | 1,827.0 | 2,094.2 |

### Main conclusion

The primary method queries 95% fewer high-fidelity training labels. It also
uses all 141,119 validation labels for model selection and calibration, so its
unique development-data cost is 203,092 labels versus 1,380,571 for the
full-label reference, an 85.29% reduction. The 17,532 held-out graph labels
and 32,560 formal path-ranking truth rows are used only for retrospective
audit and are not counted as development data. Relative to the full-label
exact-gate ceiling:

- N-2 K90 is 104 candidates higher, a 5.80% increase;
- total physical K90 is 94 operations higher, a 4.75% increase;
- relay-cascade K90 is 1,827 candidates;
- no-gate K90 is reduced by 92.48%;
- static-gate K90 is reduced by 58.12%.

At equal 5% label budget and identical online feedback, low-fidelity
pretraining saves 21.8 K90 candidates over the Phase-2 active model and 55.4
over random-label training.

The result is close to the full-label model at K90, not at K95/K99. The random
anchor cuts K99 by 40.54% relative to the primary method but uses about 9.53%
of training labels and costs 21.2 additional K90 candidates. It is a
tail-oriented sensitivity, not the headline result.

## Reproduction

Build transformer-tap-aware low-fidelity candidate targets:

```bash
python src/gcn_search/ieee118/build_ieee118_dc_lodf_low_fidelity_targets.py \
  --output-dir results/gcn_search/ieee118_simulation_efficient_gcn/phase3_dc_lodf_low_fidelity_all_candidates
```

Train five acquisition seeds with the unchanged original RTS-79 GCN:

```bash
python src/gcn_search/ieee118/run_ieee118_label_efficiency_experiment.py \
  --output-root results/gcn_search/ieee118_simulation_efficient_gcn/phase3_mf_all_candidates_perstate95_e1_w5_curve \
  --acquisition-modes pmf_hybrid_prior_corrected \
  --acquisition-seeds 20260730 20260731 20260732 20260733 20260734 \
  --label-budget-fractions 0.0025 0.005 0.01 0.02 0.05 \
  --low-fidelity-target-npz results/gcn_search/ieee118_simulation_efficient_gcn/phase3_dc_lodf_low_fidelity_all_candidates/ieee118_dc_lodf_low_fidelity_targets.npz \
  --low-fidelity-pretrain-epochs 1 \
  --low-fidelity-target-mode per_state_top_quantile \
  --low-fidelity-upper-quantile 0.95 \
  --low-fidelity-positive-weight 5.0
```

Build the label-free iterative proxy:

```bash
python src/gcn_search/ieee118/evaluate_ieee118_iterative_lodf_n1_proxy.py \
  --output-dir results/gcn_search/ieee118_simulation_efficient_gcn/phase3_iterative_lodf_n1_proxy
```

Select the feedback rule using validation scenarios:

```bash
python src/gcn_search/ieee118/select_ieee118_adaptive_probe_policy.py \
  --output-dir results/gcn_search/ieee118_simulation_efficient_gcn/phase3_adaptive_probe_policy_selection
```

Evaluate the frozen adaptive policy:

```bash
python src/gcn_search/ieee118/evaluate_ieee118_lazy_prefix_search.py \
  --run-root results/gcn_search/ieee118_simulation_efficient_gcn/phase3_mf_all_candidates_perstate95_e1_w5_curve \
  --acquisition-modes pmf_hybrid_prior_corrected \
  --first-prefix-score-mode iterative_lodf_proxy \
  --dc-lodf-prefix-transform rank \
  --second-score-physics-gate-size 26 \
  --adaptive-probes-per-second-line 5 \
  --adaptive-promotion-min-positives 1 \
  --adaptive-target critical \
  --output-dir results/gcn_search/ieee118_simulation_efficient_gcn/phase3_adaptive_probe_gate26_safety_selected
```

Build the compact audit:

```bash
python src/gcn_search/ieee118/summarize_ieee118_simulation_efficient_phase3.py
```

## Compact Outputs

The compact source of truth is:

```text
results/gcn_search/ieee118_simulation_efficient_gcn/phase3_compact_summary/
  ieee118_phase3_method_comparison.csv
  ieee118_phase3_training_ablation.csv
  ieee118_phase3_summary.json
  ieee118_phase3_readme.md
```

Large NPZ datasets, checkpoints, full prediction tables, and raw full-truth
CSVs remain local and must not be committed.

## Limitations and Next Gate

1. The experiment is retrospective and does not reclaim historical label cost.
2. The 95% figure is training-query reduction; total unique development-label
   reduction is 85.29% after complete validation labels are counted.
3. Policy selection uses eight validation scenarios, but its fully labeled S1
   subset covers only 39.38% of all first-line candidates on average and the
   deployment audit uses one frozen test seed.
4. All 176 valid S1 states are eventually constructed by K90.
5. K95 and K99 remain materially worse than the full-label baseline.
6. IEEE118 is a benchmark, not a real utility grid.
7. N-3/N-4 and larger networks have not been validated.

The next experiment must use a prospective simulator callback on independent
operating scenarios, generate only selected high-fidelity labels, and retain
the prefix cache for sampled N-3/N-4 expansion. A real-grid applicability claim
requires operator-grade or actual utility data and separate validation.
