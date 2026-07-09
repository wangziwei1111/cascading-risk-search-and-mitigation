# IEEE118 Alpha Path-Probability Sweep

This compact run reuses existing PR #14/#15 pilot-2000 model scores. It does not retrain the GCN, rerun OPA, or modify Algorithm 1.

- Paths evaluated: 32560
- Critical paths: 1754
- Relay-cascade paths: 1643
- Score table used: `C:\Users\24186\Documents\New project 7\cascading-risk-search-and-mitigation\results\gcn_search\ieee118_paper_aligned_training_scaleup\s0_bottleneck_diagnostics\s0_bottleneck_full_score_table_local_only.csv`

Scoring rule:

`score_alpha(Li -> Lj) = (epsilon + p_first(Li | S0))^alpha * p_second(Lj | S1(i))`

- `alpha=1, epsilon=0` is the strict paper-aligned path probability.
- `alpha=0` is exactly the second-step-only ablation, independent of epsilon.
- Intermediate `alpha` values soften the first-step probability from a hard multiplicative gate into a ranking prior.
- best_by_critical_hits_at_1000: `alpha_path_prob_a0_eps0` at K=1000, critical hits=661, precision=0.661.
- best_by_precision_at_1000: `alpha_path_prob_a0_eps0` at K=1000, critical hits=661, precision=0.661.
- best_by_recall_at_5000: `alpha_path_prob_a025_eps1em2` at K=5000, critical hits=1710, precision=0.342.
- best_by_relay_hits_at_1000: `alpha_path_prob_a0_eps0` at K=1000, critical hits=661, precision=0.661.
- best_by_captured_load_shed_at_1000: `alpha_path_prob_a0_eps0` at K=1000, critical hits=661, precision=0.661.
