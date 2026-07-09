# IEEE118 Experiment Synthesis

本文档整合 PR #11 到 PR #18 的 IEEE118 实验主线。它只做归档、解释和 compact result synthesis，不新增模型、不新增搜索算法、不重跑 OPA、不重训 GCN，也不改变 Algorithm 1、`strict_path_prob`、`second_only`、`alpha_path_prob`、`fragility_path_prob` 或 `strict_fragility_path_prob` 的公式。

## 1. Why IEEE118 Is Harder Than RTS-79

IEEE118 的 ordered N-2 搜索空间比 RTS-79 更大，并且在 `flow_scaled=8.00, min_rate_a=1.0` 的 stress setting 下，relay-cascade 是关键路径的重要机制。采用 first-step critical early-stop 后，正式有效路径空间为 32,560 条，其中 critical paths 为 1,754 条，relay-cascade paths 为 1,643 条。这个任务仍然稀疏，但关键路径数量和机制复杂度都显著高于 RTS-79 的复现实验。

更关键的是，IEEE118 的 `strict_path_prob = p_shed(Li|S0) * p_shed(Lj|S1)` 受 S0 first-step direct-shed probability 限制。early-stop 协议已经排除了第一步主动故障后直接切负荷的线路，因此有效 N-2 路径中的第一条线路往往不是 S0 direct-shed positive。换言之，`p_shed(Li|S0)` 学到的是“一步后直接切负荷风险”，而论文搜索实际需要的是“Li 是否把系统推入脆弱 S1 状态”。这两个物理含义不完全一致，是 IEEE118 不如 RTS-79 夸张的主要原因。

因此，当前 IEEE118 结果不能写成“复现了 RTS-79 里 50 次尝试找到几乎全部 critical paths 的效果”。更准确的结论是：严格复用 RTS-79 GCN 后，IEEE118 上的 paper-aligned pilot 明显强于 random、LODF_yP 和 PFW，但受 S0 probability bottleneck 限制，提升幅度低于 RTS-79。

## 2. Formal Early-Stop Protocol

PR #11 建立了当前 IEEE118 ordered N-2 的正式 early-stop 协议。第一条主动故障如果已经造成 critical/direct shed，则该 first-line 下所有 `Li -> Lj` 有序 N-2 路径不再继续展开，避免把“一阶已失败”的路径混入二阶搜索真值。

正式统计为：

- first-step critical lines: 10
- skipped `Li -> Lj` paths: 1,850
- valid ordered N-2 paths after early stop: 32,560
- valid critical paths: 1,754
- valid relay-cascade paths: 1,643
- valid critical ratio: 5.38698%
- max total load shed: 111.760638 MW
- first-step critical lines: `L016, L047, L051, L061, L096, L147, L180, L181, L183, L184`

这是后续 IEEE118 搜索效率评估的正式协议基础。

## 3. Paper-Aligned Pilot-2000 Result

PR #13 只完成了 12-state smoke，用于验证 S0/S1 paper-aligned dataset builder、trainer、evaluator 和 tests 能跑通。它不能作为正式结果。

PR #14 是目前最接近原 RTS-79 paper-aligned 设置的 IEEE118 pilot-2000 结果：模型严格复用 `PaperStyleRts79Gcn`，训练数据采用 S0/S1 multi-state paper-aligned 格式，但规模仍是 pilot-2000，不是 paper-8000。

pilot-2000 classification 结果：

- overall AP: 0.878658
- F1: 0.610405
- validation AP: 0.865178
- test AP: 0.860736
- S0 AP: 0.513846
- S1 AP: 0.880911

held-out seed 20260708 搜索结果显示，`strict_path_prob` 明显优于 random、LODF_yP 和 PFW，但 `second_only` 更强：

| Method | K=1000 hits | K=5000 hits | Positioning |
|---|---:|---:|---|
| random | 55.4 | 272.9 | stochastic baseline |
| line_order | 56 | 275 | weak deterministic baseline |
| LODF_yP | 58 | 275 | physical baseline |
| PFW | 66 | 265 | physical baseline |
| strict_path_prob | 360 | 1185 | paper-aligned pilot |
| second_only | 661 | 1705 | diagnostic ablation |

这个结果说明 paper-aligned GCN 确实捕捉到了有用排序信息，但也暴露了 S0 first probability 的瓶颈。

## 4. S0 Bottleneck Diagnosis

PR #15 解释了为什么 `strict_path_prob` 被 `p_first` 压低。核心发现：

- suppressed critical union: 313
- Class A: 180
- Class B: 203
- K=1000 second_only-only critical hits: 500
- K=1000 path_prob-only critical hits: 199
- second_only-only mean `p_first`: 0.027451
- second_only-only mean `p_second`: 0.992166
- path_prob-only mean `p_first`: 0.570718
- valid N-2 paths with first-step positive S0 label: 0 / 32,560
- relay_cascade suppressed ratio: 0.189897
- island_only suppressed ratio: 0.009009

这说明许多 critical paths 在第一步并不会直接切负荷，但会让系统进入脆弱 S1 状态；第二步候选线路的风险非常高。relay-cascade 路径尤其容易被 `p_first` 硬乘法门控压低。

这个发现是机制诊断，不是新方法。

## 5. Ranking Refinement: Alpha Path Probability

PR #16 基于 S0 bottleneck 测试了校准排序：

```text
score_alpha = (epsilon + p_first)^alpha * p_second
```

当 `alpha < 1` 时，`p_first` 的硬门控被放松。核心结果：

| Method | K=1000 hits | K=5000 hits | Positioning |
|---|---:|---:|---|
| strict_path_prob | 360 | 1185 | original paper-style pilot score |
| second_only / alpha0 | 661 | 1705 | diagnostic ablation |
| best alpha | 661 | 1710 | calibrated ranking improvement |
| random mean | 55.4 | 272.9 | baseline |
| LODF_yP | 58 | 275 | baseline |
| PFW | 66 | 265 | baseline |

`alpha_path_prob` 说明降低 `p_first` 的硬门控可以改善低预算排序，但它不是原论文主方法，而是 IEEE118 特定诊断后的 calibrated ranking improvement。

## 6. First-Line Fragility Experiments

PR #17 尝试学习 first-line fragility，但 any-critical label 退化为全正：

- known first-line labels: 1,461
- positive: 1,461
- negative: 0
- positive ratio: 1.0

因此 any-critical fragility 方向有启发，但该 label 不能作为最终 discriminative fragility classifier。

PR #18 用严格 top-q 目标修复 label 退化：

- 12 个 strict targets 全部 non-degenerate
- top10: 156 positive / 1305 negative, positive ratio 10.6776%
- top20: 302 positive / 1159 negative, positive ratio 20.6708%
- top30: 448 positive / 1013 negative, positive ratio 30.6639%
- first-step critical excluded: 158

搜索对比：

| K | best strict | best alpha | second_only | any-critical fragility |
|---:|---:|---:|---:|---:|
| 100 | 95 | 94 | 94 | 87 |
| 500 | 469 | 469 | 469 | 372 |
| 1000 | 676 | 661 | 661 | 673 |
| 5000 | 1709 | 1710 | 1705 | 1706 |

strict fragility targets 修复了全正标签问题，并在 K=100 / K=1000 略优，但没有全面超过 best alpha。因此它应被定位为 diagnostic refinement，而不是主方法突破。

## 7. Recommended Paper Narrative

在 IEEE118 early-stop ordered N-2 设置中，严格复用 RTS-79 GCN 的 path-probability 搜索已经显著优于 random、LODF_yP 和 PFW，但其提升幅度低于 RTS-79 原始案例。进一步诊断表明，该差异主要来自 first-step probability 的物理含义不匹配：early-stop 后的有效 N-2 路径均排除了第一步已直接切负荷的线路，因此 `p_shed(Li|S0)` 实际学习的是一阶直接切负荷风险，而不是 Li 将系统推入脆弱 S1 状态的能力。IEEE118 中大量关键路径呈现 low-p_first / high-p_second 特征，尤其集中于 relay-cascade 机制。基于该诊断，本文进一步测试了 alpha path-probability 和 strict first-line fragility targets。结果显示，降低或替代 `p_first` 的硬乘法门控能够改善低预算排序效果，但这些方法应作为 IEEE118 特定诊断性改进，而非原文主方法的替代。

## 8. What Remains Unfinished

- paper-8000 级别的 IEEE118 训练尚未完成。
- full multi-seed strict fragility truth table 尚未完成。
- 更大规模系统的训练和搜索评估尚未完成。
- Algorithm 1 with fully trained multi-state model 尚未系统验证。
- strict fragility refinement 暂未全面超过 best alpha。
- 当前结果不应写成“IEEE118 已完全复现 RTS-79 的夸张搜索效果”。

