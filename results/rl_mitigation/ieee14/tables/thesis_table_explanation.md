# IEEE14 小系统实验表格说明

表格基于 PYPOWER IEEE14 小系统、N-1/共同母线 N-2 初始故障采样，以及 scaled_from_base_flow 容量校准得到。before/after 评估使用同一批 scenario，因此可用于比较 do-nothing 与 PPO agent 在负回报、级联代数、断线数和切负荷等指标上的差异。

容量校准脚本推荐的 rate_a_scale 为 `1.3`。该值用于构造小系统压力场景，不等同于论文原始系统参数。

若 one-step oracle 优于 do-nothing 而 PPO agent 未改善，应表述为当前 PPO 训练未能利用可改善动作；one-step oracle 只能作为诊断上界。不要表述为精确复现原论文 Figure 7/8 的数值结果。
## Safe Oracle-BC Full 说明

`oracle_bc_positive_only` 只学习可改善场景的主动动作，容易在不可改善场景盲目动作，因此不作为默认策略。
`oracle_bc_full` 为 train split 每个场景生成监督标签：可改善场景使用 best action，不可改善场景使用 do-nothing。
`safe_oracle_bc_full` 再通过 val split 选择的概率门控限制主动动作。

这些结果属于诊断增强实验，不属于原论文方法。论文中应把它们写成“oracle 辅助初始化与安全门控用于分析训练机制和可缓解子集”，不要写成原论文 PPO 主线结果。
