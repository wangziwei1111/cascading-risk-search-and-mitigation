# IEEE RTS-79 连锁故障仿真与 GCN 在线搜索复现报告

## 摘要

本文针对论文 *Searching for Critical Power System Cascading Failures With Graph Convolutional Network* 中的 IEEE RTS-79 小系统实验，复现了基于改进 OPA 流程的连锁故障仿真器，并训练图卷积网络 GCN（Graph Convolutional Network，图卷积网络）用于关键连锁故障路径搜索。复现中只考虑 IEEE RTS-79 系统，不复现河南省电网案例。仿真模型采用 DCOPF（DC Optimal Power Flow，直流最优潮流）、DCPF（DC Power Flow，直流潮流）、保护继电器动作、孤岛切负荷和再调度 OPF（Optimal Power Flow，最优潮流）构成。主动故障次数上限取 `R = 2`，但保护动作导致的后续支路跳闸不受 `R` 限制。

训练阶段使用 800 个负荷场景生成 Step2-State 数据集，即 Algorithm 1（算法 1）中每一步在线搜索面对的当前运行状态。最终采用 `reachable GCN + GCN_path_prob` 作为主线搜索策略，其中 `reachable` 表示候选支路在剩余 `R = 2` 主动故障深度内是否可达切负荷事件，`GCN_path_prob` 表示用路径级概率分数对所有有序 `N-2` 路径进行全局排序。5 个测试负荷场景下，平均关键路径数为 56.6 条，`GCN_path_prob` 平均 68.2 次搜索即可找全全部关键路径，前 50 次平均找到 47.0 条，前 100 次全部找完。该结果已接近原文 Fig. 5（图 5）所展示的快速搜索量级。

## 1. 复现目标与系统设置

本复现的目标是建立一个稳定的 IEEE RTS-79 连锁故障仿真器，并在该仿真器上复现 GCN 辅助搜索关键连锁故障路径的主要机制。

系统采用 PYPOWER 中的 IEEE 24-bus RTS 数据：

```text
母线数 = 24
支路数 = 38
发电机数 = 33
```

本文中支路按 `L01, L02, ..., L38` 编号，母线按 `B01, B02, ..., B24` 编号。

固定参数如下：

```text
R = 2
β = 1.2
security_limit = 1.0
L_m^max = RATE_A
```

中文释义如下：

- `R`：主动施加的随机初始支路故障次数上限。
- `β`：保护继电器动作阈值参数。
- `security_limit`：再调度安全约束系数。
- `L_m^max`：第 `m` 条支路最大允许潮流。
- `RATE_A`：RTS-79 数据中给出的支路长期额定容量。

需要强调的是，`R = 2` 只限制主动故障次数，不限制保护继电器因过载自动切除的后续支路数量。

## 2. 负荷场景建模

按照论文 RTS-79 实验中的负荷不确定性设定，每个母线负荷乘以均匀分布随机因子，并整体放大 1.1 倍：

```text
γ_i ~ U[0.9, 1.1]
P_D,i^new = 1.1 γ_i P_D,i
```

中文释义如下：

- `γ_i`：第 `i` 个母线的随机负荷扰动因子。
- `U[0.9, 1.1]`：0.9 到 1.1 之间的均匀分布。
- `P_D,i`：第 `i` 个母线原始有功负荷。
- `P_D,i^new`：扰动并整体放大后的新有功负荷。

每个负荷场景生成后，先运行初始 DCOPF，得到初始稳定运行状态 `S0`。

## 3. 连锁故障仿真流程

本文采用顺序 OPA 流程。对一条有序主动故障路径：

```text
L_i -> L_j
```

仿真过程为：

```text
S0
-> 主动断开 L_i
-> 运行 DCPF
-> 检查保护动作
-> 孤岛切负荷
-> 再调度 OPF
-> 得到稳定状态 S1(i)
-> 主动断开 L_j
-> 运行 DCPF
-> 检查保护动作
-> 孤岛切负荷
-> 再调度 OPF
-> 得到最终状态 S2(i,j)
```

保护动作条件为：

```text
loading_ratio_m > β
```

其中：

```text
loading_ratio_m = |L_m| / L_m^max
```

中文释义如下：

- `loading_ratio_m`：第 `m` 条支路负载率。
- `L_m`：第 `m` 条支路潮流。
- `L_m^max`：第 `m` 条支路最大允许潮流。
- `β L_m^max`：保护继电器动作阈值。

再调度 OPF 的目标是最小化总切负荷，同时满足线路安全约束：

```text
|L_m| <= L_m^max
```

若总切负荷满足：

```text
total_load_shed_mw > 0
```

则该有序路径被记录为 critical cascading failure path（关键连锁故障路径）。

## 4. 典型案例核对

### 4.1 `L10 -> L05`

复现结果：

```text
total_load_shed = 149.6 MW
island_load_shed = 149.6 MW
redispatch_load_shed = 0 MW
切负荷母线 = B06
最终断线 = L05, L10
```

中文解释：先断 `L10` 后系统可稳定运行；再断 `L05` 后，`B06` 所在区域形成供电不足孤岛，因此发生孤岛切负荷。

### 4.2 `L27 -> L02`

复现结果：

```text
total_load_shed = 23.0 MW
island_load_shed = 0 MW
redispatch_load_shed = 23.0 MW
切负荷母线 = B03
最终断线 = L02, L27
```

中文解释：该路径不会直接造成孤岛，也不会因 `L06` 超过保护阈值而立即跳闸；但再调度 OPF 为满足线路安全约束，需要削减 `B03` 负荷。

## 5. GCN 输入特征与图结构

论文中的 GCN 不是以母线为节点，而是以支路为图节点。IEEE RTS-79 有 38 条支路，因此 GCN 图包含 38 个节点。如果两条支路共享同一个母线，则两条支路节点之间存在图边。

每个状态的 GCN 输入为：

```text
X_GCN = [x_t, x_p, x_b, x_l]
```

中文释义如下：

- `X_GCN`：GCN 输入特征矩阵。
- `x_t`：拓扑状态，支路断开为 1，在线为 0。
- `x_p`：保护继电器指标，定义为 `|L_k| / (β L_k^max)`。
- `x_b`：支路潮流绝对值。
- `x_l`：支路两端母线中较大的负荷。

对于离线支路：

```text
x_t = 1
x_p = 0
x_b = 0
```

并通过 `loss_mask`（损失掩码）避免其参与训练损失。

特征归一化采用 z-score（标准分数归一化）。`x_t` 保持 0/1，`x_p, x_b, x_l` 按训练集均值和标准差归一化。

## 6. GCN 模型与训练数据

GCN 图卷积核采用论文形式：

```text
G_cf = Σ_{k=0}^{K_GCN} w_cfk A_bar^k
```

归一化邻接矩阵为：

```text
A_bar = D^(-1/2) A D^(-1/2)
```

中文释义如下：

- `G_cf`：从输入通道 `c` 到输出通道 `f` 的图卷积滤波器。
- `K_GCN`：图卷积阶数。
- `w_cfk`：图卷积滤波器权重。
- `A`：支路图邻接矩阵。
- `D`：度矩阵。
- `A_bar`：对称归一化邻接矩阵。

网络结构为：

```text
Graph Convolution 1: 4 -> 16
ReLU
Graph Convolution 2: 16 -> 4
ReLU
Fully Connected: 4 -> 2
Softmax
```

中文释义如下：

- `Graph Convolution`：图卷积层。
- `ReLU`：线性整流激活函数。
- `Fully Connected`：全连接层。
- `Softmax`：归一化分类概率输出。

训练参数为：

```text
epochs = 20
batch_size = 32
learning_rate = 0.005
optimizer = Adam
K_GCN = 3
F1 = 16
F2 = 4
positive_weight = 20
```

中文释义如下：

- `epochs`：训练轮数。
- `batch_size`：批大小。
- `learning_rate`：学习率。
- `optimizer`：优化器。
- `positive_weight`：正样本权重。

本复现只训练 `reachable` 标签模型。`reachable` 表示：当前状态下主动断开某条候选支路，在剩余 `R = 2` 主动故障深度内是否可以到达切负荷事件。

800 个负荷场景生成的训练集规模为：

```text
num_states = 31188
num_candidate_labels = 1154756
num_reachable_positive = 61851
reachable_positive_ratio = 5.36%
```

训练结果为：

```text
validation total accuracy = 0.9853
validation hit rate = 0.7967
validation cover rate = 0.9825
validation F1 = 0.8799
```

中文释义如下：

- `total accuracy`：总准确率。
- `hit rate`：命中率，即预测为正的样本中真实为正的比例。
- `cover rate`：覆盖率，即真实正样本中被模型捕获的比例。
- `F1`：命中率和覆盖率的调和平均。

## 7. 在线搜索算法

最初采用节点级 `GCN_prob` 排序，即：

```text
先按 p_shed(L_i | S0) 排第一故障
再对每个 L_i 下的第二故障按 p_shed(L_j | S1(i)) 排序
```

该方法属于分层块状搜索，容易在某个第一故障下搜索大量非关键第二故障，导致搜索次数过大。5 个测试场景中，该方法平均需要 927.2 次才能找全关键路径。

最终采用路径级全局排序：

```text
GCN_path_prob
```

路径分数定义为：

```text
score(L_i -> L_j) = p_shed(L_i | S0) × p_shed(L_j | S1(i))
```

中文释义如下：

- `score(L_i -> L_j)`：有序路径 `L_i -> L_j` 的路径级风险分数。
- `p_shed(L_i | S0)`：初始状态 `S0` 下主动断开 `L_i` 的切负荷可达概率。
- `p_shed(L_j | S1(i))`：第一故障 `L_i` 处理稳定后的状态 `S1(i)` 下，再断开 `L_j` 的切负荷可达概率。

该策略将全部 1406 条有序 `N-2` 路径放在一起全局排序，而不是分块搜索。

## 8. 搜索结果

在 5 个测试负荷场景上，平均结果如下：

```text
平均 critical paths = 56.6
GCN_path_prob 平均找全次数 = 68.2
GCN_path_prob 前 50 次平均找到 = 47.0
GCN_path_prob 前 100 次平均找到 = 56.6
LODF_yP 平均找全次数 = 1259.8
random 平均找全次数 = 1378.0
line_order 平均找全次数 = 1332.6
```

其中：

- `LODF_yP`：基于 LODF（Line Outage Distribution Factor，线路停运分布因子）的物理规则搜索。
- `random`：随机搜索。
- `line_order`：按线路编号顺序枚举搜索。
- `oracle`：理想排序，仅作为上界参考。

结果说明，`GCN_path_prob` 显著提升了搜索效率。虽然本复现中平均关键路径数为 56.6 条，多于原文 RTS-79 案例中约 22 条，但仍能在约 68 次搜索内找全，并在前 100 次搜索内找全全部关键路径。

![RTS-79 search efficiency](C:/Users/24186/Documents/New%20project%207/outputs/rts79_reproduction_package_800_reachable_pathprob/fig5_style_average_search_curve.png)

## 9. 讨论

### 9.1 为什么旧的 `GCN_prob` 需要 900 多次？

旧的 `GCN_prob` 使用节点级分层排序。其问题是：一旦某个第一故障 `L_i` 被排在前面，算法会先搜索该 `L_i` 下面的大量第二故障 `L_j`，再进入下一个第一故障。这种块状搜索会浪费大量搜索次数。

### 9.2 为什么 `GCN_path_prob` 有效？

`GCN_path_prob` 将两步主动故障视为一条完整路径，并用：

```text
p1 × p2
```

近似路径整体风险。这样可以把所有 `L_i -> L_j` 直接全局比较，使真正高风险路径更早进入搜索队列。

### 9.3 和原文 Fig. 5 的关系

原文 Fig. 5 展示了 GCN 引导搜索相对于随机搜索和物理规则搜索的显著加速。本文复现结果也呈现同样趋势：`GCN_path_prob` 曲线在前 100 次内基本达到全部关键路径，而物理规则和随机搜索增长明显较慢。

需要说明的是，本文仿真得到的关键路径数量平均为 56.6 条，高于原文 RTS-79 案例中报告的约 22 条。这可能来自以下差异：

```text
1. critical path 判定口径不同；
2. 是否区分 L_i -> L_j 与 L_j -> L_i；
3. β 或 OPA 细节差异；
4. 负荷场景随机种子差异；
5. 再调度 OPF 约束实现差异。
```

尽管如此，路径级 GCN 搜索已经复现出原文图 5 的主要现象，即 GCN 能够在较少搜索次数内快速发现绝大多数关键连锁故障路径。

## 10. 结论

本文完成了 IEEE RTS-79 小系统连锁故障仿真器与 GCN 在线搜索方法复现。主要结论如下：

1. 顺序 OPA 流程必须按“主动断线、保护动作、孤岛处理、再调度、进入下一步”的顺序实现。
2. `R = 2` 只限制主动故障次数，不限制保护继电器导致的后续跳闸。
3. 使用 800 个负荷场景训练的 `reachable GCN` 具有较高分类性能，验证集 `F1 = 0.8799`。
4. 节点级 `GCN_prob` 排序会导致块状搜索，平均需要 927.2 次才能找全关键路径。
5. 路径级 `GCN_path_prob` 排序显著改善搜索效率，5 个测试场景平均 68.2 次即可找全全部关键路径。
6. 该结果已经接近原文 Fig. 5 所展示的快速搜索量级，可作为 RTS-79 复现的主结果。
