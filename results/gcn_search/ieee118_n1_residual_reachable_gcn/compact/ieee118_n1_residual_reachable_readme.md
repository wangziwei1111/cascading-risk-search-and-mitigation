# IEEE118 N-1-Gated Residual-Reachable GCN Pilot

This compact artifact uses the original RTS-79 `PaperStyleRts79Gcn`; the model core is unchanged. The selected graph radius is based on validation AP, not the held-out test thresholds.

- Selected `k_gcn`: 6 (effective maximum about 12 hops)
- Critical paths: 1754 of 32560
- N-1 prescreen: 186 physical evaluations
- Primary path-probability total physical K90/K95/K99: 2189 / 3362 / 11115
- Second-only ablation total physical K90/K95/K99: 2125 / 3219 / 10386

These are pilot-2000 results, not final full-scale training results and not a claim that all critical paths are found near K90. Large NPZs, checkpoints, and full predictions remain local.
