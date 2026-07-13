# IEEE118 Residual-Reachable Scale-Up Comparison

This compact comparison holds the original RTS-79 `PaperStyleRts79Gcn`, `k_gcn=6`, loss, truth, and N-1-gated evaluation protocol fixed. Only multi-seed training-state volume changes from 2,000 to 8,000. `path_prob` is the primary ranking; `second_only` remains a diagnostic ablation. The main search count uses N-2 candidate verifications, matching the RTS-79 convention; 186 N-1 state-construction simulations are reported separately.

| Dataset | Test AP | N-2 candidate K90 | K95 | K99 |
|---|---:|---:|---:|---:|
| pilot-2000 | 0.4463 | 2,003 | 3,176 | 10,929 |
| paper-8000 | 0.6167 | 1,793 | 2,263 | 4,305 |
