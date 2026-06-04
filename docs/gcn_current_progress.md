# RTS-79 GCN 连锁故障搜索当前进展

## 一句话版本

当前已经完成 IEEE RTS-79 小系统的改进 OPA 连锁故障仿真器、Step2-State 训练集生成、reachable GCN 训练和路径级在线搜索评估。当前主线方法是 `GCN_path_prob`，即用 GCN 输出的切负荷可达概率对有序 N-2 故障路径进行全局排序，从而快速找到关键连锁故障路径。

## 已完成内容

### 1. RTS-79 改进 OPA 连锁故障仿真器

已经实现的物理流程：

```text
初始 DCOPF
-> 主动支路故障
-> DCPF 潮流计算
-> 保护继电器动作
-> 孤岛切负荷
-> 再调度 OPF
-> 下一次主动支路故障
```

关键设定：

```text
R = 2
beta = 1.2
security_limit = 1.0
L_m^max = RATE_A
```

说明：

- `R = 2` 限制主动故障次数。
- 保护动作导致的后续线路跳闸不受 `R` 限制。
- `security_limit = 1.0` 用于再调度安全约束。
- `beta = 1.2` 用于保护动作阈值。

### 2. 文献案例点核对

已核对的典型路径：

```text
L10 -> L05
L27 -> L02
```

当前仿真能够解释这两类路径中的切负荷机理：

- `L10 -> L05`：对应 B06 附近孤岛切负荷机理。
- `L27 -> L02`：对应 B03 再调度切负荷机理，不是简单孤岛切负荷。

### 3. Step2-State 数据集

数据生成逻辑已经从“同时断两条线”改为“顺序断线 + 每步稳定后再进入下一步”。

800 个负荷场景数据规模：

```text
states = 31,188
candidate labels = 1,154,756
reachable positives = 61,851
positive ratio = 5.36%
```

负荷不确定性：

```text
gamma_i ~ U[0.9, 1.1]
P_D,i^new = 1.1 * gamma_i * P_D,i
```

### 4. reachable GCN

GCN 建模方式：

- 支路作为图节点；
- 共享母线的支路之间建立边；
- 输入特征为 `X_GCN = [x_t, x_p, x_b, x_l]`；
- 输出候选支路的 `p_shed`，即在剩余深度内可达切负荷的概率。

验证结果：

```text
total accuracy = 0.9853
hit rate = 0.7967
cover rate = 0.9825
F1 = 0.8799
```

### 5. 路径级在线搜索

当前最有效策略为：

```text
GCN_path_prob
```

路径分数：

```text
score(L_i -> L_j) = p_shed(L_i | S0) * p_shed(L_j | S1(i))
```

5 个测试负荷场景平均结果：

| 搜索方法 | 中文含义 | 找全关键路径所需平均搜索次数 |
|---|---|---:|
| `GCN_path_prob` | 路径级 GCN 概率排序 | 68.2 |
| `LODF_yP` | 物理规则排序 | 1259.8 |
| `random` | 随机搜索 | 1378.0 |
| `line_order` | 线路编号顺序搜索 | 1332.6 |

平均关键路径数：

```text
56.6
```

前 50 次搜索平均找到：

```text
47.0 条关键路径
```

前 100 次搜索平均找到：

```text
56.6 条关键路径，即基本找全
```

## 当前缺陷

1. 目前只验证了 RTS-79 小系统，尚未迁移到更大规模系统。
2. 当前测试场景仍然偏少，需要更多负荷场景和随机种子验证稳定性。
3. 当前 GCN 是搜索排序器，不是独立物理判别器，最终仍依赖 OPA / OPF 仿真验证。
4. 原文部分训练细节和超参数没有完全公开，因此当前属于核心机制复现，不是逐参数完全复刻。
5. 当前尚未加入严格的物理约束损失函数。
6. 当前还没有真正使用在线实测状态量进行模型更新。

## 导师提出的下一步改进方向

导师希望进一步升级为：

```text
用数据先生成一个模型，
加入物理约束，
在线利用实测状态量更新模型，
用模型 + 小样本驱动计算。
```

可理解为：

```text
离线数据驱动基础模型
+ 物理约束
+ 在线状态更新
+ 小样本物理仿真校验
```

## 建议的新方法名称

中文：

```text
物理约束在线 GCN 连锁故障路径快速搜索方法
```

英文：

```text
Physics-informed Online GCN for Cascading Failure Path Search
```

简称：

```text
PIO-GCN PathRank
```

## 下一步实施计划

### 第一步：加入在线状态量输入

把当前模型输入扩展为：

```text
当前母线负荷
当前发电机出力
当前支路潮流
当前支路状态
当前 loading_ratio
当前拓扑连通关系
```

### 第二步：加入物理约束特征

新增支路特征：

```text
loading_ratio = |P_line| / RATE_A
security_margin = 1.0 - loading_ratio
relay_margin = beta - loading_ratio
is_online
is_candidate
```

### 第三步：加入物理约束损失或输出校正

可加入的约束：

- 已断线路不能作为候选主动故障；
- 不在线支路输出概率应被 mask；
- 潮流越接近 `RATE_A`，风险应越高；
- 超过 `beta * RATE_A` 的线路应进入保护动作逻辑；
- 再调度后应满足 `loading_ratio <= 1.0`。

### 第四步：模型 + 小样本驱动计算

在线阶段不再穷举全部 1406 条路径，而是：

```text
当前实测状态
-> 更新 GCN 输入
-> 输出路径风险排序
-> 选取 Top-K 路径
-> 对 Top-K 路径运行 OPA / OPF 精确仿真
-> 得到关键路径集合
```

可先测试：

```text
Top-K = 20, 50, 100
```

评价指标：

```text
Top-K cover rate
search count
critical path recall
total load shed found
runtime
```

## 给导师的汇报口径

可以这样说：

> 老师，目前已经完成 RTS-79 小系统的改进 OPA 连锁故障仿真器、Step2-State 数据集、reachable GCN 训练和路径级在线搜索。当前 GCN_path_prob 能在 5 个测试场景下平均 68.2 次搜索找全关键路径，而传统物理排序和随机搜索大约需要一千多次。现在的不足是模型还主要是离线排序器，没有显式加入物理约束，也没有用在线实测状态量更新。下一步我准备在现有框架上加入当前负荷、发电、线路潮流、支路状态等在线状态量，并加入容量约束、保护阈值、拓扑 mask 等物理约束，形成“物理约束在线 GCN + Top-K 小样本 OPA 验证”的快速计算框架。

## 物理约束在线 GCN 改进进展

已新增 `PIO-GCN PathRank` smoke 框架：

- 新增 physics 特征：`_make_x_gcn_physics`；
- 数据集生成支持 `feature_mode=paper/physics`，默认仍为 `paper`；
- 新增 candidate probability mask 和物理约束损失；
- 新增 physics-informed GCN 训练入口；
- 新增 JSON measured-state interface 在线状态更新接口；
- 新增 PIO-GCN Top-K 小样本仿真评估；
- 新增 smoke 消融脚本；
- 新增测试和验证日志。

当前新增内容是可运行的第一轮工程框架，主要目的是验证接口、数据流和物理约束是否能闭环运行；正式性能结论仍应以后续更大训练集和更多场景评估为准。

### 第二轮修正

第二轮已修正以下问题：

- original physics loss 不再使用归一化后的 `loading_ratio`，而是使用数据集中保存的 raw physical features；
- relay priority loss 使用 `loading_ratio > beta`，不再误用 `security_limit = 1.0`；
- measured-state updated root case 已贯穿 Top-K 排序和物理仿真；
- `exhaustive_truth` 语义已改为 `full_truth / smoke_truth`；
- ablation smoke 已区分 paper baseline、physics CE-only、physics + mask、physics-informed、online update 和 PIO Top-K 配置。

这些仍属于 smoke 级验证，不代表正式性能结论。
### Third-Round Small Trusted Experiment

The third round adds a small trusted experiment layer on top of the PIO-GCN smoke framework.

Completed items:

- Added consistency tests between the original `simulate_cascade_path` entry point and the new `simulate_cascade_path_from_case` entry point.
- Added measured-state sanity tests to ensure manually offline line `L03` is not selected as a new active outage.
- Added `online_state_summary.json` to explain how measured-state changes load, generation, offline lines, and loading ratios.
- Added `run_pio_gcn_small_experiment.py` for 10-seed or 20-seed small experiments.
- Added `plot_pio_gcn_small_experiment.py` for result figures.

Current small experiment:

```text
num_seeds = 10
Top-K = 20, 50, 100
max_paths_for_smoke_test = 100
full_truth = false
```

Preliminary aggregate results:

```text
Top-20: mean critical found = 0.6, mean smoke recall = 0.25
Top-50: mean critical found = 1.9, mean smoke recall = 0.8167
Top-100: mean critical found = 2.5, mean smoke recall = 1.0
```

These are early smoke-truth results, not formal full-truth conclusions.

### Fourth-Round Formal-Small Experiment

The fourth round adds a formal-small experiment pipeline:

```text
src/gcn_search/legacy_rts79/run_pio_gcn_formal_small_experiment.py
```

Completed output:

```text
results/gcn_search/pio_formal_small_experiment/
```

The completed run uses full ordered N-2 truth, but only one test seed:

```text
training_num_scenarios = 5
training_epochs = 3
training_max_active_depth = 0
test_num_seeds = 1
full_truth = true
```

Key results:

```text
total_critical_paths = 55
PIO_GCN_Top20 recall = 0.0182
PIO_GCN_Top50 recall = 0.0545
PIO_GCN_Top100 recall = 0.1273
```

This can be reported as a full-truth pipeline validation on RTS-79, but not as a final multi-seed performance conclusion.

### Fifth-Round Progress

The fifth round improves credibility and maintainability:

- Removed already-tracked large intermediate GCN result files from Git tracking.
- Added Step2-State first-line filtering with `candidate_line_filter_mode`.
- Completed a 3-seed full-truth preliminary formal experiment.
- Added diagnostics for found and missed Top-100 critical paths.

Completed preliminary configuration:

```text
training_num_scenarios = 10
training_epochs = 5
training_max_active_depth = 1
candidate_line_filter_mode = high_flow_top_n
max_first_lines = 10
test_num_seeds = 3
full_truth = true
```

Key result:

```text
PIO_GCN_Top100 mean recall = 0.4213
PIO_GCN_Top100 mean_found_after_100 = 23.3333
LODF_yP mean_found_after_100 = 11.6667
original_GCN_path_prob mean_found_after_100 = 8.0
```

Remaining issue: the model is still preliminary and tends to over-predict risky lines. The next step is to improve training data coverage and calibration before making final performance claims.

### Sixth-Round Ablation Conclusion

The sixth round completed a 3-seed full-truth preliminary ablation.

Main result:

```text
physics_ce_no_mask recall@100 = 0.4209
physics_ce_mask recall@100 = 0.4209
physics_loss_no_mask recall@100 = 0.4213
physics_loss_mask recall@100 = 0.4213
paper_gcn_path_prob recall@100 = 0.1435
LODF_yP recall@100 = 0.2099
```

Advisor-reportable conclusion:

```text
The current PIO-GCN PathRank gain mainly comes from physics-enhanced features.
Candidate masking contributes little in the current ranking setup.
The current physics-informed loss is not yet the main source of improvement.
```

This is still preliminary. We should not claim final superiority until the model is trained on broader Step2 states and calibrated more carefully.

### Seventh-Round Rank-Loss Result

| factor | comparison | conclusion |
|---|---|---|
| Physics feature | paper_gcn_path_prob recall@100 0.1435 vs physics_ce_mask 0.4209 | main current gain |
| Candidate mask | physics_ce_no_mask 0.4209 vs physics_ce_mask 0.4209 | little effect in current setup |
| Original physics loss | physics_ce_mask 0.4209 vs physics_loss_mask 0.4213 | tiny Top-100 effect, no Top-20/50 gain |
| Pairwise rank-loss | physics_ce_mask 0.4209 vs physics_rank_loss_mask 0.4337 | small Top-100 change |
| LODF_yP | LODF_yP recall@100 0.2099 vs pairwise rank-loss 0.4337 | Pairwise rank-loss PIO-GCN remains stronger in this 3-seed preliminary run |

Current advisor-reportable message:

```text
Physics features are the main source of improvement.
The new reachable pairwise rank-loss produces a small Top-100 gain.
The model still needs better calibration and broader training before final claims.
```
# Round-8 Unified Current Conclusion

The current review-ready conclusion is:

| Item | Current conclusion |
|---|---|
| Most useful component | Physics-enhanced branch features. |
| PIO-GCN Top-100 preliminary recall | Around 42% on 3 RTS-79 full-truth seeds. |
| LODF_yP baseline | Around 21% Top-100 recall. |
| Weak paper-feature `GCN_path_prob` | Around 14% Top-100 recall. |
| Candidate mask | Currently not a major contributor. |
| Original physics loss | Currently contributes very little. |
| Pairwise rank-loss | No Top-20/Top-50 improvement; only a small Top-100 change, so not yet a robust contribution. |
| Online state | JSON measured-state interface only, not connected to field SCADA/PMU systems. |
| Claim boundary | RTS-79 3-seed preliminary only; not final paper-scale performance. |

In plain Chinese: this stage can report that "adding physics-enhanced features to the GCN input is useful"; it should not report that original physics loss, candidate mask, or pairwise rank-loss has already become the decisive improvement.

# Next-Stage Shortcoming Fixes

| Item | Status |
|---|---|
| Extended full-truth seeds | Completed 5-seed RTS-79 full-truth result. |
| Strong paper baseline | Completed limited 6-scenario paper-feature GCN_path_prob training; 20-scenario attempt was too slow. |
| Synthetic renewable perturbation | Module, example, test, and experiment script added; renewable full-truth experiment not yet run. |
| Loss diagnostics | Added diagnostics explaining why original physics loss and pairwise rank-loss are not decisive yet. |

Key 5-seed result:

| Method | Recall@100 | Recall@200 |
|---|---:|---:|
| PIO-GCN PathRank | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.350 | 0.568 |
| LODF_yP | 0.207 | 0.329 |

This strengthens the earlier conclusion that PIO-GCN PathRank is useful at Top-100, but it also shows that a stronger paper-feature baseline can become competitive and even surpass PIO-GCN at Top-200. This should be reported honestly.

## Latest Shortcoming-Fix Update: Renewable and Top-K Depth

The synthetic renewable perturbation full-truth preliminary experiment is now completed for 3 seeds with renewable penetration ratio 0.30. PIO-GCN PathRank reaches recall@100 about 0.426, the stronger paper-feature baseline reaches about 0.379, and LODF_yP reaches about 0.076. This only supports a synthetic RTS-79 robustness statement; it is not a real renewable power-system result.

The 5-seed RTS-79 full-truth extension also shows a Top-K depth tradeoff:

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.211 | 0.338 | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.176 | 0.254 | 0.350 | 0.568 |
| paper_GCN_path_prob_strong_v2 | 0.176 | 0.244 | 0.330 | 0.565 |
| LODF_yP | 0.036 | 0.134 | 0.207 | 0.329 |

Current honest conclusion: PIO-GCN PathRank is useful for rapid small-Top-K screening, especially Top-20/50/100. It should not be claimed as better at every ranking depth because the stronger paper-feature baseline can overtake at Top-200.

## Latest Performance Improvement: Ensemble and Rerank

Score-level ensemble and hard-negative-aware rerank were evaluated on the same 5-seed RTS-79 full-truth setting.

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| PIO-GCN PathRank | 0.211 | 0.338 | 0.423 | 0.521 |
| paper_GCN_path_prob_strong | 0.176 | 0.254 | 0.350 | 0.568 |
| ensemble_alpha_0.75 | 0.200 | 0.345 | 0.444 | 0.549 |
| rerank_balanced | 0.289 | 0.410 | 0.521 | 0.576 |
| rerank_physical_stress | 0.280 | 0.439 | 0.532 | 0.587 |

Current interpretation: simple ensemble improves some Top-100 behavior but does not fully solve the Top-200 issue. Hard-negative-aware rerank gives the clearest improvement and lifts Top-200 above the stronger paper-feature baseline in this preliminary 5-seed check.

## Latest Learned Path Reranker Result

A compact path-level dataset was built from 5 RTS-79 full-truth seeds. Each ordered N-2 path is one sample, with PIO score, paper score, LODF score, rank features, loading stress, relay margin, and first-outage stress features. Two lightweight PyTorch rerankers were trained with leave-one-seed-out prediction.

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| rerank_physical_stress | 0.280 | 0.439 | 0.532 | 0.587 |
| learned_logistic_reranker | 0.322 | 0.566 | 0.792 | 0.954 |
| learned_mlp_reranker | 0.333 | 0.698 | 0.944 | 0.997 |

The learned MLP reranker exceeds the requested Recall@100 > 0.60 and Recall@200 > 0.65 targets in this 5-seed preliminary check. This is promising, but it is still only RTS-79 preliminary and needs more seeds before final claims.

## Leakage Audit and Strict Held-Out Update

The learned reranker was audited for leakage. No forbidden input feature was found, train/val/test seeds are disjoint, and no near-perfect feature-label correlation was found. Because the original recall was close to oracle, the audit still flags a suspicious-performance warning and requires strict held-out reporting.

| Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---:|---:|---:|---:|
| learned_mlp_reranker_strict | 0.341 | 0.694 | 0.940 | 0.993 |

Feature ablation shows that `score_plus_physical` and `all_safe_features` are strongest. This supports the current result, but more seeds are needed to rule out topology/path-pattern memorization.

## Latest External and Renewable Reranker Validation

The learned path reranker was further checked on three external unseen RTS-79 full-truth seeds and on three synthetic renewable RTS-79 full-truth cases.

| Setting | Method | Recall@20 | Recall@50 | Recall@100 | Recall@200 |
|---|---|---:|---:|---:|---:|
| External seeds 20260727-20260729 | PIO-GCN PathRank | 0.209 | 0.342 | 0.437 | 0.551 |
| External seeds 20260727-20260729 | learned_mlp_reranker_external | 0.354 | 0.718 | 0.922 | 0.994 |
| Synthetic renewable, 0.30 penetration | PIO-GCN PathRank | 0.237 | 0.347 | 0.426 | 0.495 |
| Synthetic renewable, 0.30 penetration | learned_mlp_reranker_renewable | 0.345 | 0.622 | 0.808 | 0.947 |

Memorization analysis currently rates residual path-pattern risk as medium. No direct label leakage has been found, and external/renewable checks are strong, but the model is still evaluated only on RTS-79 topology. The advisor-reportable conclusion is: path-level supervised reranking is very promising for RTS-79, but it is not yet final grid-general evidence.
