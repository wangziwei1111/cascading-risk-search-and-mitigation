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

## Combined Framework

The two modules jointly form:

```text
risk identification -> risk mitigation
```

The GCN module can prioritize dangerous scenarios for offline study and stress testing. The RL module can then learn a real-time intervention policy under those or broader cascade scenarios. The current repository keeps them separate so each contribution remains explainable in the thesis while still supporting later integration.
