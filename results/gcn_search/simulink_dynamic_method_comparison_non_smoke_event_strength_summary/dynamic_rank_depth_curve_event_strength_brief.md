# Dynamic Rank-Depth Curve Brief

This curve checks whether dynamic stress appears earlier in the ranking. It is preliminary diagnostic evidence only.

| method | k | precision | mean stress |
| --- | ---: | ---: | ---: |
| learned_mlp | 10 | 0.5000 | 0.1376 |
| learned_mlp | 20 | 0.4000 | 0.1183 |
| learned_mlp | 50 | 0.3000 | 0.0985 |
| learned_mlp | 100 | 0.2700 | 0.0871 |
| pio_gcn | 10 | 0.2000 | 0.0717 |
| pio_gcn | 20 | 0.3000 | 0.0917 |
| pio_gcn | 50 | 0.3400 | 0.0997 |
| pio_gcn | 100 | 0.3600 | 0.1029 |
| lodf | 10 | 0.1000 | 0.0444 |
| lodf | 20 | 0.1000 | 0.0484 |
| lodf | 50 | 0.2800 | 0.0887 |
| lodf | 100 | 0.3000 | 0.0900 |

No dynamic recall is reported because no full dynamic truth is available.