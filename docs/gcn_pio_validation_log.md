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
