# PIO-GCN 阶段性汇报简稿

老师您好，目前连锁故障搜索这条线已经完成了一个 RTS-79 小系统的阶段性版本。主要工作是：先做了一个按论文逻辑运行的改进 OPA 连锁故障仿真器，再用 GCN 对有序 N-2 故障路径进行快速排序。这里的 N-2 不是同时断两条线，而是“断一条、系统稳定、再断下一条”，保护动作导致的后续跳闸不受 R=2 限制。

当前方法叫 PIO-GCN PathRank。它保留原始 `GCN_path_prob` 思路，不覆盖旧方法，但把输入特征从较弱的 paper 4 维特征扩展成更贴近电力物理的支路特征，例如潮流负载率、保护裕度、安全裕度、线路在线状态和候选状态。同时实现了 candidate mask、original physics loss、pairwise rank-loss 和 JSON measured-state interface。需要说明的是，这只是 JSON 状态更新接口，尚未连接现场 SCADA/PMU 量测系统。

核心 preliminary 结果如下，测试为 RTS-79、3 个 full-truth seeds：

| 方法 | Top-20 | Top-50 | Top-100 | Recall@100 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank physics-enhanced features | 12.00 | 19.00 | 23.33 | 0.421 |
| weak paper GCN_path_prob | 5.67 | 7.00 | 8.00 | 0.144 |
| LODF_yP | 2.00 | 8.00 | 11.67 | 0.210 |
| oracle 上界 | 20.00 | 50.00 | 55.33 | 1.000 |

消融结果表明，目前最主要的提升来自 physics-enhanced features。candidate mask 当前贡献不明显；original physics loss 贡献很小；pairwise rank-loss 对 Top-100 有很小提升，但 Top-20/Top-50 没提升，所以暂时不能说 pairwise rank-loss 已经稳定有效。

当前可信结论是：在 RTS-79 小系统 3-seed preliminary 条件下，物理特征增强的 GCN 排序能明显优于弱 paper GCN 和 LODF_yP，用较少 Top-K 尝试找到更多关键路径。但这还不是最终论文结论，样本规模和测试 seeds 还需要扩大。

下一步建议是：扩大训练负荷场景和测试 seeds；系统调节 pairwise rank-loss 权重和 margin；做概率校准，避免模型过度预测高风险；再和更强的物理规则、训练更充分的 paper GCN baseline 做对比。
