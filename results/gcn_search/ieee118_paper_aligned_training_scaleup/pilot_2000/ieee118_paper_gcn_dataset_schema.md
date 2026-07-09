# IEEE118 Paper-Aligned GCN Dataset Schema

- `x_gcn`: state x branch x 4 paper-style features (`x_t`, `x_p`, `x_b`, `x_l`).
- `y_gcn`: branch vulnerability labels for the current state.
- `loss_mask`: valid candidate branches for each current state.
- `sample_type`: `S0` base states and `S1` first-outage states.
- Splits are assigned by load-scenario seed to avoid leakage.
