# IEEE118 Residual-Reachable Scale-Up Comparison

This compact comparison holds the original RTS-79 `PaperStyleRts79Gcn`, `k_gcn=6`, loss, truth, and N-1-gated evaluation protocol fixed. Only multi-seed training-state volume changes from 2,000 to 8,000. `path_prob` is the primary ranking; `second_only` remains a diagnostic ablation.

| Dataset | Test AP | Total physical K90 | K95 | K99 |
|---|---:|---:|---:|---:|
| pilot-2000 | 0.4463 | 2,189 | 3,362 | 11,115 |
| paper-8000 | 0.6167 | 1,979 | 2,449 | 4,491 |
