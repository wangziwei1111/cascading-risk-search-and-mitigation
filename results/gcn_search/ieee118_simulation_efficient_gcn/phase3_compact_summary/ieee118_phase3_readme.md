# IEEE118 simulation-efficient GCN Phase 3

The main method retains `PaperStyleRts79Gcn`, pretrains it on a cheap DC/LODF target, fine-tunes with 5% retrospective high-fidelity labels, and applies validation-selected feedback probing before unchanged-GCN fallback. Candidate N-2 counts and S1 construction counts are reported separately. The 5% figure is a training-query fraction; complete validation/model-selection labels are included in the separate total development-data cost.

- Queried training labels: 61,973
- Unique development labels: 203,092
- Total development-label reduction: 85.29%
- Critical K90 / K95 / K99: 1897.0 / 3608.8 / 19039.6
- K90 S1 constructions / total physical operations: 176 / 2073.0

This is a retrospective IEEE118 experiment, not a real-grid deployment or a completed N-k scalability claim.
