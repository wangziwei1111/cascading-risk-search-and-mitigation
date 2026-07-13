# IEEE118 Residual Reachable Dataset Schema

- `x_gcn`: unchanged paper-style state features.
- `y_gcn` / `y_residual_reachable`: S0 residual-reachable labels and S1 residual critical labels.
- `loss_mask`: excludes invalid candidates and N-1-critical second lines.
- `n1_critical_mask`: per-sample copy of the same-seed S0 N-1 critical line mask.
- `known_s0_labels`: distinguishes observed S0 reachable labels from unknown candidates.
- `active_first_line`: explicit active outage when known; never inferred from ambiguous passive outages.
