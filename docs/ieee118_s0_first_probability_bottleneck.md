# IEEE118 S0 First-Probability Bottleneck Diagnostics

This diagnostic explains why the PR #14 pilot-2000 strict paper-style score

```text
path_prob(Li -> Lj) = p_shed(Li | S0) * p_shed(Lj | S1(i))
```

is weaker than the `second_only` ablation on IEEE118. This is a diagnostic stage only: it does not change OPA, full-truth generation, first-step critical early-stop, Step2/Paper-aligned datasets, `PaperStyleRts79Gcn`, Algorithm 1, or the ranking formulas.

## Inputs

The diagnostic reads PR #14 pilot-2000 local artifacts:

- full truth: `results/gcn_search/ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708/ieee118_fulltruth_summary.csv`
- path index: `results/gcn_search/ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop/ieee118_rts79_gcn_path_index.csv`
- S1 dataset NPZ: local only
- pilot-2000 model checkpoint: local only
- pilot-2000 feature normalizer
- pilot-2000 first-step probabilities
- pilot-2000 search summary and top-K outputs

The script computes a full local score table but does not commit it.

## Main Result

Pilot-2000 is already much stronger than random, LODF_yP, PFW, and line order, but `second_only` is still stronger than strict `path_prob`:

| method | K=1000 critical hits | K=1000 recall | K=1000 precision |
| --- | ---: | ---: | ---: |
| random | 60.0 | 0.034208 | 0.060 |
| line_order | 56 | 0.031927 | 0.056 |
| LODF_yP | 58 | 0.033067 | 0.058 |
| PFW | 66 | 0.037628 | 0.066 |
| path_prob | 360 | 0.205245 | 0.360 |
| second_only ablation | 661 | 0.376853 | 0.661 |

The gap is not a model-structure bug. It is a target-semantics mismatch created by the early-stop protocol and the strict path-product score.

## Suppressed Critical Paths

The diagnostic defines suppressed critical paths as critical paths that rank highly by `second_only` but are pushed far back by `path_prob`:

- Class A: `critical=True`, `second_only_rank <= 1000`, `path_prob_rank > 5000`
- Class B: `critical=True`, `second_only_rank <= 5000`, `path_prob_rank > 10000`

Results:

- Class A suppressed critical paths: 180
- Class B suppressed critical paths: 203
- Union: 313

These paths have the expected low-`p_first`, high-`p_second` signature.

At K=1000:

- overlap between path_prob and second_only top-K: 249
- path_prob-only critical hits: 199
- second_only-only critical hits: 500
- path_prob-only mean `p_first`: 0.570718
- second_only-only mean `p_first`: 0.027451
- path_prob-only mean `p_second`: 0.588608
- second_only-only mean `p_second`: 0.992166

At K=5000:

- overlap: 3,094
- path_prob-only critical hits: 18
- second_only-only critical hits: 538
- path_prob-only mean `p_first`: 0.496476
- second_only-only mean `p_first`: 0.007573
- path_prob-only mean `p_second`: 0.097319
- second_only-only mean `p_second`: 0.611104

This confirms that `second_only` finds many high-risk second-step states whose first outage has very low direct S0 load-shed probability.

## Concentration By First Line

Suppressed paths are concentrated in a small set of first lines. The top examples are:

| first_line | suppressed critical | suppressed relay | mean p_first | mean p_second | mean rank_gap | relay ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| L088 | 11 | 10 | 0.000232 | 0.831845 | 18354.36 | 0.909 |
| L122 | 11 | 11 | 0.001770 | 0.861449 | 10255.64 | 1.000 |
| L095 | 10 | 10 | 0.000008 | 0.890667 | 28033.20 | 1.000 |
| L084 | 10 | 10 | 0.000419 | 0.870326 | 15981.90 | 1.000 |
| L087 | 10 | 10 | 0.000423 | 0.886040 | 15927.50 | 1.000 |

The suppressed set is mostly relay-cascade-driven.

## Mechanism Comparison

| mechanism | paths | critical | mean p_first | mean p_second | path_prob top1000 hits | second_only top1000 hits | suppressed | suppressed ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| noncritical | 30,806 | 0 | 0.115716 | 0.092082 | 0 | 0 | 0 | 0.000000 |
| relay_cascade | 1,643 | 1,643 | 0.117134 | 0.820607 | 341 | 645 | 312 | 0.189897 |
| island_only | 111 | 111 | 0.169310 | 0.583385 | 19 | 16 | 1 | 0.009009 |

Relay-cascade paths are much more likely to be suppressed by low `p_first` than island-only paths.

## Early-Stop Consequence

First-step critical early-stop changes the semantics of valid ordered N-2 rows:

- total first lines: 186
- first-step critical lines: 10
- valid N-2 first lines: 176
- valid N-2 paths: 32,560
- valid N-2 paths with first-step positive S0 label: 0
- valid N-2 paths with first-step negative S0 label: 32,560
- mean `p_first` for valid N-2 first lines: 0.115970
- mean `p_first` for first-step critical lines: 0.647452

After early-stop, all valid ordered N-2 paths exclude first lines that already shed load in S0. Therefore the S0 label learned by `p_shed(Li | S0)` is mostly a direct N-1 load-shed probability, not a measure of whether `Li` creates a fragile post-contingency state.

This explains why strict path product can suppress valid high-risk N-2 paths: many dangerous first outages are not directly load-shedding in S0, but they create S1 states in which several second outages are highly dangerous.

## Interpretation For The Paper

Recommended wording:

> Under first-step critical early-stop, valid ordered N-2 paths exclude first outages that already cause direct load shedding. Consequently, the first factor in the strict path-product score, `p_shed(Li | S0)`, estimates direct N-1 load-shed risk rather than the ability of `Li` to move the system into a fragile S1 state. In IEEE118, many relay-cascade critical paths exhibit low `p_shed(Li | S0)` but high `p_shed(Lj | S1(i))`, so the strict product suppresses them. The second-step-only ablation therefore performs strongly, indicating that IEEE118 N-2 risk is more dependent on post-first-outage state fragility than on first-outage direct shedding probability.

This should be presented as a mechanism-level diagnostic, not as a bug. `path_prob` remains the strict paper-aligned method; `second_only` is an ablation that reveals a mismatch between direct S0 load-shed probability and S0 fragility.

## Outputs

Committed compact outputs:

- `suppressed_critical_paths_top.csv`
- `first_line_s0_suppression_summary.csv`
- `s0_probability_distribution_summary.csv`
- `s0_label_conflict_summary.csv`
- `path_prob_vs_second_only_overlap.csv`
- `mechanism_s0_bottleneck_summary.csv`
- `s0_first_probability_bottleneck_diagnostics.json`
- `s0_first_probability_bottleneck_readme.md`

Local-only output:

- `s0_bottleneck_full_score_table_local_only.csv`

No raw full truth, Step2 CSV, NPZ dataset, model checkpoint, full predictions, or Simulink/MATLAB artifact is committed.
