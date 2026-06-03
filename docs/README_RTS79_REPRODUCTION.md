# IEEE RTS-79 GCN 连锁故障复现说明

## 主线结论

当前 RTS-79 复现主线为：

```text
顺序改进 OPA 仿真器 + reachable GCN + GCN_path_prob 路径级全局排序
```

核心路径分数为：

```text
score(L_i -> L_j) = p_shed(L_i | S0) * p_shed(L_j | S1(i))
```

中文含义：

- `S0`：初始 DCOPF 稳定运行状态。
- `S1(i)`：主动断开 `L_i` 后，经过保护动作、孤岛处理和再调度后的稳定状态。
- `p_shed`：GCN 输出的切负荷可达概率。
- `reachable`：候选支路在剩余 `R = 2` 主动故障深度内是否可达切负荷事件。

## 系统和参数

对象为 IEEE RTS-79 / IEEE 24-bus RTS 小系统：

```text
母线数 = 24
支路数 = 38
发电机数 = 33
```

固定参数：

```text
R = 2
beta = 1.2
security_limit = 1.0
L_m^max = RATE_A
gamma_i ~ U[0.9, 1.1]
P_D,i^new = 1.1 * gamma_i * P_D,i
```

说明：

- `R = 2` 只限制主动施加的初始故障次数。
- 保护继电器动作导致的后续支路跳闸不受 `R` 限制。
- `security_limit = 1.0` 表示再调度 OPF 要满足 `loading_ratio <= 1.0`。
- `beta = 1.2` 表示当 `loading_ratio > 1.2` 时触发保护跳闸。

## 顺序 OPA 流程

有序 N-2 故障不是同时断开两条线路，而是：

```text
S0
-> 主动断开 L_i
-> DCPF 潮流计算
-> 保护动作检查
-> 孤岛切负荷
-> 再调度 OPF
-> 稳定状态 S1(i)
-> 主动断开 L_j
-> 再次执行 DCPF / 保护 / 孤岛 / 再调度
-> 判断是否为关键路径
```

这样做是为了和论文 Algorithm 1 的在线搜索状态一致。

## 训练数据生成

训练集采用 Step2-State 状态生成逻辑：

1. 对每个负荷场景先运行初始 DCOPF，得到 `S0`。
2. 对候选第一故障 `L_i`，运行完整故障后稳定流程。
3. 如果第一故障已经导致切负荷，则记录 `S0` 下 `L_i` 为正样本，不继续生成后续决策状态。
4. 如果第一故障未导致切负荷，则保存 `S1(i)`，继续判断第二步候选支路。
5. 已断开、不在线、孤岛中无效的支路会被 mask，不参与候选主动故障。

当前 800 个负荷场景数据规模：

```text
状态数 = 31,188
候选标签数 = 1,154,756
reachable 正样本数 = 61,851
正样本比例 = 5.36%
```

## GCN 建模

GCN（Graph Convolutional Network，图卷积网络）建模方式：

- 38 条支路作为图节点；
- 两条支路共享同一母线，则建立图连边；
- 输入特征 `X_GCN = [x_t, x_p, x_b, x_l]`；
- `x_t` 表示拓扑状态；
- `x_p` 表示过载风险；
- `x_b` 表示支路容量相关信息；
- `x_l` 表示负荷影响；
- 输出每条候选支路的 `p_shed`，即可达切负荷概率。

当前 reachable GCN 验证结果：

```text
total accuracy = 0.9853
hit rate = 0.7967
cover rate = 0.9825
F1 = 0.8799
```

## 在线搜索结果

5 个测试负荷场景平均结果：

```text
平均关键路径数 = 56.6
GCN_path_prob 平均找全次数 = 68.2
前 50 次平均找到关键路径数 = 47.0
前 100 次平均找到关键路径数 = 56.6
LODF_yP 平均找全次数 = 1259.8
random 平均找全次数 = 1378.0
line_order 平均找全次数 = 1332.6
```

方法对比：

| 方法 | 中文含义 | 找全关键路径所需平均搜索次数 |
|---|---|---:|
| `GCN_path_prob` | 本文方法：路径级 GCN 概率排序 | 68.2 |
| `LODF_yP` | 物理规则排序方法 | 1259.8 |
| `random` | 随机搜索方法 | 1378.0 |
| `line_order` | 按线路编号顺序搜索 | 1332.6 |

结论：

```text
路径级 GCN 将两步故障作为完整有序路径排序，
在保持关键路径覆盖的同时显著减少搜索次数。
```

## 关键文件

仿真器：

```text
src/gcn_search/legacy_rts79/rts79_cascade.py
```

LODF 物理规则：

```text
src/gcn_search/legacy_rts79/rts79_lodf.py
```

Step2-State 数据集生成：

```text
src/gcn_search/legacy_rts79/generate_rts79_step2_state_dataset.py
src/gcn_search/legacy_rts79/generate_rts79_step2_state_worker.py
```

GCN 训练：

```text
src/gcn_search/legacy_rts79/train_rts79_step2_state_gcn.py
src/gcn_search/legacy_rts79/train_rts79_reachable_gcn.py
```

在线搜索评估：

```text
src/gcn_search/legacy_rts79/evaluate_rts79_paper_gcn_search.py
```

结果包生成：

```text
src/gcn_search/legacy_rts79/make_rts79_reproduction_package.py
```

## 当前边界和缺陷

1. 当前只复现 IEEE RTS-79 小系统，尚未扩展到河南省电网或更大系统。
2. 当前模型主要是搜索排序加速器，不是替代物理仿真的独立判别器。
3. 最终路径是否关键仍由 OPA / OPF 仿真器验证。
4. 当前测试场景数量有限，还需要更多随机种子和负荷场景验证稳定性。
5. 原文部分网络超参数和训练细节没有完全公开，当前复现采用了工程上可解释的近似实现。
6. 下一步应加入物理约束和在线实测状态更新机制。
