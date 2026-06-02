# IEEE RTS-79 GCN 连锁故障复现实验说明

## 主线结论

当前复现主线为：

```text
顺序 OPA 仿真器 + reachable GCN + GCN_path_prob 路径级全局排序
```

核心路径分数为：

```text
score(L_i -> L_j) = p_shed(L_i | S0) * p_shed(L_j | S1(i))
```

中文含义：

- `S0`：初始 DCOPF 稳定运行状态。
- `S1(i)`：主动断开 `L_i` 后，经过保护动作、孤岛处理和再调度后的稳定状态。
- `p_shed`：GCN 输出的切负荷可达概率。
- `reachable`：候选支路在剩余 `R = 2` 主动故障深度内是否可达切负荷。

5 个测试负荷场景平均结果：

```text
平均关键路径数 = 56.6
GCN_path_prob 平均找全次数 = 68.2
前 50 次平均找到 = 47.0
前 100 次平均找到 = 56.6
LODF_yP 平均找全次数 = 1259.8
```

## 固定参数

```text
R = 2
beta = 1.2
security_limit = 1.0
L_m^max = RATE_A
gamma_i ~ U[0.9, 1.1]
P_D,i^new = 1.1 * gamma_i * P_D,i
```

## 关键文件

仿真器：

```text
rts79_cascade.py
```

LODF 物理规则：

```text
rts79_lodf.py
```

Step2-State 数据集生成：

```text
generate_rts79_step2_state_dataset.py
generate_rts79_step2_state_worker.py
```

GCN 训练：

```text
train_rts79_step2_state_gcn.py
train_rts79_reachable_gcn.py
```

在线搜索评估：

```text
evaluate_rts79_paper_gcn_search.py
```

结果包生成：

```text
make_rts79_reproduction_package.py
```

## 已生成结果

800 场景训练数据：

```text
outputs/step2_state_dataset_800_seqopa_skip_terminal_parallel_beta_1_2
```

800 场景 reachable GCN 模型：

```text
outputs/step2_state_reachable_gcn_training_800_seqopa_skip_terminal_parallel_beta_1_2/reachable/rts79_step2_state_gcn_model.pt
```

Fig. 5 风格结果包：

```text
outputs/rts79_reproduction_package_800_reachable_pathprob
```

中文报告：

```text
RTS79_GCN_连锁故障复现报告.md
```

## 复跑在线搜索评估

单个测试场景：

```powershell
.\.venv\Scripts\python.exe evaluate_rts79_paper_gcn_search.py `
  --model outputs\step2_state_reachable_gcn_training_800_seqopa_skip_terminal_parallel_beta_1_2\reachable\rts79_step2_state_gcn_model.pt `
  --normalizer outputs\step2_state_dataset_800_seqopa_skip_terminal_parallel_beta_1_2\rts79_step2_state_feature_normalizer.json `
  --output-dir outputs\paper_gcn_search_eval_800_reachable_pathprob_seed_20260722 `
  --seed 20260722 `
  --beta 1.2 `
  --security-limit 1.0 `
  --gcn-threshold 0.5
```

重新生成结果包：

```powershell
.\.venv\Scripts\python.exe make_rts79_reproduction_package.py
```

## 注意事项

1. `R = 2` 只限制主动故障次数，不限制保护继电器导致的后续跳闸。
2. 训练集采用 Step2-State 状态，不是直接同时断两条线路。
3. 第一故障若已经导致切负荷，则不再生成该路径后的 `S1(i)` 决策状态。
4. 当前主线搜索不是旧的节点级 `GCN_prob`，而是路径级 `GCN_path_prob`。
5. 旧的 `GCN_prob` 需要约 927 次找全，主要原因是分层块状搜索顺序不合理。

