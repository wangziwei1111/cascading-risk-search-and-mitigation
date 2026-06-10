# Dynamic Method Comparison Brief

This is a preliminary diagnostic comparison only, not a formal dynamic stability conclusion.
calibration_warning = True
dynamic_discrimination_signal = False

| method | top_k | dynamic_precision | mean stress | passive trips | security actions |
| --- | ---: | ---: | ---: | ---: | ---: |
| learned_mlp | 50 | 0.0000 | 0.1034 | 0 | 0 |
| learned_mlp | 100 | 0.0000 | 0.1040 | 0 | 0 |
| pio_gcn | 50 | 0.0000 | 0.1034 | 0 | 0 |
| pio_gcn | 100 | 0.0000 | 0.1040 | 0 | 0 |
| lodf | 50 | 0.0000 | 0.0856 | 0 | 0 |
| lodf | 100 | 0.0000 | 0.0949 | 0 | 0 |

No dynamic recall is reported because no full dynamic truth is available.