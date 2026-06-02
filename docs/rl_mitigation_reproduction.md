# RL 实时级联故障缓解复现说明

## 复现范围

本模块复现论文 `Real-Time Cascade Mitigation in Power Systems Using Influence Graph Improved by Reinforcement Learning` 的小系统部分：

- IEEE5 动态规划机制示例。
- IEEE14 PPO 实时缓解实验。

本阶段不做 IEEE118，不做 GCN-RL 联合闭环。

## MDP 定义

状态：

```text
S_t = [l_1, ..., l_n, rho_1, ..., rho_n]
```

其中 `l_i` 表示 branch 是否连接，`rho_i=max(abs(Pf_i), abs(Pt_i))/rateA_i` 表示相对潮流。已经断开的 branch 对应 `rho_i=0`。

动作：

```text
A = 0: do-nothing
A = i: 主动断开第 i 条 branch
```

每一代级联传播最多允许一个主动断线动作。动作空间不提前缩小，也不使用 GCN Top-M 替代完整 20-branch 动作空间。

奖励函数：

```text
R_t = - I_{S_t != S_T}
      - 100 I_fail
      - alpha I_{A_{t-1} != 0}
      - 100(1 - exp(-0.01 N_{g,t}))
      - (L_{t-1} - L_t) / L_{t-1}
```

generation 0 初始故障不计 reward；潮流不收敛时 episode 终止，并触发 `-100` 惩罚。

## IEEE14 AC 潮流后端

默认后端为：

```yaml
backend: pypower_ac
```

IEEE14 系统参数统一来自 PYPOWER/MATPOWER `case14`。`make_ieee14_case()` 默认从 `pypower.case14()` 自动抽取 bus、branch、load、generator 和原始 branch rateA，避免环境元数据与 AC 潮流后端不一致。

`PypowerACBackend` 使用相同的 PYPOWER/MATPOWER `case14`：

- 14 个 bus。
- 20 条 branch。
- branch status 由环境中的 `line_status` 控制。
- AC 潮流通过 `pypower.runpf` 计算。
- 若 `rateA=0` 或缺失，则使用文档化的默认容量。
- 若 AC 潮流不收敛，返回 `converged=False`，环境记录 `pf_failed=True` 并终止 episode。

线路容量支持三种模式：

- `original`：使用 PYPOWER 原始 `rateA`，缺失时用默认容量。
- `default_if_zero`：原始 `rateA>0` 时保留，`rateA=0` 时用默认容量。
- `scaled_from_base_flow`：先运行无故障 AC 潮流，再用 `rateA_i=max(min_rate_a_mw, rate_a_scale * base_abs_flow_i)` 校准容量。

当前 IEEE14 默认使用 `scaled_from_base_flow` 和 `rate_a_scale=1.15`，用于让小系统在 N-1/N-2 初始故障下产生可观测过载传播。该设置不是论文原始容量。

`SurrogatePowerFlowBackend` 仍保留，但只用于 debug，不作为 IEEE14 正式小系统实验默认后端。

## 孤岛识别与发电负荷平衡

`islanding.py` 根据当前 `line_status` 构造网络图并识别连通分量。每个孤岛记录：

- bus 集合；
- branch 集合；
- generator 集合；
- load 集合；
- 平衡前负荷和发电；
- 平衡后负荷和发电；
- 切负荷量。

处理规则：

- 无发电有负荷：该孤岛负荷全部切除。
- 有发电无负荷：该孤岛不贡献负荷，发电下调到 0。
- 发电不足：按比例切负荷，使孤岛功率平衡。
- 发电过剩：按容量比例下调发电。

每次主动断线或随机过载跳闸后，都会重新执行孤岛处理，再运行潮流。

## 初始故障采样

IEEE14 默认配置：

```yaml
initial_outages:
  mode: sampled
  include_n_minus_1: true
  include_common_bus_n_minus_2: true
  fixed: []
```

`mode=fixed` 使用固定初始故障，`mode=sampled` 每个 episode 从 N-1 和共同母线 N-2 池中采样，`mode=none` 仅用于 debug。

每个 episode 的 info、cascade trace、训练日志和评估 CSV 都记录：

- `initial_outages`
- `initial_outage_type`
- `initial_outage_order`
- `chronic_index`
- `load_scale`
- `gen_scale`

## PPO-clip

正式训练入口使用 `src/rl_mitigation/rl/ppo_clip.py`，不是旧 numpy debug PPO。

实现包括：

- PyTorch actor/value MLP。
- actor hidden layers 默认 `[64, 64]`。
- value hidden layers 默认 `[64, 8]`。
- invalid action mask，无效动作 logit 置为 `-1e9`。
- PPO clipped surrogate objective。
- value clipping。
- entropy regularization。
- GAE，默认 `gae_lambda=0.95`。
- checkpoint 保存到 `results/rl_mitigation/ieee14/checkpoints/`。
- CSV 日志保存到 `results/rl_mitigation/ieee14/train_logs/ppo_clip_train.csv`。
- rollout 因 `n_steps` 截断但 episode 未结束时，GAE 使用 critic 的 `last_value` 进行 bootstrap。
- 训练日志记录 `mask_enabled`、`mean_valid_action_count` 和 `sampled_invalid_action_count`。

## do-nothing PyTorch 预训练

入口：

```bash
python -m scripts.rl_mitigation.pretrain_do_nothing --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml
```

流程：

1. 随机 agent 与 IEEE14 环境交互，收集多样化状态。
2. 每个状态标记为 `action=0`。
3. 使用 cross entropy 训练 actor。
4. 加入 entropy regularization，避免完全退化为只输出 do-nothing。
5. 保存：

```text
results/rl_mitigation/ieee14/pretrain/states_actions.npz
results/rl_mitigation/ieee14/pretrain/policy_pretrained_torch.pt
```

## smoke 与正式命令

smoke 命令仍使用真实 PPO-clip 和真实 `pypower_ac` 后端，只是步数较少：

```bash
python -m scripts.rl_mitigation.train_ppo --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml --smoke --steps 2048
```

正式 60000 步训练入口：

```bash
python -m scripts.rl_mitigation.train_ppo --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml
```

评估入口：

```bash
python -m scripts.rl_mitigation.evaluate_policy --case ieee14 --episodes 100 --with-agent --without-agent
```

评估会先生成：

```text
results/rl_mitigation/ieee14/eval/eval_scenarios_seed0_episodes100.json
```

然后让 do-nothing 和 PPO agent 在同一批场景上运行，保证 before/after 比较公平。

画图入口：

```bash
python -m scripts.rl_mitigation.make_figures --case ieee14
```

最小实验流水线：

```bash
python -m scripts.rl_mitigation.run_ieee14_minimal_pipeline --config configs/rl_mitigation/ieee14_ppo.yaml --episodes 100 --smoke-steps 2048
```

论文表格导出：

```bash
python -m scripts.rl_mitigation.export_ieee14_thesis_tables
```

结果完整性检查：

```bash
python -m scripts.rl_mitigation.check_ieee14_results_integrity
```

## Figure 对应关系

- 论文 Figure 7 方法机制复现：`fig_ieee14_learning_curve_smoke.png/pdf/csv`。
- 论文 Figure 7 gridsearch 方法机制复现：`fig7_learning_curves_gridsearch.png/pdf/csv`。
- 论文 Figure 8 方法机制复现：`fig_ieee14_survival_negative_return_100.png/pdf/csv`，其中 do-nothing 和 PPO agent 分开计算生存函数。

这些图不能声称数值完全复现论文，只能用于 IEEE14 小系统机制复现与毕业论文实验流程展示。

## 场景校准与高风险清单

容量校准脚本：

```bash
python -m scripts.rl_mitigation.calibrate_ieee14_cascade_scenarios --config configs/rl_mitigation/ieee14_ppo.yaml
```

输出：

```text
results/rl_mitigation/ieee14/calibration/cascade_scenario_stats.csv
results/rl_mitigation/ieee14/calibration/cascade_scenario_summary.json
```

高风险场景脚本：

```bash
python -m scripts.rl_mitigation.list_high_risk_ieee14_scenarios --config configs/rl_mitigation/ieee14_ppo.yaml --top-k 50
```

输出：

```text
results/rl_mitigation/ieee14/high_risk/high_risk_scenarios_top50.csv
```

该清单可用于后续与 GCN 模块做论文层面的分析衔接，但本轮不实现 GCN-RL 联合闭环。

## 当前 PPO==do-nothing 问题与新增诊断

早期 100 episode 最小流水线曾出现 PPO agent 与 do-nothing 完全一致的现象：

```text
do_nothing negative_return = 80.1597
agent negative_return = 80.1597
agent proactive actions = 0
```

这不能直接解释为“主动断线无效”。当前版本新增了动作价值扫描、one-step oracle 诊断上界和策略动作概率诊断：

```bash
python -m scripts.rl_mitigation.scan_ieee14_action_values --config configs/rl_mitigation/ieee14_ppo.yaml --episodes 100
python -m scripts.rl_mitigation.evaluate_oracle_policy --config configs/rl_mitigation/ieee14_ppo.yaml --episodes 100
python -m scripts.rl_mitigation.diagnose_policy_actions --config configs/rl_mitigation/ieee14_ppo.yaml --episodes 100
```

- `scan_ieee14_action_values.py` 在同一批场景上枚举所有合法初始动作，输出 `action_value_scan_100.csv`、`action_value_summary.json`、动作改善分布图和最佳动作频率图。
- `evaluate_oracle_policy.py` 比较 `do_nothing`、`ppo_agent`、`one_step_oracle`。其中 `one_step_oracle` 只作为诊断上界，不是可部署策略。
- `diagnose_policy_actions.py` 记录初始状态的动作概率、entropy、do-nothing argmax 比例和 top action 频率，用于判断 PPO 是否仍坍缩到 do-nothing。

2026-06-02 的 100 episode smoke 诊断显示：`better_action_ratio=0.650`，`oracle_gap=6.0947`，说明当前 IEEE14 + PYPOWER + N-1/N-2 + scaled_from_base_flow 环境里确实存在优于 do-nothing 的单步主动断线动作；若 PPO 仍接近 do-nothing，应优先归因于探索、预训练偏置、训练步数和奖励尺度，而不是归因于动作空间无改进可能。

当前 do-nothing 预训练不再强制把策略完全压到 do-nothing，而是使用 `target_do_nothing_prob` 和 entropy regularization 保留探索空间。`pretrain_diagnostics.json` 记录 do-nothing 平均概率、非零动作平均概率和 entropy，用于判断预训练是否过度刚性。

可选的 oracle 行为克隆初始化入口为：

```bash
python -m scripts.rl_mitigation.pretrain_oracle_bc --config configs/rl_mitigation/ieee14_ppo.yaml --episodes 100
```

该入口默认关闭，仅用于诊断或消融。使用它时必须说明 oracle BC 使用了动作扫描标签，不能把它和纯 PPO 训练混为一谈。

`evaluate_policy.py` 支持确定性和随机评估：

```bash
python -m scripts.rl_mitigation.evaluate_policy --case ieee14 --episodes 100 --with-agent --without-agent --eval-mode deterministic
python -m scripts.rl_mitigation.evaluate_policy --case ieee14 --episodes 100 --with-agent --without-agent --eval-mode stochastic
```

确定性和随机评估分别写入 `eval_before_after_100_deterministic.csv` 和 `eval_before_after_100_stochastic.csv`；确定性评估还保留兼容文件 `eval_before_after_100.csv`。

最小流水线当前顺序为：容量校准并包含 action scan、固定评估场景生成、动作价值扫描、do-nothing 预训练、PPO smoke 训练、策略动作概率诊断、确定性/随机 before-after 评估、do-nothing/PPO/oracle 三策略评估、高风险场景列表、图表、论文表格、完整性检查和最终报告。

新增图表包括：

- `fig_action_improvement_distribution.png/pdf/csv`
- `fig_oracle_vs_do_nothing_vs_agent_survival.png/pdf/csv`
- `fig_policy_action_probability.png/pdf/csv`

这些诊断图同样不能声称数值完全复现论文 Figure 7/8，只能用于 IEEE14 小系统机制复现、训练诊断和毕业论文实验可信度说明。
