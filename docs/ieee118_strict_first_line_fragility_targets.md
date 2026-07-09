# IEEE118 Strict First-Line Fragility Targets

This note documents the strict first-line fragility target branch for the IEEE118 `flow_scaled=8.00, min_rate_a=1.0` study.

## Scope

PR #17 introduced an `any_critical_fragility_path_prob` score, but the first-line label `valid_n2_any_critical` was degenerate on the evaluated data: every valid first-line state had at least one critical second outage. This branch adds stricter first-line targets so the first-line fragility head has non-trivial positives and negatives.

This branch does not rerun OPA, does not change the first-step critical early-stop rule, does not change Algorithm 1, and does not modify `PaperStyleRts79Gcn`. It only builds stricter labels, trains those labels with the original RTS-79 GCN class, and evaluates the resulting path-probability scores against the existing baselines.

## Target Definitions

For each first-line state, first-step critical lines are excluded from the fragility loss and retained as direct-shed diagnostics. For non-direct first-line states, the following top-quantile labels are built:

- `critical_count_topq`: first lines in the top q fraction by number of critical second outages.
- `relay_count_topq`: first lines in the top q fraction by number of relay-cascade second outages.
- `max_shed_topq`: first lines in the top q fraction by maximum second-step load shed.
- `composite_topq`: first lines in the top q fraction by z-scored critical count, relay count, max shed, and total shed.

The implemented quantiles are `0.10`, `0.20`, and `0.30`.

## Degeneracy Check

The generated compact target summary reports all 12 targets as non-degenerate:

- top 10% targets: 156 positive / 1305 negative, positive ratio 10.6776%.
- top 20% targets: 302 positive / 1159 negative, positive ratio 20.6708%.
- top 30% targets: 448 positive / 1013 negative, positive ratio 30.6639%.
- first-step critical lines excluded from loss: 158.

This fixes the all-positive target issue in the PR #17 any-critical first-line label.

## Data Limitation

The held-out seed `20260708` uses complete full-truth labels, including relay-cascade and load-shed fields. The sampled train/validation S1 data from the pilot paper-aligned dataset stores critical labels but not relay-specific labels or load-shed severity. For sampled train/validation seeds, relay and load-shed strict targets are therefore pilot diagnostics, not final severity labels. A future full multi-seed truth table would be needed for fully faithful relay/load-shed first-line targets.

## Training

The trainer is `src/gcn_search/ieee118/train_ieee118_strict_fragility_gcn.py`. It imports the original RTS-79 symbols and trains `PaperStyleRts79Gcn` on each non-degenerate strict target. It sweeps positive weights `20`, `auto`, `50`, `100`, and `200`; `auto` is computed as `num_negative / num_positive`.

The baseline `positive_weight=20` often overpredicts positives for sparse targets. Auto weights give more balanced predictions, but classification quality is modest overall. Example best validation-AP rows include:

- `max_shed_top30`, auto weight 2.2612: test AP 0.8244, ROC AUC 0.9060.
- `max_shed_top20`, auto weight 3.8377: test AP 0.4374, ROC AUC 0.7679.
- `critical_count_top30`, auto weight 2.2612: test AP 0.3744, ROC AUC 0.5183.
- `critical_count_top10`, auto weight 8.3654: test AP 0.1964, ROC AUC 0.5738.

These metrics should be treated as diagnostic. They are not final IEEE118 GCN tuning results.

## Path-Probability Evaluation

Strict first-line probabilities are evaluated as:

```text
strict_fragility_path_prob = q_strict_fragile(first_line) * p_second(second_line | S1)
```

The evaluator also retains the existing baselines: random, line order where available through the prior summaries, PFW, LODF_yP, strict path probability, second-only, best alpha path probability, and PR #17 any-critical fragility path probability.

Key compact comparison against existing baselines:

| K | best strict target | strict hits | relay hits | best alpha hits | second-only hits | any-critical fragility hits |
|---:|---|---:|---:|---:|---:|---:|
| 100 | `critical_count_top30` | 95 | 89 | 94 | 94 | 87 |
| 500 | `critical_count_top30` | 469 | 461 | 469 | 469 | 372 |
| 1000 | `relay_count_top10` | 676 | 660 | 661 | 661 | 673 |
| 5000 | `critical_count_top10` | 1709 | 1622 | 1710 | 1705 | 1706 |

The strict target improves some low-budget comparisons slightly, especially at `K=100` and `K=1000`, but it does not clearly dominate the best alpha path probability across all budgets. This should be reported as a diagnostic refinement, not as a main method breakthrough.

## Compact Artifacts

Target artifacts:

- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_targets/ieee118_strict_fragility_target_metadata.json`
- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_targets/ieee118_strict_fragility_target_summary.csv`
- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_targets/ieee118_strict_fragility_line_stats_compact.csv`
- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_targets/ieee118_strict_fragility_metrics_summary.csv`
- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_targets/ieee118_strict_fragility_weight_sweep_summary.csv`

Evaluation artifacts:

- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_eval/ieee118_strict_fragility_path_prob_summary.csv`
- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_eval/ieee118_strict_fragility_vs_baselines_at_keyK.csv`
- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_eval/ieee118_strict_fragility_best_configs.csv`
- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_eval/ieee118_strict_fragility_heatmap_data.csv`
- `results/gcn_search/ieee118_paper_aligned_training_scaleup/strict_fragility_eval/strict_first_line_fragility_diagnostics.csv`

Local-only regenerated outputs:

- `ieee118_strict_fragility_targets_dataset.npz`
- strict fragility `.pt` checkpoints
- `ieee118_strict_fragility_probabilities_compact.csv`
- pretty JSON mirrors of large CSV summaries
- full score table, full predictions, raw full-truth CSV, and full Step2-State CSV

These local-only files must not be committed.
