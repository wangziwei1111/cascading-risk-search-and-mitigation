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

`PypowerACBackend` 使用 PYPOWER/MATPOWER `case14`：

- 14 个 bus。
- 20 条 branch。
- branch status 由环境中的 `line_status` 控制。
- AC 潮流通过 `pypower.runpf` 计算。
- 若 `rateA=0` 或缺失，则使用文档化的默认容量。
- 若 AC 潮流不收敛，返回 `converged=False`，环境记录 `pf_failed=True` 并终止 episode。

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

画图入口：

```bash
python -m scripts.rl_mitigation.make_figures --case ieee14
```

## Figure 对应关系

- 论文 Figure 7 方法机制复现：`fig_ieee14_learning_curve_smoke.png/pdf/csv`。
- 论文 Figure 8 方法机制复现：`fig_ieee14_survival_negative_return_100.png/pdf/csv`。

这些图不能声称数值完全复现论文，只能用于 IEEE14 小系统机制复现与毕业论文实验流程展示。
