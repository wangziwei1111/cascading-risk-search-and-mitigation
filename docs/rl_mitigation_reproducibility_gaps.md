# RL 缓解模块复现差异记录

当前版本已经从 debug/surrogate 框架升级为 IEEE14 小系统 AC 潮流 + PPO-clip 复现框架，但仍不能声称完全数值复现论文。

## 数据差异

- 论文原始 IEEE14 一周 5 分钟发电/负荷 chronics 当前不可得。
- 本仓库使用 surrogate chronics，包含日内负荷波动、周尺度波动和风电波动。
- 因 chronics 不一致，训练回报曲线和负回报生存函数不能与论文 Figure 7/8 做逐点数值对齐。

## 潮流与环境差异

- 当前正式后端为 PYPOWER/MATPOWER `case14` 的 AC 潮流。
- 论文环境可能基于 grid2op 或其内部系统参数；PYPOWER case14 的 generator、branch rating、负荷分布、保护逻辑可能不完全一致。
- PYPOWER `case14` 原始 branch `rateA` 很大。当前使用 `scaled_from_base_flow` 做容量校准，使 IEEE14 小系统中能观察到过载和级联传播。
- `scaled_from_base_flow` 是文档化的小系统压力校准，不是论文原始容量参数。
- 某些随机断线组合会使 AC 潮流矩阵奇异；环境将其视为 `pf_failed=True`，并触发论文奖励中的潮流失败惩罚。

## 孤岛处理差异

- 当前已实现连通分量识别和发电/负荷平衡。
- 负荷切除和发电下调采用比例规则。
- 若论文原环境有更细粒度的机组爬坡、无功约束或保护动作，本仓库当前未完全覆盖。

## PPO 差异

- 当前已实现 PyTorch PPO-clip、GAE、action mask、value clipping、entropy regularization 和 checkpoint。
- 正式 60000 步训练脚本已提供，但本轮 Codex 验证主要跑 smoke 训练。
- 论文的随机种子、采样初始状态集合和完整 chronics 不可得，因此不能声称训练曲线数值完全一致。

## 初始故障与评估差异

- 当前每个 episode 从 N-1 和共同母线 N-2 初始故障池中采样。
- before/after 评估已经使用同一批场景比较 do-nothing 和 PPO agent。
- 该场景池仍基于 PYPOWER case14 拓扑，不等同于论文原始 grid2op 场景池。
- Figure 8 生存函数已按 do-nothing 和 PPO agent 分开计算，但只能称为方法机制复现。

## surrogate 后端说明

- `SurrogatePowerFlowBackend` 仍保留，仅用于 debug。
- IEEE14 正式小系统复现实验默认后端为 `pypower_ac`。
- 不应把 surrogate 结果写成论文正式复现实验结果。

## 可接受表述

可以表述为：

```text
IEEE14 小系统方法机制复现
IEEE14 AC 潮流环境下的 PPO 实时缓解复现实验
```

不应表述为：

```text
完全复现论文 Figure 7/8 数值结果
完全复现论文原始 grid2op 环境
```
