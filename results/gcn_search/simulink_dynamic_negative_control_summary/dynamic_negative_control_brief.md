# Dynamic Negative Control Brief

global_degeneracy_warning = True
dynamic_discrimination_signal = True

| group | precision@20 | passive trips | security actions | mean stress |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 1.0000 | 20 | 20 | 26.1084 |
| low_score_top20 | 1.0000 | 15 | 15 | 11.7528 |
| random_top20 | 1.0000 | 18 | 18 | 16.1437 |
| line_order_top20 | 1.0000 | 12 | 12 | 9.1307 |

No dynamic recall is reported because no full dynamic truth is available.