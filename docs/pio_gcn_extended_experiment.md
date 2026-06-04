# PIO-GCN PathRank Extended Full-Truth Experiment

## Purpose

This document records the next-stage shortcoming fix for RTS-79 full-truth evaluation scale. It extends the previous 3-seed RTS-79 full-truth preliminary result to 5 full-truth seeds. This is still a preliminary RTS-79 result, not a final paper-scale conclusion.

## Configuration

```text
output_dir = results/gcn_search/pio_extended_fulltruth_5seed
test_seed_start = 20260722
test_num_seeds = 5
top_k = 20, 50, 100, 200
run_full_truth = true
system = IEEE RTS-79 / 24-bus RTS
```

The requested 10-seed setting was not run in this round to control runtime. The completed setting uses 5 full-truth seeds, which satisfies the minimum requested scale.

## Strong Paper Baseline

The paper-feature `GCN_path_prob` baseline was retrained with a stronger Step2-state setting:

```text
output_dir = results/gcn_search/paper_baseline_strong
feature_mode = paper
training_num_scenarios attempted = 20
training_num_scenarios completed = 6
training_epochs = 5
training_max_active_depth = 1
candidate_line_filter_mode = high_flow_top_n
max_first_lines = 10
```

The 20-scenario run was stopped after exceeding the interactive runtime budget; 6 scenarios were completed and used. This remains a limited strong-baseline attempt and should not be described as a fully tuned paper baseline.

## Strong Paper Baseline v2

A second stronger paper-feature attempt was launched with 10 requested training scenarios:

```text
output_dir = results/gcn_search/paper_baseline_strong_v2
feature_mode = paper
training_num_scenarios attempted = 10
training_num_scenarios completed = 7
training_epochs = 5
training_max_active_depth = 1
candidate_line_filter_mode = high_flow_top_n
max_first_lines = 10
```

The interactive run timed out after 7 completed scenario checkpoints. The v2 model was trained on those 7 completed scenarios and is therefore still a partial baseline, not a fully tuned baseline.

## Key Results

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 | Notes |
|---|---:|---:|---:|---:|---|
| PIO_GCN_Top20/50/100/200 | 0.211 | 0.338 | 0.423 | 0.521 | Physics-enhanced features model |
| paper_GCN_path_prob_strong | 0.176 | 0.254 | 0.350 | 0.568 | Stronger paper-feature baseline, limited to 6 training scenarios |
| paper_GCN_path_prob_strong_v2 | 0.176 | 0.244 | 0.330 | 0.565 | Stronger paper-feature baseline v2, limited to 7 training scenarios |
| LODF_yP | 0.036 | 0.134 | 0.207 | 0.329 | Physical-rule baseline |
| random | 0.007 | 0.026 | 0.069 | 0.156 | Random baseline |
| line_order | 0.007 | 0.025 | 0.060 | 0.134 | Line-number order |
| oracle | 0.356 | 0.890 | 1.000 | 1.000 | Upper bound only |

## Interpretation

- PIO-GCN PathRank still clearly outperforms LODF_yP at Top-20/50/100/200.
- PIO-GCN PathRank outperforms the stronger paper-feature baseline at Top-20/50/100.
- The stronger paper-feature baseline is better at Top-200 in this 5-seed result.
- The v2 paper-feature baseline keeps the same Top-200 pattern, but it does not improve Top-20/50/100 over v1.

## Ensemble and Rerank Follow-Up

The Top-200 tradeoff was followed by two improvement checks:

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.211 | 0.338 | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.176 | 0.254 | 0.350 | 0.568 |
| ensemble_alpha_0.75 | 0.200 | 0.345 | 0.444 | 0.549 |
| rerank_physical_stress | 0.280 | 0.439 | 0.532 | 0.587 |

Simple ensemble does not fully solve the Top-200 issue. The hard-negative-aware rerank result is stronger: it improves Top-100 and Top-200 in this preliminary 5-seed check.

## Learned Path Reranker Follow-Up

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| rerank_physical_stress | 0.280 | 0.439 | 0.532 | 0.587 |
| learned_logistic_reranker | 0.322 | 0.566 | 0.792 | 0.954 |
| learned_mlp_reranker | 0.333 | 0.698 | 0.944 | 0.997 |

The learned MLP reranker is the strongest current result and exceeds the requested Top-100/Top-200 targets. Because it uses only 5 RTS-79 seeds, it should be described as a strong preliminary indication rather than a final result.

Leakage audit update: strict held-out validation still gives learned MLP recall@100 about 0.940 and recall@200 about 0.993. No forbidden feature was found, but the result remains a preliminary RTS-79 finding because path labels repeat across operating-condition seeds.
- This means the earlier weak paper baseline limitation was real; the paper-feature baseline becomes more competitive when trained more fairly.
- The current conclusion should be softened: physics-enhanced features are useful, but they are not the only competitive route, especially when evaluating deeper Top-K lists.

## Output Files

```text
results/gcn_search/pio_extended_fulltruth_5seed/config.json
results/gcn_search/pio_extended_fulltruth_5seed/per_seed_fulltruth_summary.csv
results/gcn_search/pio_extended_fulltruth_5seed/pio_topk_per_seed_summary.csv
results/gcn_search/pio_extended_fulltruth_5seed/baseline_per_seed_summary.csv
results/gcn_search/pio_extended_fulltruth_5seed/aggregate_topk_summary.csv
results/gcn_search/pio_extended_fulltruth_5seed/aggregate_method_comparison.csv
results/gcn_search/pio_extended_fulltruth_5seed/diagnostics/per_seed_variability.csv
results/gcn_search/pio_extended_fulltruth_5seed/diagnostics/worst_seed_summary.csv
results/gcn_search/pio_extended_fulltruth_5seed/diagnostics/best_seed_summary.csv
```

Full-truth detail files and seed-level simulation details are kept local and should not be tracked in Git.
