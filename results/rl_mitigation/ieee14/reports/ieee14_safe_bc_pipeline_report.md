# IEEE14 Safe Oracle-BC Pipeline Report

## Required Answers
1. positive-only oracle BC 会失败的原因：训练集只包含主动缓解正样本，缺少 non-improvable 场景应当 do-nothing 的负样本，容易盲目主动断线。
2. full oracle BC 是否降低 non-improvable 误动作：full dataset 包含 115 个 do-nothing 标签，mean_prob_do_nothing_on_non_improvable=0.4148。
3. safe gate 是否进一步降低误动作：val 选择 active_prob_threshold=0.2, margin_threshold=0.05。
4. safe_oracle_bc_full test mean_negative_return=74.2906, pf_failed_ratio=0.7200。
   paired negative_return direction=policy_a_better, mean_diff=-0.8946, CI=[-1.3881, -0.4608]。
5. 改善是否集中在 improvable/high-risk 子集：见 analysis/improvable_subset_summary.csv。
6. 这不属于原论文方法；属于 oracle 辅助初始化和安全门控诊断增强。
7. 毕业论文应表述为增强实验，不应声称原论文 PPO 已稳定学到缓解策略。

## BC Diagnostics
- positive_only samples: 185
- full samples: 300, improvable=185, non_improvable=115

## Multi-Metric Safe Policy Summary
{
  "policy": "safe_oracle_bc_full",
  "split": "test",
  "eval_mode": "deterministic",
  "episodes": "100",
  "mean_negative_return": "74.29057815113192",
  "p95_negative_return": "107.8533384354516",
  "pf_failed_ratio": "0.72",
  "mean_num_generations": "1.2",
  "mean_num_line_outages": "3.92",
  "mean_load_shed_MW": "6.250983098089695",
  "mean_load_shed_ratio": "0.024135069876794188",
  "mean_num_proactive_actions": "0.13",
  "improved_ratio_negative_return": "0.13",
  "worse_ratio_negative_return": "0",
  "improved_ratio_line_outages": "0.13",
  "improved_ratio_load_shed": "0.13"
}