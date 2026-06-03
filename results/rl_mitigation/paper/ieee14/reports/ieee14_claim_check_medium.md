# IEEE14 Paper Claim Check

Mode: `medium`
Overall: `not_supported`
source_eval_csv: `results/rl_mitigation/paper/ieee14/eval/eval_100_before_after_medium.csv`
source_checkpoint: `results/rl_mitigation/paper/ieee14/checkpoints/proposed_pretrain_mask_medium/latest.pt`
source_train_log: `results/rl_mitigation/paper/ieee14/train_logs/proposed_pretrain_mask_medium.csv`

性能结论未复现：关键缓解指标未优于do-nothing。 性能结论未完全复现，特别是mean negative return未降低。

在PYPOWER IEEE14替代环境下，当前medium运行完成了论文机制复现；PPO缓解性能结论为not_supported，不能写成完整数值复现。

| Metric | do-nothing | proposed | diff | direction | supported |
|---|---:|---:|---:|---|---:|
| mean_negative_return | 80.159715 | 80.159715 | 0.000000 | unchanged | True |
| p95_negative_return | 108.873307 | 108.873307 | 0.000000 | unchanged | True |
| mean_num_generations | 1.170000 | 1.170000 | 0.000000 | unchanged | True |
| mean_num_line_outages | 4.770000 | 4.770000 | 0.000000 | unchanged | True |
| mean_load_shed_MW | 11.604456 | 11.604456 | 0.000000 | unchanged | True |
| mean_load_shed_ratio | 0.044805 | 0.044805 | 0.000000 | unchanged | True |
| pf_failed_ratio | 0.770000 | 0.770000 | 0.000000 | unchanged | True |
| mean_num_invalid_actions | 0.000000 | 0.000000 | 0.000000 | unchanged | True |
| mean_num_proactive_actions | 0.000000 | 0.000000 | 0.000000 | improved | True |
