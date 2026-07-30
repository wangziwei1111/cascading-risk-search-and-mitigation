# IEEE118 lazy ordered-prefix search

This compact audit separates second-outage verification calls from on-demand first-outage S1 construction. Unopened first-line prefixes use `p_shed_first` as an admissible upper bound; an S1 state is activated only when that bound reaches the best-first queue head.

When adaptive probing is enabled, a validation-frozen low-fidelity gate receives a small number of real N-2 probes. Only second lines confirmed by those queried outcomes are expanded before the original GCN fallback order. Unqueried full-truth labels are never read by the policy.

The experiment is retrospective because the local evaluation dataset already contains every S1 feature row. The reported activation trace is suitable for policy comparison, but prospective simulator timing is still required before claiming operational speedup.
