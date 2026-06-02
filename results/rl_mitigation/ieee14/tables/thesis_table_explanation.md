# IEEE14 小系统实验表格说明

表格基于 PYPOWER IEEE14 小系统、N-1/共同母线 N-2 初始故障采样、以及 scaled_from_base_flow 容量校准得到。before/after 评估使用同一批 scenario，因此可用于比较 do-nothing 与 PPO agent 在负回报、级联代数、断线数和切负荷等指标上的差异。

容量校准脚本推荐的 rate_a_scale 为 `1.3`。该值用于构造小系统压力场景，不等同于论文原始系统参数。

论文中建议表述为：在 PYPOWER IEEE14 小系统环境下，PPO agent 相较 do-nothing 策略在若干指标上表现出缓解效果。不要表述为完全复现原论文 Figure 7/8 的数值结果。
