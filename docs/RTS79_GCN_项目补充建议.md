# RTS-79 GCN 连锁故障搜索项目补充建议

## 1. 补充定位

当前项目已经完成了对论文 *Searching for Critical Power System Cascading Failures With Graph Convolutional Network* 中 IEEE RTS-79 案例的核心复现：顺序 OPA 仿真器、支路级 GCN、`reachable` 标签训练、以及 `GCN_path_prob` 在线搜索策略。

如果跳出原文，本项目可以进一步从“论文复现”扩展为“连锁故障风险搜索与解释平台”。补充重点不再是证明 GCN 是否能复现 Fig. 5，而是回答三个更工程化的问题：

1. 哪些故障路径真正值得调度人员优先关注？
2. 模型为什么认为这些路径危险？
3. 在参数、负荷、保护阈值或搜索预算变化时，结论是否稳定？

## 2. 可新增的项目主线

### 2.1 从“找全关键路径”扩展到“风险排序”

当前评估指标主要是 `attempts_to_find_all`、前 50/100/200/500 次搜索找到多少关键路径。这适合复现论文，但实际应用中，调度人员更关心有限预算内的高风险路径。

建议新增路径风险评分：

```text
Risk(L_i -> L_j) = P(load_shed | L_i -> L_j) * E(load_shed_MW | L_i -> L_j)
```

其中：

- `P(load_shed | path)`：路径导致切负荷的概率或模型预测概率。
- `E(load_shed_MW | path)`：该路径一旦发生后的期望切负荷量。
- `Risk`：兼顾“会不会出事”和“出事有多严重”。

这样项目可以从二分类搜索升级为风险优先级排序。后续结果表不只报告“找到了多少条”，还可以报告：

- Top-K 路径覆盖了多少 MW 切负荷风险；
- Top-K 中最大、平均、分位数切负荷量；
- 高概率低损失路径与低概率高损失路径的差异。

### 2.2 增加严重度标签，而不仅是 reachable 标签

当前 `reachable` 标签回答的是：在剩余主动故障深度内是否可以到达切负荷事件。这是一个很有用的标签，但它把 1 MW 和 500 MW 的切负荷都压成了正样本。

建议新增两个监督目标：

```text
classification target: whether load shedding occurs
regression target: total_load_shed_mw
```

或者分级标签：

```text
0 = no shedding
1 = small shedding
2 = medium shedding
3 = severe shedding
```

这样可以训练多任务 GCN：

```text
GCN encoder
├── reachable head: classification
└── severity head: regression or ordinal classification
```

项目价值会从“快速找关键路径”提升为“快速找严重关键路径”。

### 2.3 引入不确定性与鲁棒性分析

原文使用负荷扰动：

```text
gamma_i ~ U[0.9, 1.1]
P_D,i_new = 1.1 * gamma_i * P_D,i
```

当前复现已经使用 5 个测试种子验证了趋势。建议进一步做鲁棒性矩阵：

```text
beta ∈ {1.1, 1.2, 1.3, 1.4}
load_scale ∈ {1.0, 1.1, 1.2}
security_limit ∈ {0.9, 1.0}
```

输出可以包括：

- 每组参数下的 critical path 数量；
- GCN_path_prob 相对 LODF_yP 的加速倍数；
- Top-100 搜索覆盖率；
- 不同参数下反复出现的高风险支路对。

这部分能回答“结论是不是只在 beta=1.2 下成立”。如果要写成论文或课程项目，这会明显增强可信度。

### 2.4 增加可解释性模块

原文提到使用 Layerwise Relevance Propagation 解释 GCN。当前项目主线更关注复现搜索效率，可解释性还可以补上。

建议做两层解释：

1. 路径级解释：为什么 `L_i -> L_j` 被排在前面。
2. 支路级解释：哪些相邻支路、潮流、负荷或拓扑状态推动了模型判断。

可落地的简化版本：

- 对每条 Top-K 路径保存 `x_t, x_p, x_b, x_l`；
- 统计 GCN 高分路径中最常出现的支路、母线、过载指标；
- 对比 `GCN_path_prob` 与 `LODF_yP` 排序差异，解释 GCN 为什么能提前发现 LODF 排不到前面的路径。

如果暂时不实现 LRP，也可以先实现“特征贡献诊断表”，例如：

```text
path, score, total_load_shed_mw, first_fault, second_fault,
max_x_p_before_first, max_x_p_after_first, islanding, redispatch_shed,
top_related_branches
```

### 2.5 从单系统 RTS-79 扩展到跨系统泛化

当前复现只考虑 IEEE RTS-79，这是合理的第一阶段。但项目后续可以补一个“小规模泛化实验”：

- 在 RTS-79 上训练，在不同负荷分布下测试；
- 在 RTS-79 的不同参数设置上训练与测试；
- 若数据接口允许，再扩展到 IEEE 39-bus 或 IEEE 118-bus。

不一定一开始就追求跨系统迁移。更现实的第一步是“同系统、跨运行工况泛化”，即训练集和测试集采用不同负荷强度、不同 beta 或不同安全约束。

## 3. 建议新增实验

### 3.1 搜索预算实验

当前 5 个种子的均值结果为：

```text
GCN_path_prob:
  attempts_to_find_all = 68.2
  found_after_50 = 47.0 / 56.6
  found_after_100 = 56.6 / 56.6

LODF_yP:
  attempts_to_find_all = 1259.8
  found_after_50 = 7.6 / 56.6
  found_after_100 = 11.8 / 56.6
```

建议补充“固定预算下的收益”：

```text
budget ∈ {10, 20, 50, 100}
metric = found_critical_paths / total_critical_paths
metric = found_load_shed_mw / total_load_shed_mw
```

这样更贴近在线安全评估场景，因为实际系统不会等到搜索完所有路径。

### 3.2 严重路径优先实验

将 critical path 按 `total_load_shed_mw` 分成若干档：

```text
small: 0 < shed <= 50 MW
medium: 50 < shed <= 150 MW
large: shed > 150 MW
```

比较不同搜索策略在前 K 次搜索中找到的大事故路径数量。这个实验可以检验 GCN 是否只是找到“会切负荷”的路径，还是能优先找到“严重切负荷”的路径。

### 3.3 消融实验

当前 GCN 输入特征为：

```text
X_GCN = [x_t, x_p, x_b, x_l]
```

建议做特征消融：

```text
without x_t
without x_p
without x_b
without x_l
only x_t + x_p
only x_b + x_l
```

对比指标：

- validation F1；
- Top-50 critical path 覆盖率；
- attempts_to_find_all；
- 高风险路径排序稳定性。

这能解释模型到底依赖拓扑状态、保护裕度、潮流，还是负荷信息。

### 3.4 阈值敏感性实验

当前搜索使用 `gcn_threshold = 0.5`。建议补充：

```text
gcn_threshold ∈ {0.1, 0.3, 0.5, 0.7, 0.9}
```

观察：

- 低阈值是否提高覆盖但引入更多误报；
- 高阈值是否减少搜索但漏掉关键路径；
- `GCN_path_prob` 是否比单点阈值更稳定。

## 4. 建议新增输出文件

建议在 `outputs/` 下新增统一的项目补充结果目录：

```text
outputs/project_extension/
├── risk_ranking/
│   ├── top_paths_by_probability.csv
│   ├── top_paths_by_shed_mw.csv
│   └── top_paths_by_expected_risk.csv
├── robustness/
│   ├── beta_sensitivity_summary.csv
│   ├── load_scale_sensitivity_summary.csv
│   └── robustness_heatmap.png
├── ablation/
│   ├── feature_ablation_metrics.csv
│   └── feature_ablation_search_summary.csv
└── interpretability/
    ├── top_path_explanations.csv
    └── recurring_high_risk_branches.csv
```

## 5. 可写入报告的补充段落

可以在原复现报告的“讨论”后新增如下内容：

```text
在完成论文 RTS-79 案例复现后，本项目进一步将研究目标从“复现 GCN 加速搜索现象”扩展为“面向在线安全评估的高风险连锁故障路径识别”。原论文主要关注在有限搜索次数内发现尽可能多的 critical cascading failure paths，而实际调度场景还需要区分不同路径的事故严重程度、解释模型排序原因，并验证模型在不同负荷水平、保护阈值和安全约束下的稳定性。

因此，后续工作可在现有顺序 OPA 仿真器和支路级 GCN 框架基础上，增加路径风险评分、切负荷严重度预测、参数鲁棒性分析和可解释性诊断。特别地，可将路径风险定义为切负荷发生概率与切负荷规模的组合，使搜索目标从二分类意义上的“是否关键”进一步转向工程意义上的“是否高风险”。这将使本项目不再局限于论文 Fig. 5 的复现，而具备进一步发展为连锁故障风险评估工具的基础。
```

## 6. 推荐优先级

如果时间有限，建议按以下顺序推进：

1. 固定搜索预算实验：最快体现项目价值，直接服务在线搜索场景。
2. 严重度统计：利用现有仿真输出即可做，不一定马上重训模型。
3. 参数鲁棒性分析：提升结论可信度，适合写报告。
4. 特征消融：解释 GCN 为什么有效。
5. 多任务 GCN：工作量最大，但最有研究增量。

## 7. 一句话总结

原文证明了 GCN 可以加速关键连锁故障搜索；本项目后续可以进一步证明：GCN 不仅能更快地找路径，还能帮助识别更严重、更稳定、更可解释的系统风险。
