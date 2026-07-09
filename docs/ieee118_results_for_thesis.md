# IEEE118 Results for Thesis Defense

## One-Page Comparison

| Method | K=1000 hits | K=5000 hits | Nature | Main-text result? |
|---|---:|---:|---|---|
| random | 55.4 | 272.9 | stochastic baseline | yes, baseline |
| line_order | 56 | 275 | weak deterministic baseline | yes, baseline |
| LODF_yP | 58 | 275 | physical baseline | yes, baseline |
| PFW | 66 | 265 | physical baseline | yes, baseline |
| Algorithm1 | 62 | unavailable | original method completed, current pilot weak | appendix / caveated |
| strict_path_prob | 360 | 1185 | paper-aligned pilot score | yes, caveated as pilot-2000 |
| second_only | 661 | 1705 | diagnostic ablation | diagnostic only |
| best_alpha_path_prob | 661 | 1710 | calibrated ranking improvement | optional diagnostic |
| any_critical_fragility_path_prob | 673 | 1706 | degenerate-label diagnostic | appendix only |
| best_strict_fragility_path_prob | 676 | 1709 | strict fragility refinement | optional diagnostic |

## Why IEEE118 Is Not as Dramatic as RTS-79

IEEE118 is harder because the early-stop valid N-2 universe removes first-step direct-shed lines from the second-step search. As a result, the S0 probability `p_shed(Li|S0)` is not a clean measure of whether line `Li` pushes the system into a fragile S1 state. Many IEEE118 critical paths are low-p_first / high-p_second paths, especially relay-cascade paths. Multiplying by `p_first` therefore suppresses many useful paths. This is why strict path probability still beats random and physical baselines, but does not reproduce the very dramatic RTS-79 search curve.

## Thesis Contribution

The IEEE118 extension contributes a larger, stress-calibrated ordered N-2 benchmark with a formal first-step critical early-stop protocol, a paper-aligned RTS-79 GCN reuse pipeline, and a detailed diagnosis of why the original path-probability score behaves differently on IEEE118. The work shows that the original paper-style score is useful but bottlenecked by S0 probability, and it identifies calibrated ranking and strict first-line fragility targets as reasonable IEEE118-specific diagnostic refinements.

## Limitations

The current formal IEEE118 training result is pilot-2000 rather than paper-8000. Algorithm 1 has been completed but is not yet strong under the current pilot model. The any-critical first-line fragility label is all-positive and cannot support a discriminative classifier. Strict fragility targets fix that label degeneracy, but only slightly improve some budgets and do not decisively dominate best alpha. None of these diagnostic variants should be described as the original paper main method.

## Future Work

Future work should train the full paper-8000 IEEE118 model, generate multi-seed first-line fragility truth tables, evaluate Algorithm 1 with the fully trained multi-state model, and compare original path probability, alpha calibration, strict fragility, second-only ablations, random, line_order, PFW, and LODF_yP under the same fixed and percentage search budgets.

