# Thesis Integration Plan

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
