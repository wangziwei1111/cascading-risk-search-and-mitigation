# PIO-GCN Reproduction Commands

Run commands from:

```text
C:\Users\24186\Documents\New project 7\cascading-risk-search-and-mitigation
```

Use the project virtual environment:

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" <command>
```

## Unit Tests

Purpose: check simulator consistency, feature generation, candidate mask/original physics loss logic, JSON measured-state interface handling, and pairwise rank-loss behavior.

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" -m pytest tests/test_cascade_from_case_consistency.py tests/test_measured_state_sanity.py tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_gcn_ranking_loss.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py
```

Output: pytest console result.

Recommended for review: yes.

## Dataset Generation

Purpose: generate Step2-state training data with physics-enhanced features.

Smoke:

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/generate_rts79_step2_state_dataset.py --feature-mode physics --num-scenarios 1 --output-dir results/gcn_search/pio_validation_round8_smoke/physics_dataset
```

Recommended:

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/generate_rts79_step2_state_dataset.py --feature-mode physics --num-scenarios 10 --max-active-depth 1 --candidate-line-filter-mode high_flow_top_n --max-first-lines 10 --output-dir results/gcn_search/pio_formal_preliminary_3seed/training/physics_dataset
```

Output: dataset `.npz` kept local, feature normalizer JSON, dataset stats JSON, sample summary CSV.

## Physics-Informed Training

Purpose: train the physics-enhanced feature GCN. Model input uses normalized features; original physics loss uses raw physical features.

Smoke:

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/train_rts79_physics_gcn.py --dataset-npz results/gcn_search/pio_formal_preliminary_3seed/training/physics_dataset/rts79_step2_state_dataset_physics.npz --epochs 1 --output-dir results/gcn_search/pio_validation_round8_smoke/physics_train
```

Recommended:

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/train_rts79_physics_gcn.py --dataset-npz results/gcn_search/pio_formal_preliminary_3seed/training/physics_dataset/rts79_step2_state_dataset_physics.npz --epochs 5 --lambda-mask 0.1 --lambda-relay 0.1 --lambda-monotonic 0.1 --output-dir results/gcn_search/pio_formal_preliminary_3seed/training/physics_informed
```

Output: model `.pt` kept local, metrics CSV, epoch log CSV, train config JSON.

## 3-Seed Preliminary Formal Experiment

Purpose: reproduce the main 3-seed full-truth preliminary result.

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/run_pio_gcn_formal_small_experiment.py --output-dir results/gcn_search/pio_formal_preliminary_3seed --test-seed-start 20260722 --test-num-seeds 3 --top-k 20 50 100
```

Output: aggregate summaries, method comparison, figures, training metrics.

Runtime: slower than smoke because it uses full ordered N-2 truth for 3 seeds.

## Formal Ablation

Purpose: compare physics-enhanced features, candidate mask, original physics loss, paper GCN, LODF_yP, random, line order, and oracle.

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/run_pio_gcn_formal_ablation.py --output-dir results/gcn_search/pio_formal_ablation_3seed --base-experiment-dir results/gcn_search/pio_formal_preliminary_3seed --top-k 20 50 100
```

Output: `ablation_aggregate_summary.csv`, `ablation_method_comparison.csv`, compact diagnostics, figures.

## Pairwise Rank-Loss Experiment

Purpose: test whether pairwise rank-loss improves Top-K sorting.

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/run_pio_gcn_rank_loss_experiment.py --output-dir results/gcn_search/pio_rank_loss_preliminary_3seed --base-experiment-dir results/gcn_search/pio_formal_preliminary_3seed --lambda-rank 0.2 --rank-margin 0.05 --rank-max-pairs 512
```

Output: `aggregate_method_comparison.csv`, `rank_loss_training_metrics.csv`, diagnostics summary, figures.

## Synthetic Renewable Preliminary

Purpose: run the synthetic renewable perturbation full-truth preliminary experiment. This is a synthetic RTS-79 operating-point perturbation only.

Recommended:

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/run_pio_gcn_renewable_preliminary_experiment.py --output-dir results/gcn_search/pio_renewable_preliminary --renewable-penetration-ratio 0.30 --fluctuation-low 0.60 --fluctuation-high 1.10 --test-seed-start 20260722 --test-num-seeds 3 --top-k 20 50 100 200
```

Output: `aggregate_method_comparison.csv`, `renewable_case_summary.csv`, compact diagnostics, and figures.

## Top-K Depth Tradeoff

Purpose: compare shallow Top-K and deeper Top-K behavior for PIO-GCN PathRank and stronger paper-feature baselines.

Recommended:

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/analyze_topk_depth_tradeoff.py --output-dir results/gcn_search/pio_topk_depth_tradeoff --extended-dir results/gcn_search/pio_extended_fulltruth_5seed
```

Output: `topk_depth_tradeoff_summary.csv`, `recall_gain_by_k.csv`, recommendations, and figures.

## Score-Level Ensemble Ranking

Purpose: combine regenerated PIO-GCN path scores and paper-GCN path scores.

Recommended:

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/evaluate_pio_gcn_ensemble_ranking.py --output-dir results/gcn_search/pio_ensemble_preliminary --extended-dir results/gcn_search/pio_extended_fulltruth_5seed --top-k 20 50 100 200 --alphas 0.25 0.50 0.75
```

Output: `ensemble_method_comparison.csv`, `ensemble_topk_summary.csv`, compact diagnostics, and figures.

## Hard-Negative-Aware Rerank

Purpose: rerank the top 300 PIO-GCN candidates with PIO score, LODF score, loading stress, and relay risk.

Recommended:

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" src/gcn_search/legacy_rts79/evaluate_pio_gcn_hard_negative_rerank.py --output-dir results/gcn_search/pio_rerank_preliminary --extended-dir results/gcn_search/pio_extended_fulltruth_5seed --top-k 20 50 100 200 --rerank-pool-size 300
```

Output: `rerank_method_comparison.csv`, `rerank_topk_summary.csv`, compact diagnostics, and figures.

## Figure Generation

Figures are generated by the formal experiment, ablation, pairwise rank-loss, synthetic renewable, Top-K depth tradeoff, ensemble, and rerank scripts. Main output directories:

```text
results/gcn_search/pio_formal_preliminary_3seed/figures/
results/gcn_search/pio_formal_ablation_3seed/figures/
results/gcn_search/pio_rank_loss_preliminary_3seed/figures/
results/gcn_search/pio_renewable_preliminary/figures/
results/gcn_search/pio_topk_depth_tradeoff/figures/
results/gcn_search/pio_ensemble_preliminary/figures/
results/gcn_search/pio_rerank_preliminary/figures/
```

## Artifact Self-Check

Purpose: verify that key docs/results exist and disallowed result details are not tracked.

```powershell
& "C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe" scripts/gcn_search/check_pio_gcn_artifacts.py
```

Output: PASS/FAIL console report.

## Clean Large File Tracking

Purpose: remove unsuitable result details from Git tracking while keeping local files.

```powershell
git rm --cached -- <tracked-large-or-detail-file>
```

Round-8 cleanup list:

```text
results/gcn_search/tracked_large_files_removed_round8.txt
```
