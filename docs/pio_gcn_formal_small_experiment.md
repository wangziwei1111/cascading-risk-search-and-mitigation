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

## Fifth-Round 3-Seed Preliminary Formal Experiment

The fifth round improves the experiment credibility and repository maintainability.

Key changes:

- Large intermediate files already tracked by Git were removed from Git tracking with `git rm --cached`.
- Step2-State generation now supports candidate first-line filtering.
- A 3-seed full-truth preliminary formal experiment was completed.
- Diagnostics were added for found and missed Top-100 critical paths.

Completed configuration:

```text
training_num_scenarios = 10
training_epochs = 5
training_max_active_depth = 1
candidate_line_filter_mode = high_flow_top_n
max_first_lines = 10
test_seed_start = 20260722
test_num_seeds = 3
top_k = 20, 50, 100
full_truth = true
```

Training data:

```text
num_states = 110
num_candidate_labels = 4080
reachable_positive_ratio = 0.1047
```

3-seed Top-K result:

```text
PIO_GCN_Top20: mean recall = 0.2160
PIO_GCN_Top50: mean recall = 0.3427
PIO_GCN_Top100: mean recall = 0.4213
```

Baseline comparison:

```text
PIO_GCN_Top100: mean_found_after_100 = 23.3333
LODF_yP: mean_found_after_100 = 11.6667
original_GCN_path_prob: mean_found_after_100 = 8.0
random: mean_found_after_100 = 3.0
line_order: mean_found_after_100 = 3.6667
oracle: mean_found_after_100 = 55.3333
```

This is now suitable for an advisor progress report as a preliminary RTS-79 full-truth result. It is still not a final performance claim because:

- the training set is filtered to high-flow Top-10 first outages;
- the model remains weak, with high coverage but many false positives;
- the experiment has only 3 test seeds.

## Sixth-Round Formal Preliminary Ablation

The sixth round answers the question: where does the PIO-GCN improvement come from?

Output directory:

```text
results/gcn_search/pio_formal_ablation_3seed/
```

The ablation reuses the fifth-round 3-seed full truth:

```text
test seeds = 20260722, 20260723, 20260724
full truth = true
top_k = 20, 50, 100
```

### Ablation Results

| method | physics feature | candidate mask | physics loss | mean found@100 | mean recall@100 |
|---|---:|---:|---:|---:|---:|
| physics_ce_no_mask | yes | no | no | 23.3333 | 0.4209 |
| physics_ce_mask | yes | yes | no | 23.3333 | 0.4209 |
| physics_loss_no_mask | yes | no | yes | 23.3333 | 0.4213 |
| physics_loss_mask | yes | yes | yes | 23.3333 | 0.4213 |
| paper_gcn_path_prob | no, paper 4-feature | no | no | 8.0 | 0.1435 |
| LODF_yP | physical rule | no | no | 11.6667 | 0.2099 |
| random | no | no | no | 3.0 | 0.0548 |
| line_order | no | no | no | 3.6667 | 0.0657 |
| oracle | upper bound | upper bound | upper bound | 55.3333 | 1.0 |

### Interpretation

The largest contribution currently comes from the physics feature representation, not from the physics-informed loss.

Evidence:

```text
paper_gcn_path_prob recall@100 = 0.1435
physics_ce_no_mask recall@100 = 0.4209
```

The candidate mask does not visibly change this run:

```text
physics_ce_no_mask recall@100 = 0.4209
physics_ce_mask recall@100 = 0.4209
```

The physics-informed loss gives only a very small Top-100 change and slightly worse Top-20/Top-50 behavior:

```text
physics_ce_mask recall@20/50/100 = 0.2216 / 0.3488 / 0.4209
physics_loss_mask recall@20/50/100 = 0.2160 / 0.3427 / 0.4213
```

Therefore, the current honest conclusion is:

```text
PIO-GCN's current improvement mainly comes from using richer physics features.
The candidate mask has little effect in this particular ordered-path construction.
The current physics loss is not yet a major performance driver and needs further tuning.
```

Diagnostics:

```text
results/gcn_search/pio_formal_ablation_3seed/diagnostics/per_method_score_distribution.csv
results/gcn_search/pio_formal_ablation_3seed/diagnostics/per_method_top100_missed_critical.csv
results/gcn_search/pio_formal_ablation_3seed/diagnostics/per_method_top100_found_critical.csv
results/gcn_search/pio_formal_ablation_3seed/diagnostics/per_method_rank_of_critical_paths.csv
```

## Seventh-Round Rank-Loss Physics-Informed Training

The seventh round adds a reachable pairwise ranking loss. The goal is not just to classify whether a branch can reach load shedding, but to rank reachable critical branches ahead of noncritical branches inside the same state.

### Why the original physics loss contributed little

The previous physics-informed loss mostly constrained invalid candidates, relay-priority behavior, and loading monotonicity. These constraints help physical consistency, but they do not directly optimize the ordered path ranking objective. As a result, the sixth-round ablation showed:

```text
physics_ce_mask recall@100 = 0.4209
physics_loss_mask recall@100 = 0.4213
```

This was only a tiny Top-100 difference and did not improve Top-20 or Top-50.

### Rank-loss definition

For each state, positive candidates are branches with `y_reachable = 1`; negative candidates are branches with `y_reachable = 0`. The ranking loss encourages:

```text
p_positive >= p_negative + margin
```

The preliminary run used:

```text
lambda_rank = 0.2
rank_margin = 0.05
rank_max_pairs = 512
```

### Rank-loss results

Output directory:

```text
results/gcn_search/pio_rank_loss_preliminary_3seed/
```

| method | found@20 | found@50 | found@100 | recall@20 | recall@50 | recall@100 |
|---|---:|---:|---:|---:|---:|---:|
| physics_ce_mask | 12.3333 | 19.3333 | 23.3333 | 0.2216 | 0.3488 | 0.4209 |
| physics_loss_mask | 12.0 | 19.0 | 23.3333 | 0.2160 | 0.3427 | 0.4213 |
| physics_rank_loss_mask | 12.3333 | 19.3333 | 24.0 | 0.2216 | 0.3488 | 0.4337 |
| LODF_yP | 2.0 | 8.0 | 11.6667 | 0.0362 | 0.1443 | 0.2099 |
| paper_gcn_path_prob | 5.6667 | 7.0 | 8.0 | 0.1012 | 0.1250 | 0.1435 |
| oracle | 20.0 | 50.0 | 55.3333 | 0.3624 | 0.9060 | 1.0 |

### Interpretation

Rank-loss gives a small but concrete Top-100 improvement:

```text
CE mask found@100 = 23.3333
Rank-loss mask found@100 = 24.0
```

It does not improve Top-20 or Top-50 in this preliminary run:

```text
CE mask found@20/50 = 12.3333 / 19.3333
Rank-loss mask found@20/50 = 12.3333 / 19.3333
```

Training diagnostics indicate that rank-loss increases positive-negative score separation:

```text
mean_positive_score = 0.8054
mean_negative_score = 0.6920
positive_negative_score_gap = 0.1135
```

This is still a 3-seed preliminary RTS-79 result, not a final large-scale conclusion.
# Round-8 Unified Conclusion

The formal preliminary result should now be read with the following consistent interpretation:

- The main observed improvement comes from physics-enhanced features.
- PIO-GCN reaches about 42% Top-100 recall on 3 RTS-79 full-truth preliminary seeds.
- LODF_yP is about 21% Top-100 recall.
- The weak paper-feature `GCN_path_prob` baseline is about 14% Top-100 recall.
- Candidate mask and original physics loss do not materially change the current 3-seed result.
- Rank-loss does not improve Top-20/Top-50; its small Top-100 increase is not yet a robust contribution.
- The experiment is still RTS-79 3-seed preliminary, not a final performance claim.
- The measured-state path is a JSON interface, not a real SCADA/PMU connection.
