# Thesis Integration Plan

## Current Thesis Boundary Update

For the current writing stage, prioritize the RL paper reproduction. The GCN-RL bridge and IEEE14 GCN risk-ranking extension are paused as thesis integration material, not paper-reproduction evidence.

Recommended wording:

```text
The repository first reproduces the RL paper mechanism: MDP state/action/reward, do-nothing initialization, invalid-action masking, PPO training, IEEE5 DP, IEEE14 PPO, and an IEEE118 smoke framework. Diagnostics such as one-step oracle, oracle BC, safe gate, and GCN-RL bridge are reported separately and are not attributed to the original paper method.
```

## Stage 1: GCN Critical Fault Path Search

Role: rapidly identify high-risk N-k cascading failure paths.

The GCN module solves:

```text
Where is the danger?
```

## Stage 2: RL Real-Time Cascade Mitigation

Role: during cascade propagation, choose do-nothing or a proactive line-opening action to reduce cascade generations, line outages, and load shedding risk.

The RL module solves:

```text
How should we intervene after the danger starts?
```

当前 IEEE14 RL 实验已形成独立最小流水线：容量校准、do-nothing 预训练、PPO-clip smoke 训练、同场景 before/after 评估、高风险场景清单、Figure 7/8 图表和论文表格导出。下一阶段才考虑把 GCN 搜索出的高风险故障路径输入 RL 模块做联合评估。

## Combined Framework

The two modules jointly form:

```text
risk identification -> risk mitigation
```

The GCN module can prioritize dangerous scenarios for offline study and stress testing. The RL module can then learn a real-time intervention policy under those or broader cascade scenarios. The current repository keeps them separate so each contribution remains explainable in the thesis while still supporting later integration.
## IEEE14 Learning-Ablation Integration

For the thesis, report the IEEE14 results in three clearly separated layers:

1. Main reproduction layer: PYPOWER IEEE14, MDP state/action definition, invalid-action mask, PPO training, and sampled N-1/common-bus N-2 contingencies.
2. Diagnostic upper-bound layer: action value scan and one-step oracle. These support the statement that the environment has mitigation opportunity, not that a deployable RL policy has solved it.
3. Enhanced-experiment layer: oracle BC initialization, training ablation, paired statistics, and improvable-subset analysis. These are diagnostic additions and should not be attributed to the original paper.

Current split-level action scan results are suitable for the thesis methodology section:

- train: `better_action_ratio=0.6333`, `mean_best_improvement=8.3791`
- val: `better_action_ratio=0.5600`, `mean_best_improvement=8.2059`
- test: `better_action_ratio=0.6000`, `mean_best_improvement=8.1251`

The current smoke ablation should be described cautiously. It demonstrates the comparison workflow and shows that one-step oracle is beneficial, but it does not yet justify a blanket claim that PPO has learned a stable mitigation policy on the whole test split.

## Safe Oracle-BC Wording

Use the following three-layer wording:

1. Paper-mechanism reproduction: the implementation covers MDP state, full action space, do-nothing, action mask, PPO, N-1/N-2 initial contingencies, and a PYPOWER IEEE14 cascade environment. Plain PPO is not yet stably better than do-nothing on the held-out test split.
2. Diagnostic upper bound: action value scan and one-step oracle show that active line opening has mitigation potential in the environment.
3. Enhanced experiments: oracle_bc_full and safe gate are diagnostic additions. If they improve selected metrics or subsets, write that oracle-assisted initialization and safety gating reveal mitigation potential under enhanced supervision; do not describe them as the original paper method.

The thesis should avoid the claim “PPO significantly mitigates cascade risk” unless paired test-split statistics support it. A safer claim is: “The IEEE14 environment contains actionable mitigation opportunities, while plain PPO remains difficult to train; oracle-assisted and safe-gated diagnostics help identify where mitigation is possible.”
