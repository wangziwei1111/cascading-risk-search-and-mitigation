# IEEE14 Minimal Pipeline Report

- 运行时间: 2026-06-02T20:20:37.835335 -> 2026-06-02T20:22:41.616774
- 配置文件: `configs/rl_mitigation/ieee14_ppo.yaml`
- backend: `pypower_ac`
- rate_a_mode: `scaled_from_base_flow`
- rate_a_scale: `1.15`
- 初始故障模式: `sampled`
- 评估 episodes: `100`

## Before/After Summary
- do_nothing 平均 negative_return: 80.1597
- do_nothing 平均 num_generations: 1.1700
- do_nothing 平均 num_line_outages: 4.7700
- do_nothing 平均 load_shed_MW: 11.6045
- agent 平均 negative_return: 80.1597
- agent 平均 num_generations: 1.1700
- agent 平均 num_line_outages: 4.7700
- agent 平均 load_shed_MW: 11.6045
- agent 平均主动断线次数: 0.0000
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

## 复现边界
本实验基于 PYPOWER IEEE14、surrogate chronics 和文档化容量校准，不能声称完全复现论文原始 Figure 7/8 数值。