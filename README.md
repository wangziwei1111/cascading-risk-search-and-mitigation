# Cascading Risk Search and Mitigation

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
```

`pypower_ac` 后端基于 PYPOWER/MATPOWER `case14` 做 AC 潮流，动作空间对应 20 条 branch：`A=0` 为 do-nothing，`A=i` 为主动断开第 `i` 条 branch。

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
python -m scripts.rl_mitigation.evaluate_policy --case ieee14 --episodes 100 --with-agent --without-agent
python -m scripts.rl_mitigation.make_figures --case ieee14
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
  eval_before_after_100.csv
  metrics_summary_100.json

results/rl_mitigation/ieee14/figures/
  fig_ieee14_learning_curve_smoke.png/pdf/csv
  fig_ieee14_survival_negative_return_100.png/pdf/csv
```

## 论文写作边界

当前版本可称为“IEEE14 小系统方法机制复现”或“IEEE14 小系统复现实验框架”。由于论文原始 chronics、随机种子和 grid2op 环境细节不可得，不应声称数值完全复现论文 Figure 7/8。差异记录见：

```text
docs/rl_mitigation_reproducibility_gaps.md
```
