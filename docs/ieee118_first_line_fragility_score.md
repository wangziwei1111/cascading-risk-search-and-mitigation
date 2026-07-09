# IEEE118 First-Line Fragility Score

This stage tests a first-line fragility score for IEEE118 after the PR #15 S0 bottleneck diagnosis and the PR #16 alpha path-probability sweep. It does not modify OPA, full-truth generation, first-step critical early-stop, Algorithm 1, or the GCN architecture.

## Why Strict `p_first` Is Not Enough

The strict paper-aligned path probability is:

`score(Li -> Lj) = p_shed(Li | S0) * p_shed(Lj | S1(i))`

PR #15 showed that after first-step critical early-stop, `p_shed(Li | S0)` estimates whether `Li` directly causes load shedding as a single first outage. It does not directly estimate whether `Li` creates a fragile post-first-outage state with dangerous second-outage candidates.

PR #16 softened this first-step multiplier with an alpha sweep. This PR goes one step further and trains a separate first-line fragility target.

## Label Definition

For each first line `Li` in an S0 state:

- if `Li` is first-step critical, it is excluded from the fragility loss mask and recorded separately as `first_step_direct_shed_label = 1`;
- if `Li` is not first-step critical and at least one valid ordered N-2 path `Li -> Lj` is critical, then `y_fragile(Li) = 1`;
- otherwise `y_fragile(Li) = 0`.

This target asks whether `Li` creates an S1 state that has at least one critical second outage. It is different from the first-step direct load-shed label.

## Model

The fragility model reuses the original RTS-79 `PaperStyleRts79Gcn` from:

`src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`

The input is the S0 graph feature tensor. The output is one fragility probability per line:

`q_fragile(Li | S0)`

No new GCN architecture is introduced.

## Data Source

The builder uses existing PR #14 pilot-2000 paper-aligned artifacts:

- S0 graph features from `ieee118_paper_gcn_dataset.npz`;
- sampled S1 labels when a unique first line can be inferred from `current_outage_labels`;
- complete held-out seed `20260708` full-truth labels when the local fulltruth/path-index files are available.

No OPA rerun is performed.

Important limitation: with the current `valid_n2_any_critical` definition, the available labels are degenerate in this run:

- known first-line labels: 1,461
- positive fragility labels: 1,461
- negative fragility labels: 0
- positive ratio: 1.0

For held-out seed `20260708`, all 176 non-first-step-critical first lines have at least one critical second outage. This means the classification metrics are not meaningful evidence of discrimination; they mostly confirm the label construction. A future label should be stricter, for example using top-risk thresholds, load-shed severity, relay-cascade count, or a count/rank target rather than `any critical`.

## Classification Metrics

The main `positive_weight=20` run completed with `PaperStyleRts79Gcn`, but because there are no negative labels, metrics are degenerate:

- overall precision/recall/F1: 1.0
- average precision: 1.0
- ROC AUC: not defined
- positive prediction rate at 0.5: 1.0
- positive prediction rate at 0.8: 1.0

These numbers should not be reported as proof that the model learned a discriminative fragility concept.

## Ranking Evaluation

The evaluated fragility ranking is:

`fragility_path_prob(Li -> Lj) = q_fragile(Li | S0) * p_shed(Lj | S1(i))`

It is compared against:

- `strict_path_prob`
- `second_only`
- `best_alpha_path_prob`
- `random`
- `LODF_yP`
- `PFW`

At K=1000:

| method | critical hits | recall critical | precision | relay hits |
|---|---:|---:|---:|---:|
| random | 55.4 | 0.0316 | 0.0554 | 52.7 |
| LODF_yP | 58 | 0.0331 | 0.0580 | 49 |
| PFW | 66 | 0.0376 | 0.0660 | 41 |
| strict_path_prob | 360 | 0.2052 | 0.3600 | 341 |
| best_alpha_path_prob | 661 | 0.3769 | 0.6610 | 645 |
| second_only | 661 | 0.3769 | 0.6610 | 645 |
| fragility_path_prob | 673 | 0.3837 | 0.6730 | 656 |

At K=5000:

| method | critical hits | recall critical | precision | relay hits |
|---|---:|---:|---:|---:|
| random | 272.9 | 0.1556 | 0.0546 | 255.3 |
| LODF_yP | 275 | 0.1568 | 0.0550 | 248 |
| PFW | 265 | 0.1511 | 0.0530 | 229 |
| strict_path_prob | 1185 | 0.6756 | 0.2370 | 1099 |
| second_only | 1705 | 0.9721 | 0.3410 | 1621 |
| fragility_path_prob | 1706 | 0.9726 | 0.3412 | 1621 |
| best_alpha_path_prob | 1710 | 0.9749 | 0.3420 | 1624 |

The fragility ranking improves over strict path_prob and physical baselines. It is very close to second_only and does not beat the best alpha path-probability setting at K=5000. The small K=1000 improvement over second_only is likely due to learned score variation among otherwise all-positive first-line labels, not a clean positive/negative fragility classifier.

## Low-`p_first` / High-`p_second` and Relay Cascades

At K=1000, fragility_path_prob captures 427 low-`p_first` / high-`p_second` critical paths, compared with 418 for second_only and 0 for strict path_prob. Relay-cascade hits also increase from 341 under strict path_prob to 656 under fragility_path_prob.

## Paper Positioning

This method can be described as an IEEE118 improvement direction motivated by the S0 bottleneck:

> To mitigate the mismatch between first-step direct shedding probability and second-step fragility under first-step early-stop, we construct a first-line fragility target indicating whether a first outage creates an S1 state containing at least one valid critical second outage. The score is learned with the original RTS-79 `PaperStyleRts79Gcn` architecture and evaluated as a replacement for the first factor in path probability ranking.

However, the current `any critical` label is degenerate on IEEE118 flow_scaled=8.00. It should not be presented as a final discriminative GCN result. A stricter fragility label is needed before claiming a robust new method.

## Artifacts

Dataset/training compact outputs:

`results/gcn_search/ieee118_paper_aligned_training_scaleup/first_line_fragility/`

Evaluation compact outputs:

`results/gcn_search/ieee118_paper_aligned_training_scaleup/first_line_fragility_eval/`

Local-only files not committed:

- `ieee118_first_line_fragility_dataset.npz`
- `ieee118_first_line_fragility_model.pt`
- full predictions CSVs
- raw fulltruth CSVs
- Step2-State CSVs
