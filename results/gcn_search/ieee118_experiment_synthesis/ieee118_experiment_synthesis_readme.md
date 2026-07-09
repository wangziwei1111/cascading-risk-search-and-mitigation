# IEEE118 Experiment Synthesis

This directory is a compact synthesis of PR #11 through PR #18. It does not rerun OPA, retrain GCNs, modify Algorithm 1, or generate new large artifacts.

## Key Search Rows

| method                          |    K |   critical_hits |   precision | caveat                                              |
|:--------------------------------|-----:|----------------:|------------:|:----------------------------------------------------|
| second_only                     | 1000 |             661 |      0.661  | strong ablation; not original main method           |
| strict_path_prob                | 1000 |             360 |      0.36   | original paper-style path probability on pilot-2000 |
| best_alpha_path_prob            | 1000 |             661 |      0.661  | calibrated ranking; not original paper method       |
| best_strict_fragility_path_prob | 1000 |             676 |      0.676  | slight low-budget gains, not decisive breakthrough  |
| second_only                     | 5000 |            1705 |      0.341  | strong ablation; not original main method           |
| strict_path_prob                | 5000 |            1185 |      0.237  | original paper-style path probability on pilot-2000 |
| best_alpha_path_prob            | 5000 |            1710 |      0.342  | calibrated ranking; not original paper method       |
| best_strict_fragility_path_prob | 5000 |            1709 |      0.3418 | slight low-budget gains, not decisive breakthrough  |

## Positioning

- PR #11 is the formal early-stop protocol.
- PR #14 is the current closest paper-aligned pilot training result, but it is not paper-8000.
- PR #15 explains the S0 first-probability bottleneck.
- PR #16 and PR #18 are calibrated/diagnostic improvements, not original-paper replacements.
- PR #17 is a useful negative result because the any-critical label is all-positive.

Large local-only files such as raw full-truth CSVs, Step2-State CSVs, NPZ datasets, model checkpoints, full predictions, and Simulink/MATLAB artifacts are intentionally excluded.
