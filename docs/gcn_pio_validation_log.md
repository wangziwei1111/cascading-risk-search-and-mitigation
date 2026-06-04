# Round 9 Final Polish and PR Readiness

Purpose: final polish for the current PIO-GCN PathRank stage. This round does not add a new algorithm, does not rerun large experiments, and does not extend functionality.

## Path and Terminology Fixes

- Fixed nonexistent script references from `run_pio_gcn_formal_experiment.py` to the real `run_pio_gcn_formal_small_experiment.py`.
- Updated README entry commands so they point to real scripts for data generation, physics GCN training, PIO-GCN Top-K evaluation, formal preliminary experiment, formal ablation, pairwise rank-loss experiment, and artifact self-check.
- Unified current-facing docs around these terms: `PIO-GCN PathRank`, `physics-enhanced features`, `candidate mask`, `original physics loss`, `pairwise rank-loss`, `JSON measured-state interface`, and `3-seed RTS-79 full-truth preliminary result`.
- Reworded field-measurement claims to state that JSON measured-state interface is not connected to field SCADA/PMU systems.

## Added Import Smoke Test

Added:

```text
tests/test_pio_gcn_imports.py
```

It imports key PIO-GCN PathRank modules without running large experiments:

```text
gcn_physics_constraints
online_state_update
rts79_cascade_from_case
train_rts79_physics_gcn
evaluate_rts79_pio_gcn_topk
run_pio_gcn_formal_small_experiment
run_pio_gcn_formal_ablation
run_pio_gcn_rank_loss_experiment
```

## Artifact Self-Check Enhancements

`scripts/gcn_search/check_pio_gcn_artifacts.py` now also checks:

- `docs/pio_gcn_pr_description.md` contains an RL untouched statement.
- `docs/pio_gcn_advisor_brief.md` clearly states that the result is not a final paper conclusion.
- `docs/pio_gcn_stage_summary.md` does not contain the nonexistent script name `run_pio_gcn_formal_experiment.py`.
- Key summary CSV files exist and are non-empty.

## Validation Commands

```text
python -m pytest tests/test_cascade_from_case_consistency.py tests/test_measured_state_sanity.py tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_gcn_ranking_loss.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py tests/test_pio_gcn_imports.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
```

## Observed Result

```text
pytest: 24 passed, 266 warnings
artifact self-check: PASS: PIO-GCN artifacts are review-ready.
```

## RL Status

`src/rl_mitigation` and `scripts/rl_mitigation` are not modified in this round.

## PR Recommendation

After the final validation commands pass, this branch is ready to open a review PR for the current PIO-GCN PathRank preliminary milestone.

# PIO-GCN PathRank 验证日志

## 基本信息

- 分支：`feature/pio-gcn-topk-smoke`
- 开始基线 commit：`f72eb64ddf7f3d9bd8e7bbe2603dfdfadf65f63e`
- Python：`Python 3.13.7`
- 关键依赖：
  - `numpy 2.4.4`
  - `pandas 3.0.3`
  - `torch 2.11.0+cpu`
  - `pytest 9.0.3`
- 运行环境说明：系统默认 Python 的 torch DLL 路径异常，验证改用 `C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe`。该 venv 原有 torch，已补装 pytest。

## 修改文件

- `README.md`
- `docs/gcn_current_progress.md`
- `src/gcn_search/legacy_rts79/generate_rts79_step2_state_dataset.py`
- `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`

## 新增文件

- `docs/pio_gcn_method.md`
- `docs/gcn_pio_validation_log.md`
- `examples/rts79_measured_state_example.json`
- `src/gcn_search/legacy_rts79/gcn_physics_constraints.py`
- `src/gcn_search/legacy_rts79/online_state_update.py`
- `src/gcn_search/legacy_rts79/train_rts79_physics_gcn.py`
- `src/gcn_search/legacy_rts79/evaluate_rts79_pio_gcn_topk.py`
- `src/gcn_search/legacy_rts79/run_pio_gcn_ablation.py`
- `tests/test_gcn_physics_features.py`
- `tests/test_gcn_probability_mask.py`
- `tests/test_gcn_physics_losses.py`
- `tests/test_online_state_update.py`

## 单元测试

命令：

```powershell
C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe -m pytest tests/test_gcn_physics_features.py -q
```

结果：`2 passed`

命令：

```powershell
C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe -m pytest tests/test_gcn_probability_mask.py -q
```

结果：`2 passed`

命令：

```powershell
C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe -m pytest tests/test_gcn_physics_losses.py -q
```

结果：`3 passed`

命令：

```powershell
C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe -m pytest tests/test_online_state_update.py -q
```

结果：`2 passed`

合并运行结果：`9 passed`

## Smoke-test 命令和输出

### paper feature 回归数据集

命令：

```powershell
python generate_rts79_step2_state_dataset.py --output-dir results/gcn_search/pio_validation/paper_dataset --num-scenarios 1 --first-seed 20260722 --max-active-depth 0 --feature-mode paper
```

输出：

```text
results/gcn_search/pio_validation/paper_dataset/rts79_step2_state_dataset.npz
results/gcn_search/pio_validation/paper_dataset/rts79_step2_state_feature_normalizer.json
results/gcn_search/pio_validation/paper_dataset/rts79_step2_state_dataset_stats.json
```

关键指标：

```text
feature_mode = paper
num_features = 4
num_states = 1
num_candidate_labels = 38
num_reachable_positive = 25
```

### physics feature 数据集

命令：

```powershell
python generate_rts79_step2_state_dataset.py --output-dir results/gcn_search/pio_validation/physics_dataset --num-scenarios 1 --first-seed 20260722 --max-active-depth 0 --feature-mode physics
```

输出：

```text
results/gcn_search/pio_validation/physics_dataset/rts79_step2_state_dataset_physics.npz
results/gcn_search/pio_validation/physics_dataset/rts79_step2_state_feature_normalizer_physics.json
results/gcn_search/pio_validation/physics_dataset/rts79_step2_state_dataset_stats_physics.json
```

关键指标：

```text
feature_mode = physics
num_features = 9
num_states = 1
num_candidate_labels = 38
num_reachable_positive = 25
```

### physics-informed GCN 训练

命令：

```powershell
python train_rts79_physics_gcn.py --dataset-npz results/gcn_search/pio_validation/physics_dataset/rts79_step2_state_dataset_physics.npz --output-dir results/gcn_search/pio_validation/physics_train --epochs 1 --batch-size 1 --lambda-mask 0.1 --lambda-relay 0.1 --lambda-monotonic 0.1
```

输出：

```text
results/gcn_search/pio_validation/physics_train/rts79_physics_gcn_model.pt
results/gcn_search/pio_validation/physics_train/rts79_physics_gcn_metrics.csv
results/gcn_search/pio_validation/physics_train/rts79_physics_gcn_epoch_log.csv
results/gcn_search/pio_validation/physics_train/rts79_physics_gcn_train_config.json
```

关键指标：

```text
validation_total_accuracy = 0.4473684210526316
validation_hit_rate = 0.75
validation_cover_rate = 0.24
validation_f1 = 0.36363636363636365
```

说明：这是 1 场景、1 epoch smoke 模型，不作为正式性能结论。

### CE-only 退化训练

命令：

```powershell
python train_rts79_physics_gcn.py --dataset-npz results/gcn_search/pio_validation/physics_dataset/rts79_step2_state_dataset_physics.npz --output-dir results/gcn_search/pio_validation/physics_train_ce_only --epochs 1 --batch-size 1 --lambda-mask 0 --lambda-relay 0 --lambda-monotonic 0
```

结果：通过。`total_loss = ce_loss`，说明 lambda 全 0 时可退化为普通 CE 训练。

### 原始 GCN_path_prob 基线 smoke

命令：

```powershell
python train_rts79_physics_gcn.py --dataset-npz results/gcn_search/pio_validation/paper_dataset/rts79_step2_state_dataset.npz --output-dir results/gcn_search/pio_validation/paper_train_ce_only --epochs 1 --batch-size 1 --lambda-mask 0 --lambda-relay 0 --lambda-monotonic 0
python evaluate_rts79_paper_gcn_search.py --model results/gcn_search/pio_validation/paper_train_ce_only/rts79_physics_gcn_model.pt --normalizer results/gcn_search/pio_validation/paper_dataset/rts79_step2_state_feature_normalizer.json --output-dir results/gcn_search/baseline_smoke --seed 20260722 --beta 1.2 --security-limit 1.0 --gcn-threshold 0.5
```

输出：

```text
results/gcn_search/baseline_smoke/rts79_search_efficiency_summary.csv
results/gcn_search/baseline_smoke/rts79_search_efficiency_curve.csv
results/gcn_search/baseline_smoke/rts79_search_order.csv
```

关键 smoke 指标：

```text
GCN_path_prob attempts_to_find_all = 1401
GCN_path_prob found_after_50_attempts = 8
GCN_path_prob found_after_100_attempts = 10
```

说明：这是 1 场景、1 epoch 小模型，不能和 800 场景正式结果混用。

### PIO-GCN Top-K smoke

命令：

```powershell
python evaluate_rts79_pio_gcn_topk.py --model results/gcn_search/pio_validation/physics_train/rts79_physics_gcn_model.pt --normalizer results/gcn_search/pio_validation/physics_dataset/rts79_step2_state_feature_normalizer_physics.json --output-dir results/gcn_search/pio_validation/pio_topk --seed 20260722 --top-k 20 50 100 --max-paths-for-smoke-test 100
```

输出：

```text
results/gcn_search/pio_validation/pio_topk/pio_gcn_topk_order.csv
results/gcn_search/pio_validation/pio_topk/pio_gcn_topk_simulation_results.csv
results/gcn_search/pio_validation/pio_topk/pio_gcn_topk_summary.csv
results/gcn_search/pio_validation/pio_topk/pio_gcn_topk_config.json
```

关键 smoke 指标：

```text
Top-20: critical_found = 0
Top-50: critical_found = 2
Top-100: critical_found = 4
```

说明：使用 `--max-paths-for-smoke-test 100`，不是完整实验。

### 带 measured-state JSON 的 PIO-GCN Top-K smoke

命令：

```powershell
python evaluate_rts79_pio_gcn_topk.py --model results/gcn_search/pio_validation/physics_train/rts79_physics_gcn_model.pt --normalizer results/gcn_search/pio_validation/physics_dataset/rts79_step2_state_feature_normalizer_physics.json --output-dir results/gcn_search/pio_validation/pio_topk_measured --seed 20260722 --top-k 20 --measured-state-json examples/rts79_measured_state_example.json --max-paths-for-smoke-test 20
```

关键 smoke 指标：

```text
Top-20: critical_found = 1
```

### ablation smoke-test

命令：

```powershell
python run_pio_gcn_ablation.py --model results/gcn_search/pio_validation/physics_train/rts79_physics_gcn_model.pt --normalizer results/gcn_search/pio_validation/physics_dataset/rts79_step2_state_feature_normalizer_physics.json --output-dir results/gcn_search/pio_validation/pio_ablation --top-k 20 --max-paths-for-smoke-test 20 --measured-state-json examples/rts79_measured_state_example.json
```

输出：

```text
results/gcn_search/pio_validation/pio_ablation/pio_gcn_ablation_summary.csv
results/gcn_search/pio_validation/pio_ablation/pio_gcn_ablation_details.csv
results/gcn_search/pio_validation/pio_ablation/pio_gcn_ablation_config.json
```

结果：通过。所有方法均写入 summary；该消融是 smoke proxy，不是正式性能对比。

## 是否影响原始 GCN_path_prob

- 未删除原始 `GCN_path_prob`。
- 原始 `_make_x_gcn(case, beta)` 保持 4 维输出。
- 新增 physics 功能通过 `feature_mode=physics`、新训练脚本和新评估脚本进入。
- paper 模式默认不变。

## 是否修改 RL 部分

检查命令：

```powershell
git diff -- src/rl_mitigation scripts/rl_mitigation
```

结果：空输出。

结论：未修改 RL 部分。

## 当前限制

1. 当前新增的是 smoke framework，不是正式性能复现实验。
2. 新模型仅使用 1 个负荷场景、1 epoch 训练，排序效果不能代表正式 800 场景模型。
3. `--max-paths-for-smoke-test` 会限制精确仿真路径数量，因此 recall 为空或仅适合作 smoke 说明。
4. measured-state JSON 是接口样例，不是真实在线量测数据。

## 第二轮修正验证记录

### 修正内容

- physics loss 已改用 raw features：模型输入仍为归一化 `x_gcn`，物理约束读取 `physics_raw_features/x_gcn_raw`。
- relay loss 已改用 `loading_ratio > beta`，默认 `beta = 1.2`。
- measured-state 已贯穿 Top-K 排序和物理仿真：`S1(i)` 和最终 `simulate_cascade_path_from_case` 均从 updated root case 出发。
- `exhaustive_truth` 语义已修正：正式参数为 `--run-full-truth`；使用 `--max-paths-for-smoke-test` 时只输出 `smoke_recall`。
- ablation 已改成真实配置区分，不再所有方法共用同一 evaluator 配置。

### 新增/更新文件

- `src/gcn_search/legacy_rts79/rts79_cascade_from_case.py`
- `src/gcn_search/legacy_rts79/evaluate_rts79_pio_gcn_topk.py`
- `src/gcn_search/legacy_rts79/run_pio_gcn_ablation.py`
- `src/gcn_search/legacy_rts79/train_rts79_physics_gcn.py`
- `src/gcn_search/legacy_rts79/gcn_physics_constraints.py`
- `src/gcn_search/legacy_rts79/generate_rts79_step2_state_dataset.py`
- `tests/test_gcn_raw_feature_training.py`
- `tests/test_pio_topk_measured_consistency.py`
- `tests/test_gcn_physics_losses.py`
- `docs/pio_gcn_method.md`
- `docs/gcn_current_progress.md`
- `docs/gcn_pio_validation_log.md`

### 单元测试

命令：

```powershell
C:\Users\24186\Documents\New project 7\.venv\Scripts\python.exe -m pytest tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py -q
```

结果：

```text
13 passed, 40 warnings
```

### physics feature 数据集 smoke-test

命令：

```powershell
python generate_rts79_step2_state_dataset.py --output-dir results/gcn_search/pio_validation_round2/physics_dataset --num-scenarios 1 --first-seed 20260722 --max-active-depth 0 --feature-mode physics
```

输出：

```text
results/gcn_search/pio_validation_round2/physics_dataset/rts79_step2_state_dataset_physics.npz
```

确认字段：

```text
x_gcn
x_gcn_raw
physics_raw_features
```

关键结果：

```text
feature_mode = physics
num_features = 9
num_states = 1
physics_loss_uses_raw_physical_features = true
```

### paper feature 回归 smoke-test

命令：

```powershell
python generate_rts79_step2_state_dataset.py --output-dir results/gcn_search/pio_validation_round2/paper_dataset --num-scenarios 1 --first-seed 20260722 --max-active-depth 0 --feature-mode paper
```

结果：

```text
feature_mode = paper
num_features = 4
```

### physics-informed 训练 smoke-test

命令：

```powershell
python train_rts79_physics_gcn.py --dataset-npz results/gcn_search/pio_validation_round2/physics_dataset/rts79_step2_state_dataset_physics.npz --output-dir results/gcn_search/pio_validation_round2/physics_train --epochs 1 --batch-size 1 --lambda-mask 0.1 --lambda-relay 0.1 --lambda-monotonic 0.1 --beta 1.2
```

结果：

```text
validation_f1 = 0.36363636363636365
relay_priority_loss = 0.0
loading_monotonic_loss = 0.0026232784148305655
```

说明：本 smoke 场景没有 raw `loading_ratio > beta` 的支路，因此 relay loss 为 0；beta 判据由单元测试覆盖。

### CE-only 训练 smoke-test

命令：

```powershell
python train_rts79_physics_gcn.py --dataset-npz results/gcn_search/pio_validation_round2/physics_dataset/rts79_step2_state_dataset_physics.npz --output-dir results/gcn_search/pio_validation_round2/physics_train_ce_only --epochs 1 --batch-size 1 --lambda-mask 0 --lambda-relay 0 --lambda-monotonic 0 --beta 1.2
```

结果：通过，`total_loss = ce_loss`。

### PIO-GCN Top-K smoke-test，无 measured-state

命令：

```powershell
python evaluate_rts79_pio_gcn_topk.py --model results/gcn_search/pio_validation_round2/physics_train/rts79_physics_gcn_model.pt --normalizer results/gcn_search/pio_validation_round2/physics_dataset/rts79_step2_state_feature_normalizer_physics.json --output-dir results/gcn_search/pio_validation_round2/pio_topk --seed 20260722 --top-k 20 50 100 --max-paths-for-smoke-test 100
```

输出：

```text
results/gcn_search/pio_validation_round2/pio_topk/
```

关键结果：

```text
Top-20 critical_found = 0
Top-50 critical_found = 2
Top-100 critical_found = 4
simulation_initial_source = seed_initial_dcopf_case
```

### PIO-GCN Top-K smoke-test，有 measured-state

命令：

```powershell
python evaluate_rts79_pio_gcn_topk.py --model results/gcn_search/pio_validation_round2/physics_train/rts79_physics_gcn_model.pt --normalizer results/gcn_search/pio_validation_round2/physics_dataset/rts79_step2_state_feature_normalizer_physics.json --output-dir results/gcn_search/pio_validation_round2/pio_topk_measured --seed 20260722 --top-k 20 --measured-state-json examples/rts79_measured_state_example.json --max-paths-for-smoke-test 20
```

输出：

```text
results/gcn_search/pio_validation_round2/pio_topk_measured/
```

关键结果：

```text
Top-20 critical_found = 17
used_measured_state = True
initial_offline_lines = L03
simulation_initial_source = measured_state_updated_case
```

人工检查：`L03` 未出现在 Top-K order 的 first/second 主动故障路径中，且 final outage labels 保留 `L03`。

### ablation smoke-test

命令：

```powershell
python run_pio_gcn_ablation.py --physics-informed-model results/gcn_search/pio_validation_round2/physics_train/rts79_physics_gcn_model.pt --physics-ce-model results/gcn_search/pio_validation_round2/physics_train_ce_only/rts79_physics_gcn_model.pt --physics-normalizer results/gcn_search/pio_validation_round2/physics_dataset/rts79_step2_state_feature_normalizer_physics.json --baseline-summary results/gcn_search/baseline_smoke_round2/rts79_search_efficiency_summary.csv --paper-model results/gcn_search/pio_validation_round2/paper_train_ce_only/rts79_physics_gcn_model.pt --paper-normalizer results/gcn_search/pio_validation_round2/paper_dataset/rts79_step2_state_feature_normalizer.json --output-dir results/gcn_search/pio_validation_round2/pio_ablation --top-k 20 --max-paths-for-smoke-test 20 --measured-state-json examples/rts79_measured_state_example.json
```

输出：

```text
results/gcn_search/pio_validation_round2/pio_ablation/pio_gcn_ablation_summary.csv
results/gcn_search/pio_validation_round2/pio_ablation/pio_gcn_ablation_details.csv
results/gcn_search/pio_validation_round2/pio_ablation/pio_gcn_ablation_config.json
```

确认：

- `original_GCN_path_prob` 读取 paper baseline CSV；
- `physics_features_only` 使用 physics CE-only 模型且关闭 probability mask；
- `physics_features_plus_mask` 使用 physics CE-only 模型且启用 mask；
- `physics_informed_loss` 使用非零 lambda 模型；
- `online_state_update` 使用 measured-state；
- `pio_gcn_topk` 使用 physics-informed model + mask + Top-K simulation。

### RL 修改检查

命令：

```powershell
git diff -- src/rl_mitigation scripts/rl_mitigation
```

结果：空输出。

结论：第二轮未修改 RL 部分。
## Third-Round Validation Log: Small Trusted Experiment

### Cascade from-case consistency test

Command:

```powershell
python -m pytest tests/test_cascade_from_case_consistency.py -q
```

Result:

```text
5 passed
```

The test compares the original `simulate_cascade_path([first, second], config=...)`
with `simulate_cascade_path_from_case(root_case, [first, second], ...)` on five fixed paths:

```text
L10->L05
L27->L02
L01->L02
L04->L08
L16->L17
```

Compared fields:

```text
total_load_shed_mw
critical
final_outage_labels
final_max_loading_ratio
```

### Measured-state sanity test

Command:

```powershell
python -m pytest tests/test_measured_state_sanity.py -q
```

Result:

```text
1 passed
```

Checked behavior:

- `examples/rts79_measured_state_example.json` opens `L03`.
- `L03` does not appear in `first_line` or `second_line` in Top-K order.
- `initial_offline_lines` contains `L03`.
- `final_outage_labels` contains `L03`.
- `simulation_initial_source = measured_state_updated_case`.
- `online_state_summary.json` is generated.

### Existing GCN/PIO regression tests

Command:

```powershell
python -m pytest tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py -q
```

Result:

```text
13 passed
```

### Small experiment

Command:

```powershell
python src/gcn_search/legacy_rts79/run_pio_gcn_small_experiment.py --model results/gcn_search/pio_validation_round2/physics_train/rts79_physics_gcn_model.pt --normalizer results/gcn_search/pio_validation_round2/physics_dataset/rts79_step2_state_feature_normalizer_physics.json --baseline-summary-dir results/gcn_search/baseline_smoke_round2 --output-dir results/gcn_search/pio_small_experiment --seed-start 20260722 --num-seeds 10 --top-k 20 50 100 --max-paths-for-smoke-test 100
```

Output:

```text
results/gcn_search/pio_small_experiment/per_seed_summary.csv
results/gcn_search/pio_small_experiment/aggregate_summary.csv
results/gcn_search/pio_small_experiment/method_comparison_summary.csv
results/gcn_search/pio_small_experiment/config.json
```

Aggregate summary:

```text
Top-20: mean_num_critical_found = 0.6, mean_smoke_recall = 0.25, mean_runtime_seconds = 3.5413
Top-50: mean_num_critical_found = 1.9, mean_smoke_recall = 0.8167, mean_runtime_seconds = 3.5413
Top-100: mean_num_critical_found = 2.5, mean_smoke_recall = 1.0, mean_runtime_seconds = 3.5413
```

Because this run uses `--max-paths-for-smoke-test 100`, the recall column is smoke recall only.
It must not be reported as formal full-truth critical path recall.

### Method comparison summary

Output:

```text
results/gcn_search/pio_small_experiment/method_comparison_summary.csv
```

Key rows:

```text
original_GCN_path_prob_smoke_baseline: attempts_to_find_all = 1370, found_after_100 = 11
PIO_GCN_Top20: mean_critical_found = 0.6, mean_smoke_recall = 0.25
PIO_GCN_Top50: mean_critical_found = 1.9, mean_smoke_recall = 0.8167
PIO_GCN_Top100: mean_critical_found = 2.5, mean_smoke_recall = 1.0
```

The baseline row is read from an existing baseline CSV. Its truth definition may differ from the PIO smoke truth,
so it is recorded for context and should not be forced into a formal apples-to-apples comparison.

### Plot outputs

Command:

```powershell
python src/gcn_search/legacy_rts79/plot_pio_gcn_small_experiment.py --per-seed-summary results/gcn_search/pio_small_experiment/per_seed_summary.csv --aggregate-summary results/gcn_search/pio_small_experiment/aggregate_summary.csv --output-dir results/gcn_search/pio_small_experiment/figures
```

Output:

```text
results/gcn_search/pio_small_experiment/figures/critical_found_bar.png
results/gcn_search/pio_small_experiment/figures/runtime_bar.png
```

No `topk_recall_bar.png` was generated because this run does not contain full-truth recall.

### RL modification check

Command:

```powershell
git diff -- src/rl_mitigation scripts/rl_mitigation
```

Result:

```text
empty output
```

Conclusion: the third round did not modify RL mitigation code.

## Fourth-Round Validation Log: Formal-Small Experiment

### Pytest

Command:

```powershell
python -m pytest tests/test_cascade_from_case_consistency.py tests/test_measured_state_sanity.py tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py -q
```

Result:

```text
19 passed
```

### Formal-small experiment attempts

The target command was attempted first:

```powershell
python src/gcn_search/legacy_rts79/run_pio_gcn_formal_small_experiment.py --output-dir results/gcn_search/pio_formal_small_experiment --training-num-scenarios 50 --training-epochs 10 --test-seed-start 20260722 --test-num-seeds 5 --top-k 20 50 100 --skip-training-if-exists
```

Result: timed out in the current interactive runtime window.

The light configuration suggested by the task was then attempted:

```powershell
training_num_scenarios = 20
training_epochs = 5
test_num_seeds = 3
```

Result: timed out during training data generation.

The completed run used a smaller full-truth preview:

```powershell
python src/gcn_search/legacy_rts79/run_pio_gcn_formal_small_experiment.py --output-dir results/gcn_search/pio_formal_small_experiment --training-num-scenarios 5 --training-epochs 3 --training-max-active-depth 0 --test-seed-start 20260722 --test-num-seeds 1 --top-k 20 50 100 --skip-training-if-exists
```

This run completed successfully.

### Output path

```text
results/gcn_search/pio_formal_small_experiment/
```

Required summary files were generated:

```text
config.json
training_dataset_stats.json
physics_training_metrics.csv
physics_ce_training_metrics.csv
per_seed_full_truth_summary.csv
pio_topk_per_seed_summary.csv
baseline_per_seed_summary.csv
aggregate_method_comparison.csv
aggregate_topk_summary.csv
```

### Full truth

This completed run uses full ordered N-2 truth for the one test seed.

```text
test_seed = 20260722
total_critical_paths = 55
```

### aggregate_topk_summary.csv

```text
PIO_GCN_Top20: mean_critical_found = 1, mean_critical_path_recall = 0.0182
PIO_GCN_Top50: mean_critical_found = 3, mean_critical_path_recall = 0.0545
PIO_GCN_Top100: mean_critical_found = 7, mean_critical_path_recall = 0.1273
```

### aggregate_method_comparison.csv

```text
original_GCN_path_prob: found_after_100 = 10, attempts_to_find_all = 1401
LODF_yP: found_after_100 = 11, attempts_to_find_all = 1148
random: found_after_100 = 4, attempts_to_find_all = 1381
line_order: found_after_100 = 3, attempts_to_find_all = 1400
oracle: found_after_100 = 55, attempts_to_find_all = 55
```

### Figures

```text
results/gcn_search/pio_formal_small_experiment/figures/topk_recall_bar.png
results/gcn_search/pio_formal_small_experiment/figures/found_after_k_comparison.png
results/gcn_search/pio_formal_small_experiment/figures/runtime_comparison.png
```

### Result cleanup policy

`.gitignore` was updated to ignore large/intermediate GCN result files:

```text
results/gcn_search/**/*.pt
results/gcn_search/**/*.npz
results/gcn_search/**/scenario_checkpoints/
results/gcn_search/**/*order.csv
results/gcn_search/**/*curve.csv
results/gcn_search/**/*full_truth.csv
results/gcn_search/**/*smoke_truth.csv
results/gcn_search/**/*simulation_results.csv
```

The completed formal-small experiment keeps key summary CSV files, aggregate CSV files, figures, and docs.
Incomplete timeout outputs were removed before rerunning to avoid mixing incompatible configurations.

### RL modification check

Command:

```powershell
git diff -- src/rl_mitigation scripts/rl_mitigation
```

Result:

```text
empty output
```

Conclusion: the fourth round did not modify RL mitigation code.

## Fifth-Round Validation Log: Maintainability and 3-Seed Preliminary Formal Experiment

### Tracked large-file cleanup

Command used:

```powershell
git ls-files results/gcn_search | Where-Object { $_ -match '\.(pt|npz)$' -or $_ -match 'scenario_checkpoints/' -or $_ -match '(order|curve|full_truth|smoke_truth|simulation_results)\.csv$' } | git rm --cached -- ...
```

Result:

```text
89 tracked intermediate files were removed from Git tracking.
```

Cleanup categories:

```text
results/gcn_search/**/*.pt
results/gcn_search/**/*.npz
results/gcn_search/**/scenario_checkpoints/
results/gcn_search/**/*order.csv
results/gcn_search/**/*curve.csv
results/gcn_search/**/*full_truth.csv
results/gcn_search/**/*smoke_truth.csv
results/gcn_search/**/*simulation_results.csv
```

Local files were not deleted. They were only removed from Git tracking. The file list is saved at:

```text
results/gcn_search/tracked_large_files_removed_round5.txt
```

### Step2-State generation acceleration

New parameters:

```text
--candidate-line-filter-mode all | first_n | high_flow_top_n
--max-first-lines N
```

Default behavior remains unchanged:

```text
candidate_line_filter_mode = all
max_first_lines = null
```

The fifth-round preliminary experiment uses:

```text
candidate_line_filter_mode = high_flow_top_n
max_first_lines = 10
```

This keeps the original full behavior available while allowing preliminary experiments to include first-outage states without expanding all 38 first outages per scenario.

### Pytest

Command:

```powershell
python -m pytest tests/test_cascade_from_case_consistency.py tests/test_measured_state_sanity.py tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py -q
```

Result:

```text
19 passed
```

### 3-seed preliminary formal experiment

Command:

```powershell
python src/gcn_search/legacy_rts79/run_pio_gcn_formal_small_experiment.py --output-dir results/gcn_search/pio_formal_preliminary_3seed --training-num-scenarios 10 --training-epochs 5 --training-max-active-depth 1 --candidate-line-filter-mode high_flow_top_n --max-first-lines 10 --test-seed-start 20260722 --test-num-seeds 3 --top-k 20 50 100 --skip-training-if-exists
```

Output directory:

```text
results/gcn_search/pio_formal_preliminary_3seed/
```

Training dataset stats:

```text
num_states = 110
num_candidate_labels = 4080
num_one_step_positive = 199
num_reachable_positive = 427
one_step_positive_ratio = 0.0488
reachable_positive_ratio = 0.1047
```

Training metrics:

```text
validation_total_accuracy = 0.1225
validation_hit_rate = 0.1061
validation_cover_rate = 1.0
validation_f1 = 0.1919
```

This indicates a weak preliminary model with high coverage but many false positives.

Full-truth seeds:

```text
20260722: total_critical_paths = 55
20260723: total_critical_paths = 52
20260724: total_critical_paths = 59
```

### aggregate_topk_summary.csv

```text
PIO_GCN_Top20: mean_critical_found = 12.0, mean_critical_path_recall = 0.2160
PIO_GCN_Top50: mean_critical_found = 19.0, mean_critical_path_recall = 0.3427
PIO_GCN_Top100: mean_critical_found = 23.3333, mean_critical_path_recall = 0.4213
```

### aggregate_method_comparison.csv

```text
PIO_GCN_Top20: mean_found_after_20 = 12.0, mean_recall_at_20 = 0.2160
PIO_GCN_Top50: mean_found_after_50 = 19.0, mean_recall_at_50 = 0.3427
PIO_GCN_Top100: mean_found_after_100 = 23.3333, mean_recall_at_100 = 0.4213
original_GCN_path_prob: mean_found_after_100 = 8.0, mean_attempts_to_find_all = 1400.0
LODF_yP: mean_found_after_100 = 11.6667, mean_attempts_to_find_all = 1272.0
random: mean_found_after_100 = 3.0, mean_attempts_to_find_all = 1390.0
line_order: mean_found_after_100 = 3.6667, mean_attempts_to_find_all = 1287.6667
oracle: mean_found_after_100 = 55.3333, mean_attempts_to_find_all = 55.3333
```

PIO-GCN outperforms the listed non-oracle baselines in Top-100 critical paths found for this 3-seed preliminary run, but the model is still preliminary and should not be described as a final performance result.

### Diagnostics

Diagnostics directory:

```text
results/gcn_search/pio_formal_preliminary_3seed/diagnostics/
```

Files:

```text
topk_score_distribution.csv
missed_critical_paths.csv
found_critical_paths.csv
per_seed_candidate_count.csv
```

These files help explain whether missed paths were ranked after Top-100, whether model scores were poorly separated, and how many candidate paths were scored per seed.

### Figures

```text
results/gcn_search/pio_formal_preliminary_3seed/figures/topk_recall_bar.png
results/gcn_search/pio_formal_preliminary_3seed/figures/found_after_k_comparison.png
results/gcn_search/pio_formal_preliminary_3seed/figures/runtime_comparison.png
```

### RL modification check

Command:

```powershell
git diff -- src/rl_mitigation scripts/rl_mitigation
```

Result:

```text
empty output
```

Conclusion: the fifth round did not modify RL mitigation code.

## Sixth-Round Validation Log: Formal Preliminary Ablation

### Training diagnostics update

`train_rts79_physics_gcn.py` now reports additional validation diagnostics:

```text
validation_precision
validation_recall
validation_pr_auc
mean_predicted_positive_probability
positive_prediction_rate_at_0.5
positive_prediction_rate_at_0.8
mean_physics_loss
```

These metrics are intended to explain whether a model is over-predicting risky branches.

### Ablation command

```powershell
python src/gcn_search/legacy_rts79/run_pio_gcn_formal_ablation.py --output-dir results/gcn_search/pio_formal_ablation_3seed --base-experiment-dir results/gcn_search/pio_formal_preliminary_3seed --top-k 20 50 100
```

The run reused the fifth-round full-truth files for seeds:

```text
20260722
20260723
20260724
```

Full truth was validated against the fifth-round `per_seed_full_truth_summary.csv`.

### Ablation aggregate summary

Key Top-100 results:

```text
physics_ce_no_mask: mean_found_after_100 = 23.3333, mean_recall_at_100 = 0.4209
physics_ce_mask: mean_found_after_100 = 23.3333, mean_recall_at_100 = 0.4209
physics_loss_no_mask: mean_found_after_100 = 23.3333, mean_recall_at_100 = 0.4213
physics_loss_mask: mean_found_after_100 = 23.3333, mean_recall_at_100 = 0.4213
paper_gcn_path_prob: mean_found_after_100 = 8.0, mean_recall_at_100 = 0.1435
LODF_yP: mean_found_after_100 = 11.6667, mean_recall_at_100 = 0.2099
random: mean_found_after_100 = 3.0, mean_recall_at_100 = 0.0548
line_order: mean_found_after_100 = 3.6667, mean_recall_at_100 = 0.0657
oracle: mean_found_after_100 = 55.3333, mean_recall_at_100 = 1.0
```

Interpretation:

```text
The main gain comes from physics features.
Candidate mask does not materially change this 3-seed result.
Physics-informed loss gives only a tiny Top-100 gain and does not improve Top-20/Top-50 in this run.
```

### Diagnostics

Diagnostics directory:

```text
results/gcn_search/pio_formal_ablation_3seed/diagnostics/
```

Files:

```text
per_method_score_distribution.csv
per_method_top100_missed_critical.csv
per_method_top100_found_critical.csv
per_method_rank_of_critical_paths.csv
```

Figures:

```text
results/gcn_search/pio_formal_ablation_3seed/figures/ablation_recall_at_100.png
results/gcn_search/pio_formal_ablation_3seed/figures/ablation_found_after_k.png
results/gcn_search/pio_formal_ablation_3seed/figures/ablation_runtime.png
```

### Pytest

Command:

```powershell
python -m pytest tests/test_cascade_from_case_consistency.py tests/test_measured_state_sanity.py tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py -q
```

Result:

```text
19 passed
```

### RL modification check

Command:

```powershell
git diff -- src/rl_mitigation scripts/rl_mitigation
```

Result:

```text
empty output
```

Conclusion: the sixth round did not modify RL mitigation code.

## Seventh-Round Validation Log: Rank-Loss Training and Diagnostic Cleanup

### Large diagnostic cleanup

The detailed score distribution file was too large for long-term Git tracking:

```text
results/gcn_search/pio_formal_ablation_3seed/diagnostics/per_method_score_distribution.csv
```

It was removed from Git tracking with `git rm --cached`. The local file was not deleted.

A compact replacement summary was generated:

```text
results/gcn_search/pio_formal_ablation_3seed/diagnostics/per_method_score_distribution_summary.csv
```

The repository ignore rules now exclude future detailed score-distribution CSV files.

### New ranking loss test

New test file:

```text
tests/test_gcn_ranking_loss.py
```

It covers:

- zero loss when positive probabilities exceed negatives by the margin;
- positive loss when positives are ranked below negatives;
- zero loss when no positive or no negative pair exists;
- batch input;
- finite loss values.

### Pytest

Command:

```powershell
python -m pytest tests/test_cascade_from_case_consistency.py tests/test_measured_state_sanity.py tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_gcn_ranking_loss.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py -q
```

Result:

```text
23 passed
```

### Rank-loss training command

Command:

```powershell
python src/gcn_search/legacy_rts79/run_pio_gcn_rank_loss_experiment.py --output-dir results/gcn_search/pio_rank_loss_preliminary_3seed --base-experiment-dir results/gcn_search/pio_formal_preliminary_3seed --lambda-rank 0.2 --rank-margin 0.05 --rank-max-pairs 512
```

The run reused the fifth-round full-truth seeds:

```text
20260722
20260723
20260724
```

### Rank-loss training metrics

Final validation metrics:

```text
validation_pr_auc = 0.4402
mean_predicted_positive_probability = 0.7038
positive_prediction_rate_at_0.5 = 0.9743
positive_prediction_rate_at_0.8 = 0.2304
mean_positive_score = 0.8054
mean_negative_score = 0.6920
positive_negative_score_gap = 0.1135
```

The model still over-predicts positives, but the positive-negative score gap is larger than before.

### Rank-loss comparison result

```text
physics_ce_mask: found@20/50/100 = 12.3333 / 19.3333 / 23.3333
physics_loss_mask: found@20/50/100 = 12.0 / 19.0 / 23.3333
physics_rank_loss_mask: found@20/50/100 = 12.3333 / 19.3333 / 24.0
LODF_yP: found@20/50/100 = 2.0 / 8.0 / 11.6667
paper_gcn_path_prob: found@20/50/100 = 5.6667 / 7.0 / 8.0
oracle: found@20/50/100 = 20.0 / 50.0 / 55.3333
```

Interpretation:

```text
Rank-loss improves Top-100 slightly, from 23.3333 to 24.0 found critical paths.
It does not improve Top-20 or Top-50 in this run.
```

### Output files

```text
results/gcn_search/pio_rank_loss_preliminary_3seed/aggregate_topk_summary.csv
results/gcn_search/pio_rank_loss_preliminary_3seed/aggregate_method_comparison.csv
results/gcn_search/pio_rank_loss_preliminary_3seed/diagnostics/rank_loss_vs_ce_summary.csv
results/gcn_search/pio_rank_loss_preliminary_3seed/figures/rank_loss_vs_ce_recall.png
results/gcn_search/pio_rank_loss_preliminary_3seed/figures/rank_loss_vs_ce_found_after_k.png
```

### RL modification check

Command:

```powershell
git diff -- src/rl_mitigation scripts/rl_mitigation
```

Result:

```text
empty output
```

Conclusion: the seventh round did not modify RL mitigation code.
# Round 8 Validation Log

Purpose: close the current PIO-GCN branch into a reviewable preliminary milestone. This round does not add a new algorithm. It cleans result tracking, unifies conclusions, adds advisor/PR/reproduction documents, and adds an artifact self-check.

## Result Cleanup

Tracked old smoke, old validation, seed-level full-truth, root-level attachment, and historical IEEE14 result files were removed from Git tracking with `git rm --cached`. Local files were not deleted.

Cleanup list:

```text
results/gcn_search/tracked_large_files_removed_round8.txt
```

Large or unsuitable tracked artifact types are now covered by `.gitignore`, including `.pt`, `.npz`, seed folders, full-truth detail, smoke-truth detail, simulation-result detail, order detail, scenario checkpoints, root result docx/pdf attachments, and detailed score distribution CSV files.

## Added Review Documents

```text
docs/pio_gcn_stage_summary.md
docs/pio_gcn_advisor_brief.md
docs/pio_gcn_pr_description.md
docs/pio_gcn_reproduction_commands.md
```

## Unified Conclusion

- Main gain: physics-enhanced features.
- Preliminary Top-100 recall: around 42% on 3 RTS-79 full-truth seeds.
- LODF_yP: around 21%.
- Weak paper-feature `GCN_path_prob`: around 14%.
- Candidate mask: currently not a major contributor.
- Original physics loss: currently contributes very little.
- Rank-loss: no Top-20/Top-50 improvement; small Top-100 change only, not robust yet.
- JSON measured-state input only; no real SCADA/PMU integration claim.
- This is a 3-seed RTS-79 preliminary result, not a final paper-scale conclusion.

## Validation Commands

```text
python -m pytest tests/test_cascade_from_case_consistency.py tests/test_measured_state_sanity.py tests/test_gcn_physics_features.py tests/test_gcn_probability_mask.py tests/test_gcn_physics_losses.py tests/test_gcn_ranking_loss.py tests/test_online_state_update.py tests/test_gcn_raw_feature_training.py tests/test_pio_topk_measured_consistency.py
python scripts/gcn_search/check_pio_gcn_artifacts.py
```

Observed result:

```text
pytest: 23 passed, 284 warnings
artifact self-check: PASS: PIO-GCN artifacts are review-ready.
```

## RL Status

`src/rl_mitigation` and `scripts/rl_mitigation` are not modified in this round.

## Stage Score Suggestion

Current stage is suitable for a preliminary advisor update and PR review. It is not yet suitable for final paper performance claims.
