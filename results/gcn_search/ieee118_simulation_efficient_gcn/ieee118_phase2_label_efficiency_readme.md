# IEEE118 Phase-2 Label-Efficiency Result

The unchanged RTS-79 `PaperStyleRts79Gcn` was trained with hidden-label replay at five acquisition seeds. The primary hybrid uses random anchors, risk/uncertainty/physics cohorts, and queried-label prior correction.

- Full-label training oracle labels: 1,239,452
- Primary queried labels: 61,973 (5.00%)
- Mean test AP: 0.5579 +/- 0.0150 (full-label 0.6167)
- Mean gated path K90: 1891.2 +/- 26.7 (full-label 1793)
- Mean gated path K95/K99: 3569.4/21806.2

The validation-selected dual-anchor mean fusion uses about 9.52% of the union label budget and improves the active-only K99/residual K90 diagnostics, but it remains a freeze-then-confirm recommendation.

Gate 1 is not passed. Residual-only high-recall ranking remains much worse than the full-label model, and this is retrospective replay rather than an on-demand physical-oracle run.
