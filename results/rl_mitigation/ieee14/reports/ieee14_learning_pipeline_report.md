# IEEE14 Learning Pipeline Report

## Required Answers
1. 环境中是否存在可缓解空间：是。test better_action_ratio=0.6000。
2. one-step oracle 改善幅度：test mean_best_improvement=8.1251。
3. random init PPO 是否学到：见 training_ablation_summary.csv 中 ppo_random_init。
4. do-nothing init PPO 是否学到：见 training_ablation_summary.csv 中 ppo_do_nothing_init。
5. oracle BC init PPO 是否学到：见 training_ablation_summary.csv 中 ppo_oracle_bc_init。
6. 改善主要出现在哪些场景子集：见 improvable_subset_summary.csv 和 improvable_subset_report.md。
7. 是否可以写 RL 策略具有缓解效果：只能在 paired stats 和 test split 支持时谨慎表述；oracle BC 属于增强实验。
8. 原论文机制复现：MDP、action mask、PPO、N-1/N-2、PYPOWER IEEE14；诊断增强：action scan、one-step oracle、oracle BC、subset analysis、training ablation。

## Deterministic Test Summary
- ppo_random_init: mean_negative_return=78.3683, improvement_vs_do_nothing=-3.1831, argmax_do_nothing_ratio=0.0000
- ppo_do_nothing_init: mean_negative_return=75.1901, improvement_vs_do_nothing=-0.0050, argmax_do_nothing_ratio=0.9500
- ppo_oracle_bc_init: mean_negative_return=100.1000, improvement_vs_do_nothing=-24.9149, argmax_do_nothing_ratio=0.0000

## Paired Stats Snapshot
- ppo_do_nothing_init vs do_nothing / negative_return: mean_diff=0.0050, CI=[0.0010, 0.0090], improved_ratio=0.000
- ppo_do_nothing_init vs do_nothing / num_generations: mean_diff=0.0000, CI=[0.0000, 0.0000], improved_ratio=0.000
- ppo_do_nothing_init vs do_nothing / num_line_outages: mean_diff=0.0500, CI=[0.0100, 0.0902], improved_ratio=0.000
- ppo_do_nothing_init vs do_nothing / load_shed_MW: mean_diff=0.0000, CI=[0.0000, 0.0000], improved_ratio=0.000
- ppo_oracle_bc_init vs do_nothing / negative_return: mean_diff=24.9149, CI=[15.9570, 34.3759], improved_ratio=0.590
- ppo_oracle_bc_init vs do_nothing / num_generations: mean_diff=-0.2000, CI=[-0.2800, -0.1300], improved_ratio=0.200
- ppo_oracle_bc_init vs do_nothing / num_line_outages: mean_diff=-2.0100, CI=[-2.6202, -1.4000], improved_ratio=0.570
- ppo_oracle_bc_init vs do_nothing / load_shed_MW: mean_diff=-15.4260, CI=[-20.9621, -10.2890], improved_ratio=0.420

## Subset Snapshot
- all_test / do_nothing: mean_negative_return=75.1851, mean_improvement_vs_do_nothing=0.0000
- all_test / one_step_oracle: mean_negative_return=67.0600, mean_improvement_vs_do_nothing=8.1251
- all_test / ppo_do_nothing_init: mean_negative_return=75.1901, mean_improvement_vs_do_nothing=-0.0050
- all_test / ppo_oracle_bc_init: mean_negative_return=100.1000, mean_improvement_vs_do_nothing=-24.9149
- all_test / ppo_random_init: mean_negative_return=78.3683, mean_improvement_vs_do_nothing=-3.1831
- improvable / do_nothing: mean_negative_return=103.6419, mean_improvement_vs_do_nothing=0.0000
- improvable / one_step_oracle: mean_negative_return=90.1000, mean_improvement_vs_do_nothing=13.5419
- improvable / ppo_do_nothing_init: mean_negative_return=103.6436, mean_improvement_vs_do_nothing=-0.0017
- improvable / ppo_oracle_bc_init: mean_negative_return=100.1000, mean_improvement_vs_do_nothing=3.5419
- improvable / ppo_random_init: mean_negative_return=100.4756, mean_improvement_vs_do_nothing=3.1663
- non_improvable / do_nothing: mean_negative_return=32.5000, mean_improvement_vs_do_nothing=0.0000
- non_improvable / one_step_oracle: mean_negative_return=32.5000, mean_improvement_vs_do_nothing=0.0000