# IEEE14 Minimal Pipeline Report

- 运行时间: 2026-06-02T20:48:16.584050 -> 2026-06-02T20:56:57.985551
- 配置文件: `configs/rl_mitigation/ieee14_ppo.yaml`
- backend: `pypower_ac`
- rate_a_mode: `scaled_from_base_flow`
- rate_a_scale: `1.15`
- 初始故障模式: `sampled`
- 评估 episodes: `100`

## 关键诊断结论
- action scan 可改善场景比例: 0.6500
- action scan 平均最佳改善量: 6.0947
- PPO agent 主动断线次数均值: 0.0600
- PPO argmax 为 do-nothing 的比例: 0.9700
- do-nothing / PPO / one-step oracle 平均 negative_return: 80.1597 / 80.1271 / 74.0650
- 结论: 当前 PPO 已产生非零主动动作，并相对 do-nothing 有改善；one-step oracle 仅作为诊断上界。

## Before/After Summary
- do_nothing 平均 negative_return: 80.1597
- do_nothing 平均 num_generations: 1.1700
- do_nothing 平均 num_line_outages: 4.7700
- do_nothing 平均 load_shed_MW: 11.6045
- agent 平均 negative_return: 80.1271
- agent 平均 num_generations: 1.1700
- agent 平均 num_line_outages: 4.7900
- agent 平均 load_shed_MW: 11.6879
- agent 平均主动断线次数: 0.0600
- agent 平均无效动作次数: 0.0000

## 高风险场景 Top5
- rank 1: outages=3,7, type=common_bus_N-2, negative_return=113.81365184335915
- rank 2: outages=16, type=N-1, negative_return=113.69208593503843
- rank 3: outages=3,8, type=common_bus_N-2, negative_return=112.92166482601984
- rank 4: outages=3,8, type=common_bus_N-2, negative_return=111.99744318362917
- rank 5: outages=6,8, type=common_bus_N-2, negative_return=111.99731654228425

## 图表路径
- `results/rl_mitigation/ieee14/figures/fig7_learning_curves_gridsearch.png`
- `results/rl_mitigation/ieee14/figures/fig_ieee14_survival_negative_return_100.png`
- `results/rl_mitigation/ieee14/figures/fig_action_improvement_distribution.png`
- `results/rl_mitigation/ieee14/figures/fig_oracle_vs_do_nothing_vs_agent_survival.png`
- `results/rl_mitigation/ieee14/figures/fig_policy_action_probability.png`

## 复现边界
本实验基于 PYPOWER IEEE14、surrogate chronics 和文档化容量校准，只用于检验 IEEE14 缓解模块可信度；不得声称精确复现原论文 Figure 7/8 数值。