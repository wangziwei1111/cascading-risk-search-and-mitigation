# PIO-GCN PathRank 方法说明

## 方法名称

中文名：

```text
物理约束在线 GCN 连锁故障路径快速搜索方法
```

英文名：

```text
Physics-informed Online GCN for Cascading Failure Path Search
```

简称：

```text
PIO-GCN PathRank
```

## 与原始 GCN_path_prob 的关系

原始主线为：

```text
顺序改进 OPA 仿真器 + reachable GCN + GCN_path_prob 路径级全局排序
```

原始路径分数为：

```text
score(L_i -> L_j) = p_shed(L_i | S0) * p_shed(L_j | S1(i))
```

本次改进没有删除或覆盖原始 `GCN_path_prob`，而是在其基础上新增：

- physics feature dataset generation；
- physics-informed GCN training；
- online measured-state input；
- candidate probability mask；
- Top-K 小样本物理仿真校验；
- smoke-test 消融记录。

## 物理增强特征

新增函数：

```text
src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py
_make_x_gcn_physics(case, beta, security_limit=1.0)
_x_gcn_physics_feature_names()
```

physics 特征包括：

| 特征 | 中文含义 |
|---|---|
| `branch_status_offline` | 支路离线状态，离线为 1，在线为 0 |
| `relay_loading_ratio` | `|P_line| / (beta * RATE_A)`，相对保护阈值的负载率 |
| `abs_flow` | 支路潮流绝对值 |
| `max_terminal_load` | 支路两端母线最大负荷 |
| `loading_ratio` | `|P_line| / RATE_A`，相对长期安全容量的负载率 |
| `security_margin` | `security_limit - loading_ratio`，安全裕度 |
| `relay_margin` | `beta - loading_ratio`，保护裕度 |
| `is_online` | 支路是否在线 |
| `is_candidate` | 支路是否可作为候选主动故障 |

原始 `_make_x_gcn(case, beta)` 保持 4 维输入不变。

## 物理约束损失

新增模块：

```text
src/gcn_search/legacy_rts79/gcn_physics_constraints.py
```

核心函数：

```text
apply_candidate_probability_mask(probability, candidate_mask)
make_candidate_mask(case, used_lines=None)
compute_mask_invalid_loss(...)
compute_relay_priority_loss(...)
compute_loading_monotonic_loss(...)
compute_physics_constraint_loss(...)
```

约束逻辑：

- 已断开、不在线、已在 `used_lines` 中的线路不能作为候选主动故障；
- 非候选线路预测概率通过 mask 置零；
- 过载线路的风险概率不应过低；
- 在候选集合内，负载率更高的线路不应被系统性排到更低风险；
- 当所有 lambda 为 0 时，`total_physics_loss = 0`，训练退化为普通 CE 训练。

## 在线状态更新

新增模块：

```text
src/gcn_search/legacy_rts79/online_state_update.py
```

支持 JSON 字段：

```text
branch_status
branch_flow_mw
bus_load_mw
generator_output_mw
timestamp
source
```

样例：

```text
examples/rts79_measured_state_example.json
```

在线接口不会原地修改输入 case，而是复制后覆盖当前实测状态。

## Top-K 小样本物理仿真流程

新增脚本：

```text
src/gcn_search/legacy_rts79/evaluate_rts79_pio_gcn_topk.py
```

流程：

```text
加载 physics GCN 模型和 normalizer
-> 可选加载 measured-state JSON
-> 构造在线 case
-> 计算 physics GCN 概率
-> 用 candidate mask 修正概率
-> 按 score(L_i -> L_j) 生成路径排序
-> 只对 Top-K 路径运行 simulate_cascade_path
-> 输出排序、仿真结果和 summary
```

输出：

```text
pio_gcn_topk_order.csv
pio_gcn_topk_simulation_results.csv
pio_gcn_topk_summary.csv
pio_gcn_topk_config.json
```

## 消融 smoke-test

新增脚本：

```text
src/gcn_search/legacy_rts79/run_pio_gcn_ablation.py
```

记录方法：

- `original_GCN_path_prob`
- `physics_features_only`
- `physics_features_plus_mask`
- `physics_informed_loss`
- `online_state_update`
- `pio_gcn_topk`

注意：当前是 smoke-test 级别，不是正式完整消融实验。失败方法会记录在 `notes` 中，不会导致整个脚本崩溃。

## 验证命令

单元测试：

```powershell
python -m pytest tests/test_gcn_physics_features.py
python -m pytest tests/test_gcn_probability_mask.py
python -m pytest tests/test_gcn_physics_losses.py
python -m pytest tests/test_online_state_update.py
```

physics 数据集 smoke：

```powershell
python generate_rts79_step2_state_dataset.py --num-scenarios 1 --max-active-depth 0 --feature-mode physics
```

physics GCN 训练 smoke：

```powershell
python train_rts79_physics_gcn.py --dataset-npz <physics_dataset.npz> --epochs 1
```

PIO-GCN Top-K smoke：

```powershell
python evaluate_rts79_pio_gcn_topk.py --model <model.pt> --normalizer <normalizer.json> --top-k 20 50 100 --max-paths-for-smoke-test 100
```

## 当前限制

1. 当前新增的是 smoke framework，不是正式 800 场景训练结果。
2. 当前 physics loss 是可运行的初版约束，权重仍需系统调参。
3. Top-K 当前用于减少精确仿真次数，但小模型排序效果不代表正式模型性能。
4. measured-state JSON 是接口样例，不是真实 SCADA/PMU 数据。
5. 原始 `GCN_path_prob` 仍保留为基线方法。

## 第二轮修正记录

本轮修正重点是物理一致性和评价语义。

### raw physics features

数据集在 physics 模式下同时保存：

```text
x_gcn                # 归一化后模型输入
x_gcn_raw            # 未归一化原始特征
physics_raw_features # physics loss 使用的原始物理特征
```

训练时：

```text
model input uses normalized features
physics loss uses raw physical features
```

也就是说，GCN 前向传播仍使用归一化 `x_gcn`，但 `loading_ratio`、`is_online`、`is_candidate` 等物理约束量从 raw features 中读取。

### relay loss 使用 beta

`compute_relay_priority_loss` 已改为：

```text
relay candidate = loading_ratio > beta
```

默认 `beta = 1.2`。这避免把 `security_limit = 1.0` 和继电保护阈值 `beta = 1.2` 混淆。

### measured-state 贯穿 Top-K 仿真

`evaluate_rts79_pio_gcn_topk.py` 在加载 measured-state 后，会先构造 updated root case。后续：

- 第一步概率预测；
- 第一故障后的 `S1(i)`；
- 第二步概率预测；
- Top-K 精确物理仿真；

均从该 updated root case 出发。

输出文件新增：

```text
used_measured_state
initial_offline_lines
simulation_initial_source
```

### full truth / smoke truth 语义

`--run-exhaustive-truth` 不再使用。当前改为：

```text
--run-full-truth
```

如果使用 `--max-paths-for-smoke-test`，则只输出 `smoke_recall`，不把它伪装成正式 `critical_path_recall`。

### ablation 区分

`run_pio_gcn_ablation.py` 已从形式消融改成不同配置：

- `original_GCN_path_prob`：读取原始 baseline CSV；
- `physics_features_only`：physics CE-only 模型，关闭 candidate probability mask；
- `physics_features_plus_mask`：physics CE-only 模型，启用 mask；
- `physics_informed_loss`：带非零 lambda 的 physics-informed 模型；
- `online_state_update`：使用 measured-state updated root case；
- `pio_gcn_topk`：physics-informed 模型 + mask + Top-K physical simulation。

当前仍是 smoke-test，不是正式性能消融。
