# PIO-GCN Formal Small Experiment

This document records the fourth-round RTS-79 PIO-GCN formal-small experiment.

## Experiment Level

This run is a preliminary light formal experiment.

It uses full ordered N-2 truth for the test seed, so the Top-K recall values are formal for that seed. However, the training and test scale is still small, so the numbers should be reported as preliminary RTS-79 small-system results, not large-scale system conclusions.

## Configuration

```text
training_num_scenarios = 5
training_first_seed = 20260750
training_epochs = 3
training_max_active_depth = 0
test_seed_start = 20260722
test_num_seeds = 1
top_k = 20, 50, 100
beta = 1.2
security_limit = 1.0
full_truth = true
```

The originally requested heavier settings were attempted but did not finish in the current interactive runtime window:

```text
50 scenarios, 10 epochs, 5 test seeds
20 scenarios, 5 epochs, 3 test seeds
20 scenarios, 5 epochs, 1 test seed
```

The final completed run therefore uses a lighter training configuration and one full-truth test seed.

## Training Data

```text
feature_mode = physics
num_features = 9
num_states = 6
num_candidate_labels = 228
num_reachable_positive = 140
reachable_positive_ratio = 0.6140
```

Important consistency rule:

```text
model input uses normalized features
physics loss uses raw physical features
```

## Baselines

The comparison table includes:

- `PIO_GCN_Top20`, `PIO_GCN_Top50`, `PIO_GCN_Top100`: model ranking plus Top-K physical simulation.
- `original_GCN_path_prob`: original paper-style path probability baseline using the available weak paper-feature model.
- `LODF_yP`: physical-rule ranking baseline.
- `random`: fixed random-seed baseline.
- `line_order`: line-number order baseline.
- `oracle`: upper bound only, not a deployable method.

## Main Results

Output directory:

```text
results/gcn_search/pio_formal_small_experiment/
```

For the test seed, the full truth contains:

```text
total_critical_paths = 55
```

Aggregate Top-K result:

```text
PIO_GCN_Top20: critical_found = 1, recall = 0.0182
PIO_GCN_Top50: critical_found = 3, recall = 0.0545
PIO_GCN_Top100: critical_found = 7, recall = 0.1273
```

Baseline highlights:

```text
original_GCN_path_prob: found_after_100 = 10, attempts_to_find_all = 1401
LODF_yP: found_after_100 = 11, attempts_to_find_all = 1148
random: found_after_100 = 4, attempts_to_find_all = 1381
line_order: found_after_100 = 3, attempts_to_find_all = 1400
oracle: found_after_100 = 55, attempts_to_find_all = 55
```

## Figures

```text
results/gcn_search/pio_formal_small_experiment/figures/topk_recall_bar.png
results/gcn_search/pio_formal_small_experiment/figures/found_after_k_comparison.png
results/gcn_search/pio_formal_small_experiment/figures/runtime_comparison.png
```

## What Can Be Reported

It is reasonable to report:

- The RTS-79 improved OPA simulator and from-case simulation interface are working.
- Full ordered N-2 truth can be generated for at least a formal-small test seed.
- PIO-GCN Top-K and fair baselines now share the same full-truth definition.
- The repository now produces reportable summary tables and figures.

It is not yet reasonable to claim:

- Final PIO-GCN performance superiority.
- Large-scale generalization.
- Stable multi-seed statistics.

## Next Step

The next engineering step is to speed up dataset generation and full-truth evaluation, then rerun with:

```text
training_num_scenarios = 50
training_epochs = 10
test_num_seeds = 5
training_max_active_depth = 1
```
