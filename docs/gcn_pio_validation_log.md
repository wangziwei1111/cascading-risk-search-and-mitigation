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
