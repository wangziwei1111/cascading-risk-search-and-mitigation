# IEEE118 RTS-79 Protocol Search

Main method: `RTS79_GCN_path_prob_reused_on_IEEE118_earlystop`, using `p_shed(Li|S0) * p_shed(Lj|S1(i))`.
`RTS79_GCN_second_only_reused_on_IEEE118_earlystop` is retained only as an ablation.
`PFW` is the power-flow-weighted baseline using absolute PF in S0 and S1 states.
Valid ordered N-2 paths: 32560.
Curve points are sparse and include RTS-79-style full-cascade-path deduplicated counts.
The full-cascade path is an approximate reconstruction from relay/final outage labels, not an exact protection_event_table replay.
