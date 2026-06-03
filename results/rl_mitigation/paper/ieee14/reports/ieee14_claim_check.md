# IEEE14 Paper Claim Check

Overall: `partially_supported`

性能结论未完全复现：部分指标改善，但关键指标未全部优于do-nothing。 特别是mean negative return未降低。

在PYPOWER IEEE14替代环境下，仓库完成了论文机制复现和smoke训练验证；当前PPO缓解性能结论为partially_supported，不能写成完整数值复现。

| Metric | do-nothing | proposed | diff | direction | supported |
|---|---:|---:|---:|---|---:|
| mean_negative_return | 79.0650 | 88.1911 | 9.1261 | worse | False |
| p95_negative_return | 110.0899 | 106.2332 | -3.8567 | improved | True |
| mean_num_generations | 1.3000 | 1.0500 | -0.2500 | improved | True |
| mean_num_line_outages | 5.5000 | 5.8000 | 0.3000 | worse | False |
| mean_load_shed_MW | 18.0471 | 15.3071 | -2.7399 | improved | True |
| mean_load_shed_ratio | 0.0697 | 0.0591 | -0.0106 | improved | True |
| pf_failed_ratio | 0.7500 | 0.8500 | 0.1000 | worse | False |
| mean_num_invalid_actions | 0.0000 | 0.0000 | 0.0000 | unchanged | True |
| mean_num_proactive_actions | 0.0000 | 1.0500 | 1.0500 | improved | True |
