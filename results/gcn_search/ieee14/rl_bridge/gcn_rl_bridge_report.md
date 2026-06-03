# IEEE14 GCN-to-RL Bridge

This report uses the same PYPOWER IEEE14 scenario IDs for both risk identification and mitigation evaluation.
No RTS79, IEEE39, or legacy GCN branch mapping is used.

## GCN-selected test scenarios

Top-K size: 20

| rank | scenario_id | GCN score | do-nothing risk | best action improvement | initial outages |
|---:|---:|---:|---:|---:|---|
| 1 | 42 | 0.1219 | 107.8668 | 7.7668 | 8 |
| 2 | 85 | 0.1155 | 109.8472 | 9.7472 | 6,9 |
| 3 | 45 | 0.1149 | 106.9203 | 106.8203 | 8 |
| 4 | 86 | 0.1149 | 102.9554 | 2.8554 | 3,5 |
| 5 | 69 | 0.1148 | 113.8617 | 13.7618 | 3 |
| 6 | 73 | 0.1142 | 104.8771 | 4.7771 | 8,16 |
| 7 | 59 | 0.1123 | 108.7691 | 8.6691 | 7 |
| 8 | 15 | 0.1118 | 103.9211 | 3.8211 | 3,7 |
| 9 | 37 | 0.1113 | 101.9801 | 1.8801 | 8 |
| 10 | 38 | 0.1108 | 109.8562 | 9.7562 | 9,11 |
| 11 | 26 | 0.1103 | 101.9801 | 1.8801 | 8,15 |
| 12 | 64 | 0.1096 | 110.7403 | 10.6403 | 3,7 |
| 13 | 10 | 0.1087 | 101.9887 | 1.8887 | 5,8 |
| 14 | 25 | 0.1063 | 105.0967 | 4.9967 | 8,14 |
| 15 | 96 | 0.1061 | -0.0000 | 0.0000 | 4 |
| 16 | 46 | 0.1055 | 104.9505 | 104.8505 | 4 |
| 17 | 35 | 0.1055 | 108.0501 | 107.9501 | 5,8 |
| 18 | 91 | 0.1044 | 107.8370 | 7.7370 | 9,11 |
| 19 | 4 | 0.1035 | 100.0000 | 0.0000 | 7,13 |
| 20 | 62 | 0.1033 | 101.9801 | 1.8801 | 3,4 |

## RL evaluation on all test vs GCN top-K

| policy | subset | n | mean negative return | mean line outages | mean load shed MW | PF failed rate |
|---|---|---:|---:|---:|---:|---:|
| do_nothing | all_test | 100 | 75.1851 | 4.7000 | 15.7833 | 0.7200 |
| do_nothing | gcn_top_20 | 20 | 100.6739 | 7.0500 | 27.2446 | 0.9500 |
| safe_oracle_bc_full | all_test | 100 | 74.2906 | 3.9200 | 6.2510 | 0.7200 |
| safe_oracle_bc_full | gcn_top_20 | 20 | 98.8216 | 5.3500 | 9.0992 | 0.9500 |
| one_step_oracle | all_test | 100 | 67.0600 | 2.2900 | 0.3573 | 0.6700 |
| one_step_oracle | gcn_top_20 | 20 | 80.0900 | 2.5500 | 0.0000 | 0.8000 |

Interpretation: the GCN module defines a same-system IEEE14 high-risk subset; the RL policies are evaluated on that subset without changing the action interface.
