# IEEE14 Paper Pipeline Report

Config: `configs/rl_mitigation/paper/ieee14_paper_ppo.yaml`
Smoke: `True`
Training steps: `2048`
Eval episodes: `100`

## Artifacts

- PPO train log: `C:\Users\24186\Documents\New project 7\cascading-risk-search-and-mitigation\results\rl_mitigation\paper\ieee14\train_logs\proposed_pretrain_mask_smoke.csv`
- Checkpoint: `C:\Users\24186\Documents\New project 7\cascading-risk-search-and-mitigation\results\rl_mitigation\paper\ieee14\checkpoints\proposed_pretrain_mask\latest.pt`
- Eval CSV: `C:\Users\24186\Documents\New project 7\cascading-risk-search-and-mitigation\results\rl_mitigation\paper\ieee14\eval\eval_100_before_after_smoke.csv`
- Figure 8: `C:\Users\24186\Documents\New project 7\cascading-risk-search-and-mitigation\results\rl_mitigation\paper\ieee14\figures\fig8_ieee14_negative_return_survival_smoke.png`
- Claim check: `C:\Users\24186\Documents\New project 7\cascading-risk-search-and-mitigation\results\rl_mitigation\paper\ieee14\reports\ieee14_claim_check.json`

## Do-Nothing Pretrain Diagnostics

- mean_prob_do_nothing: `0.07344046980142593`
- median_prob_do_nothing: `0.0752444937825203`
- mean_entropy: `3.028817653656006`
- mean_max_nonzero_prob: `0.05925650894641876`

## Claim Metrics

| Metric | do-nothing | proposed | diff | direction | supported |
|---|---:|---:|---:|---|---:|
| mean_negative_return | 80.1597 | 80.1271 | -0.0326 | improved | True |
| p95_negative_return | 108.8733 | 108.8733 | 0.0000 | unchanged | True |
| mean_num_generations | 1.1700 | 1.1700 | 0.0000 | unchanged | True |
| mean_num_line_outages | 4.7700 | 4.7900 | 0.0200 | worse | False |
| mean_load_shed_MW | 11.6045 | 11.6879 | 0.0835 | worse | False |
| mean_load_shed_ratio | 0.0448 | 0.0451 | 0.0003 | worse | False |
| pf_failed_ratio | 0.7700 | 0.7700 | 0.0000 | unchanged | True |
| mean_num_invalid_actions | 0.0000 | 0.0000 | 0.0000 | unchanged | True |
| mean_num_proactive_actions | 0.0000 | 0.0600 | 0.0600 | improved | True |

Overall: `partially_supported`

当前PYPOWER IEEE14替代环境下，plain paper PPO尚未稳定优于do-nothing。仓库已复现MDP、动作空间、奖励函数、do-nothing初始化、invalid action mask和PPO训练流程；性能结论仍需更长训练、更接近原论文grid2op环境或进一步调参验证。
