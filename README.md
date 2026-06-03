# Cascading Risk Search and Mitigation

## Current Focus: RL Paper Reproduction

The current main line is reproducing the reinforcement-learning paper:

```text
Real-Time Cascade Mitigation in Power Systems Using Influence Graph Improved by Reinforcement Learning
```

GCN-RL coupling is paused for the paper-reproduction stage. The paper main results are kept under:

```text
results/rl_mitigation/paper/
```

Diagnostic and enhanced analyses are not paper results. Action-value scans, one-step oracle, oracle BC, safe gate, and GCN-RL bridge outputs must be described only as diagnostics or extra experiments, not as the original PPO method. See:

```text
docs/rl_paper_reproduction_status.md
docs/rl_paper_figure_index.md
docs/rl_mitigation_extra_diagnostics.md
```

Current IEEE14 smoke claim check is cautious: the PYPOWER IEEE14 substitute environment reproduces the MDP/training mechanism, but the PPO mitigation performance claim is only partially supported and should not be overstated.

公开仓库地址：

```text
https://github.com/wangziwei1111/cascading-risk-search-and-mitigation
```

本仓库用于硕士毕业设计中的“电力系统连锁故障风险识别与实时缓解”代码复现和后续整合。

## 模块关系

- `src/gcn_search/`：GCN 关键连锁故障路径搜索模块，回答“哪些故障路径危险”。
- `src/rl_mitigation/`：RL 实时级联故障缓解模块，回答“故障开始传播后如何实时干预”。

二者不是替代关系，而是“风险识别 -> 风险缓解”的前后衔接关系。本轮开发只升级 `src/rl_mitigation/`，不做 IEEE118，也不做 GCN-RL 闭环。

## RL 模块当前状态

IEEE14 小系统实验默认使用：

```yaml
backend: pypower_ac
initial_outages:
  mode: sampled
powerflow:
  rate_a_mode: scaled_from_base_flow
```

`pypower_ac` 后端基于 PYPOWER/MATPOWER `case14` 做 AC 潮流，IEEE14 元数据也统一从 `pypower.case14()` 自动抽取。动作空间对应 20 条 branch：`A=0` 为 do-nothing，`A=i` 为主动断开第 `i` 条 branch。

每个 episode 默认从 N-1 和共同母线 N-2 初始故障池中随机采样一个场景，同时从 surrogate chronics 中抽取负荷/发电快照。线路容量默认使用 `scaled_from_base_flow` 校准，使 IEEE14 小系统在部分初始故障下出现可观测过载和级联传播。该容量校准是小系统机制复现实验设置，不等同于论文原始系统参数。

`surrogate` 后端仍保留，但只用于 debug：

```yaml
backend: surrogate
```

正式 IEEE14 小系统复现实验不应默认使用 surrogate。

## 关键命令

```bash
python -m scripts.rl_mitigation.pretrain_do_nothing --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml
python -m scripts.rl_mitigation.train_ppo --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml --smoke --steps 2048
python -m scripts.rl_mitigation.train_ppo --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml
python -m scripts.rl_mitigation.calibrate_ieee14_cascade_scenarios --config configs/rl_mitigation/ieee14_ppo.yaml
python -m scripts.rl_mitigation.evaluate_policy --case ieee14 --episodes 100 --with-agent --without-agent
python -m scripts.rl_mitigation.make_figures --case ieee14
python -m scripts.rl_mitigation.list_high_risk_ieee14_scenarios --config configs/rl_mitigation/ieee14_ppo.yaml --top-k 50
python -m scripts.rl_mitigation.run_ieee14_minimal_pipeline --config configs/rl_mitigation/ieee14_ppo.yaml --episodes 100 --smoke-steps 2048
python -m scripts.rl_mitigation.export_ieee14_thesis_tables
python -m scripts.rl_mitigation.check_ieee14_results_integrity
pytest tests/rl_mitigation -q
```

## 主要输出

```text
results/rl_mitigation/ieee14/pretrain/
  states_actions.npz
  policy_pretrained_torch.pt

results/rl_mitigation/ieee14/train_logs/
  ppo_clip_train.csv

results/rl_mitigation/ieee14/checkpoints/
  latest.pt
  best.pt

results/rl_mitigation/ieee14/eval/
  eval_scenarios_seed0_episodes100.json
  eval_before_after_100.csv
  metrics_summary_100.json

results/rl_mitigation/ieee14/figures/
  fig7_learning_curves_gridsearch.png/pdf/csv
  fig_ieee14_learning_curve_smoke.png/pdf/csv
  fig_ieee14_survival_negative_return_100.png/pdf/csv

results/rl_mitigation/ieee14/calibration/
  cascade_scenario_stats.csv
  cascade_scenario_summary.json

results/rl_mitigation/ieee14/high_risk/
  high_risk_scenarios_top50.csv

results/rl_mitigation/ieee14/tables/
  table_ieee14_before_after_summary.csv
  table_ieee14_high_risk_top10.csv
  table_ieee14_capacity_calibration.csv
  thesis_table_explanation.md

results/rl_mitigation/ieee14/reports/
  ieee14_minimal_pipeline_report.md
  result_integrity_check.json
```

before/after 评估会先生成固定场景列表，再让 do-nothing 和 PPO agent 在同一批 scenario_id 上运行，保证比较公平。Figure 8 生存函数按 `do_nothing` 和 `agent` 分开计算和绘制，不混合两类策略。

高风险场景清单仅服务后续论文分析和未来与 GCN 风险搜索模块串联；本轮没有实现 GCN-RL 联合闭环。

PPO-clip 已修正 rollout 截断时的 GAE bootstrap：若 rollout 因 `n_steps` 截断但 episode 未结束，会使用 critic 对当前观测的估计值作为 bootstrap value。

## 论文写作边界

当前版本可称为“IEEE14 小系统方法机制复现”或“IEEE14 小系统复现实验框架”。由于论文原始 chronics、随机种子和 grid2op 环境细节不可得，不应声称数值完全复现论文 Figure 7/8。差异记录见：

```text
docs/rl_mitigation_reproducibility_gaps.md
```
## IEEE14 RL 诊断更新

为解释 PPO agent 曾经与 do-nothing 完全一致的问题，仓库新增了动作价值扫描、one-step oracle 上界和策略动作概率诊断：

```bash
python -m scripts.rl_mitigation.scan_ieee14_action_values --config configs/rl_mitigation/ieee14_ppo.yaml --episodes 100
python -m scripts.rl_mitigation.evaluate_oracle_policy --config configs/rl_mitigation/ieee14_ppo.yaml --episodes 100
python -m scripts.rl_mitigation.diagnose_policy_actions --config configs/rl_mitigation/ieee14_ppo.yaml --episodes 100
```

2026-06-02 的 100 episode smoke 结果显示 `better_action_ratio=0.650`、`oracle_gap=6.0947`，说明当前 IEEE14 环境存在优于 do-nothing 的单步主动断线动作；`one_step_oracle` 只作为诊断上界，不能当作部署策略或论文原始结果复现。
## IEEE14 学习机制对比实验

新增 `train/val/test` 固定场景划分、split 版 action scan、oracle BC 初始化、三组 PPO 初始化消融、paired stats 和可改善子集分析。推荐烟雾复现实验命令：

```bash
python -m scripts.rl_mitigation.run_ieee14_learning_pipeline --config configs/rl_mitigation/ieee14_ppo.yaml --smoke --train-steps 2048 --eval-episodes 100
```

当前 100 个 test 场景结果显示：`better_action_ratio=0.600`，`mean_best_improvement=8.1251`。oracle BC 数据只来自 train split：300 个 train 场景中筛出 185 个 BC 样本，不能使用 test split 做 BC。

结果边界：

- 原论文机制复现主线：MDP 状态、do-nothing 动作、invalid action mask、PPO 训练、随机 N-1/N-2 初始故障、PYPOWER IEEE14 小系统。
- 诊断上界：action value scan、one-step oracle。
- 增强实验：oracle BC 初始化、可改善子集分析、training ablation。

不要把 oracle BC 说成原论文方法；它只用于回答“训练机制是否能学到 oracle 暗示的缓解动作”。

## Safe Oracle-BC Full 诊断

新增 `oracle_bc_full` 和 `safe_oracle_bc_full`：

- `oracle_bc_full` 对 train split 全部 scenario 生成标签：可改善场景学 best action，不可改善场景学 do-nothing。
- `oracle_bc_positive_only` 保留为消融反例，它缺少 do-nothing 负样本，容易盲目主动断线。
- `safe_oracle_bc_full` 使用 val split 调出的概率门控，只在主动动作概率和 margin 达标时执行非零动作。

入口：

```bash
python -m scripts.rl_mitigation.run_ieee14_safe_bc_pipeline --config configs/rl_mitigation/ieee14_ppo.yaml --eval-episodes 100
```

报告：

```text
results/rl_mitigation/ieee14/reports/ieee14_safe_bc_pipeline_report.md
results/rl_mitigation/ieee14/tables/table_policy_multi_metric_test_summary.csv
```
