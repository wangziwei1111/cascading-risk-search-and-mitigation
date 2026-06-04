# PIO-GCN 阶段性汇报简稿

老师您好，目前连锁故障搜索这条线已经完成了一个 RTS-79 小系统的阶段性版本。核心工作是：先做了按顺序故障逻辑运行的改进 OPA 连锁故障仿真器，再用 GCN 对有序 N-2 故障路径做快速排序。这里的 N-2 是“先断一条，系统完成保护、孤岛处理和再调度后，再断下一条”，不是两条线同时断开。

当前方法叫 PIO-GCN PathRank。它保留原始 `GCN_path_prob`，没有覆盖旧方法；主要改进是把输入从较弱的 paper 4 维特征扩展为 physics-enhanced features，例如潮流负载率、线路在线状态、安全裕度、保护裕度和候选状态。同时实现了 candidate mask、original physics loss、pairwise rank-loss 和 JSON measured-state interface。需要强调：这只是 JSON measured-state interface，不是现场 SCADA/PMU 接入。

核心 3-seed RTS-79 full-truth preliminary result 如下：

| 方法 | Found@20 | Found@50 | Found@100 | Recall@100 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 12.00 | 19.00 | 23.33 | 约 0.421 |
| weak paper `GCN_path_prob` | 5.67 | 7.00 | 8.00 | 约 0.144 |
| LODF_yP | 2.00 | 8.00 | 11.67 | 约 0.210 |
| oracle 上界 | 20.00 | 50.00 | 55.33 | 1.000 |

消融结果说明，目前最主要提升来自 physics-enhanced features。candidate mask 当前贡献不明显；original physics loss 贡献很小；pairwise rank-loss 对 Top-100 有轻微变化，但 Top-20/Top-50 没有提升，所以不能说 rank-loss 已经稳定有效。

后续又做了 5-seed full-truth 扩展检查。PIO-GCN 在 Top-20/50/100 仍优于 stronger paper baseline；但到 Top-200，strong paper baseline 的 recall 约 0.568，PIO-GCN 约 0.521。这说明 PIO-GCN 更适合前排快速筛选，不能简单宣称所有 Top-K 都更好。

新能源部分已完成 synthetic renewable perturbation full-truth preliminary：3 个 seeds，新能源渗透率 0.30。PIO-GCN 的 recall@100 约 0.426，strong paper baseline 约 0.379，LODF_yP 约 0.076。这个结果只说明合成新能源扰动下方法仍可运行，不能等同于真实新能源电网结论。

当前结论不是最终论文结论。下一步建议是扩大训练场景和测试 seeds，补做更充分的 paper baseline，尝试 hard negative mining、路径级排序损失或 score-level ensemble，并进一步验证新能源扰动下的稳定性。

补充性能增强结果：我又在同一批 5 个 full-truth seeds 上做了 ensemble 和 hard-negative rerank。简单 ensemble 能让 Top-100 略升，例如 alpha=0.75 时 recall@100 约 0.444，但 Top-200 仍低于 strong paper baseline。hard-negative rerank 效果更明显，`rerank_physical_stress` 的 recall@100 约 0.532、recall@200 约 0.587，超过原 PIO-GCN 和 strong paper baseline。可以向老师汇报为：当前最有希望的改进方向不是简单融合，而是在 PIO 前排候选中加入物理应力二次排序。

最新又完成了 learned path reranker：把每条有序 N-2 路径作为一个样本，用路径分数、物理应力、继电器裕度和 first-outage stress 特征训练轻量模型。leave-one-seed-out 结果显示，MLP reranker 的 recall@100 约 0.944、recall@200 约 0.997，已经超过设定目标。但这个结果很强，也要谨慎汇报：目前只有 RTS-79 的 5 个 seeds，说明路径级监督学习非常有潜力，但还不能说是最终论文结论。
