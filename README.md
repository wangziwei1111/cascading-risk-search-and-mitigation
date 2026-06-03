# Cascading Risk Search and Mitigation

公开仓库：

```text
https://github.com/wangziwei1111/cascading-risk-search-and-mitigation
```

本仓库用于“电力系统连锁故障风险识别与实时缓解”的代码复现和论文实验整理。

## Current Focus

当前主线是复现强化学习论文：

```text
Real-Time Cascade Mitigation in Power Systems Using Influence Graph Improved by Reinforcement Learning
```

本阶段只把 RL 论文复现作为主结果。GCN-RL 闭环、one-step oracle、oracle BC、safe gate、action scan 等只作为诊断或增强实验，不能写成论文原始 PPO 方法结果。

主要产物：

```text
results/rl_mitigation/paper/
docs/rl_paper_reproduction_status.md
docs/rl_paper_figure_index.md
docs/rl_mitigation_extra_diagnostics.md
```

## RL Paper Pipeline

IEEE14 使用 PYPOWER `case14` 的 AC 潮流替代环境，动作空间为全部支路主动断线加 do-nothing，初始故障从 N-1 和共同母线 N-2 场景中采样。IEEE118 当前保留 smoke/framework 级验证，未做完整 600000-step 正式训练。

模式入口：

```powershell
python -m scripts.rl_mitigation.paper.run_ieee14_paper_pipeline --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml --mode smoke
python -m scripts.rl_mitigation.paper.run_ieee14_paper_pipeline --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml --mode medium
python -m scripts.rl_mitigation.paper.run_ieee14_paper_pipeline --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml --mode formal
```

`--mode smoke|medium|formal` 会分别生成 `_smoke`、`_medium`、无后缀正式产物。`--steps` 和 `--eval-episodes` 可以覆盖默认训练步数和评估场景数。

总 pipeline：

```powershell
python -m scripts.rl_mitigation.paper.run_rl_paper_reproduction_pipeline --mode smoke
```

## Current Result Boundary

当前 smoke/medium-reduced 运行已经证明复现管线、do-nothing 预训练、PPO 训练、评估一致性检查、Figure 7/8 文件命名和 claim check 可以闭环运行。

但 IEEE14 PPO 性能结论仍不能写成完整数值复现。claim check 采用严格规则：只有 `mean_negative_return`、`mean_num_line_outages`、`mean_load_shed_MW` 都严格改善且 `pf_failed_ratio` 不升高，才算 `fully_supported`。

正式论文结论需要继续运行：

```powershell
python -m scripts.rl_mitigation.paper.run_ieee14_paper_pipeline --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml --mode formal
python -m scripts.rl_mitigation.paper.train_ieee14_gridsearch --config configs/rl_mitigation/paper/ieee14_paper_gridsearch.yaml --mode formal
```

验证：

```powershell
pytest tests/rl_mitigation/paper -q
```
