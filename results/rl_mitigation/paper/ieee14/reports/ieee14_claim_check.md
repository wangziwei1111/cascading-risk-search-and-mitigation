# IEEE14 Paper Claim Check

Overall: `partially_supported`

当前PYPOWER IEEE14替代环境下，论文关于PPO缓解效果的数值结论尚未完全复现；已复现MDP和训练机制，但性能结论需要进一步调参或更接近原论文grid2op环境。

| Check | Supported |
|---|---:|
| mean_negative_return_lower | False |
| p95_negative_return_lower | True |
| num_generations_lower | True |
| num_line_outages_lower | False |
| load_shed_lower | False |
| invalid_action_count_low | True |
| proactive_actions_conservative | True |
| pf_failed_not_higher | False |
