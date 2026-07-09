# IEEE118 Alpha Path-Probability Sweep

This stage is a low-cost ranking sweep on top of the PR #14/#15 IEEE118 pilot-2000 paper-aligned GCN outputs. It does not retrain `PaperStyleRts79Gcn`, rerun OPA, change the first-step early-stop rule, or modify Algorithm 1.

## Motivation

PR #15 showed that the strict paper-aligned score

`path_prob(Li -> Lj) = p_first(Li | S0) * p_second(Lj | S1(i))`

can suppress many critical IEEE118 ordered N-2 paths after first-step critical early-stop. In the early-stop dataset, valid N-2 rows have no first-step-positive S0 label by construction, so `p_first` is a direct N-1 load-shed probability rather than a clean measure of first-line fragility. The alpha sweep tests whether softening the first-step multiplier improves ranking while preserving the original model outputs.

## Scoring Rule

The swept ranking score is:

`score_alpha(Li -> Lj) = (epsilon + p_first(Li | S0))^alpha * p_second(Lj | S1(i))`

Special cases:

- `alpha=1, epsilon=0`: strict paper-aligned path probability.
- `alpha=0`: exactly `second_only`, independent of `epsilon`.
- `0 < alpha < 1`: treats `p_first` as a soft prior rather than a hard multiplicative gate.

The sweep used `alpha = {0, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0}` and `epsilon = {0, 1e-6, 1e-4, 1e-3, 1e-2}` on 32,560 valid early-stop ordered N-2 paths.

## Key Results

At K=1000, the best alpha setting is `alpha_path_prob_a0_eps0`, which is exactly the `second_only` ablation:

| method | critical hits | recall critical | precision | relay hits | recall relay |
|---|---:|---:|---:|---:|---:|
| random | 55.4 | 0.0316 | 0.0554 | 52.7 | 0.0321 |
| line_order | 56 | 0.0319 | 0.0560 | 56 | 0.0341 |
| LODF_yP | 58 | 0.0331 | 0.0580 | 49 | 0.0298 |
| PFW | 66 | 0.0376 | 0.0660 | 41 | 0.0250 |
| strict_path_prob | 360 | 0.2052 | 0.3600 | 341 | 0.2075 |
| second_only / alpha0 | 661 | 0.3769 | 0.6610 | 645 | 0.3926 |

At K=5000, the best recall setting is `alpha_path_prob_a025_eps1em2`:

| method | critical hits | recall critical | precision | relay hits | recall relay |
|---|---:|---:|---:|---:|---:|
| random | 272.9 | 0.1556 | 0.0546 | 255.3 | 0.1554 |
| line_order | 281 | 0.1602 | 0.0562 | 258 | 0.1570 |
| LODF_yP | 275 | 0.1568 | 0.0550 | 248 | 0.1509 |
| PFW | 265 | 0.1511 | 0.0530 | 229 | 0.1394 |
| strict_path_prob | 1185 | 0.6756 | 0.2370 | 1099 | 0.6689 |
| second_only / alpha0 | 1705 | 0.9721 | 0.3410 | 1621 | 0.9866 |
| alpha=0.25, epsilon=1e-2 | 1710 | 0.9749 | 0.3420 | 1624 | 0.9884 |

Thus the best alpha is below 1.0, and strict multiplication by `p_first` is not the best ranking rule for this early-stop IEEE118 dataset.

## Interpretation

The sweep supports the PR #15 diagnosis: `p_first` should not be used as a hard multiplicative gate after first-step critical early-stop. For small budgets, the best result is second-step-only scoring; for a larger K=5000 budget, a very soft `p_first` prior (`alpha=0.25`, `epsilon=1e-2`) slightly improves over pure second-only.

This is a ranking improvement experiment, not the original paper main method. The strict `path_prob` result should still be reported as the paper-aligned baseline, and `second_only` / alpha-softened variants should be described as diagnostics or candidate improvements.

## Artifacts

Outputs are compact and live under:

`results/gcn_search/ieee118_paper_aligned_training_scaleup/alpha_path_prob_sweep/`

Generated files:

- `alpha_path_prob_sweep_summary.csv/json`
- `alpha_path_prob_sweep_curve_points_sparse.csv`
- `alpha_path_prob_sweep_topk_paths.csv`
- `alpha_path_prob_sweep_best_configs.csv`
- `alpha_path_prob_sweep_config.json`
- `alpha_path_prob_vs_baselines_at_keyK.csv`
- `alpha_path_prob_heatmap_data.csv`
- `alpha_path_prob_sweep_readme.md`

The local full score table remains local-only and is not committed:

`results/gcn_search/ieee118_paper_aligned_training_scaleup/s0_bottleneck_diagnostics/s0_bottleneck_full_score_table_local_only.csv`

## Next Step

The natural next method change is not more alpha tuning, but a dedicated first-line fragility target: a score estimating whether `Li` creates a dangerous post-first-outage state `S1(i)`, rather than whether `Li` directly sheds load at `S0`.
