# Dynamic Method Comparison Brief

This is a preliminary diagnostic comparison only, not a formal dynamic stability conclusion.
calibration_warning = False
dynamic_discrimination_signal = False

| method | top_k | dynamic_precision | mean stress | passive trips | security actions |
| --- | ---: | ---: | ---: | ---: | ---: |
| learned_mlp | 50 | 0.3000 | 0.0985 | 0 | 0 |
| learned_mlp | 100 | 0.2700 | 0.0871 | 0 | 0 |
| pio_gcn | 50 | 0.3400 | 0.0997 | 0 | 0 |
| pio_gcn | 100 | 0.3600 | 0.1029 | 0 | 0 |
| lodf | 50 | 0.2800 | 0.0887 | 0 | 0 |
| lodf | 100 | 0.3000 | 0.0900 | 0 | 0 |

No dynamic recall is reported because no full dynamic truth is available.