# IEEE118 mechanism-aware GCN compact audit

Only compact ablation and paired prospective summaries are versioned here.
The 4,604-row physical replay, dense mechanism targets, checkpoints, training
logs, and complete prospective query logs remain local.

The unchanged `PaperStyleRts79Gcn` backbone was tested with continuous relay,
island-shed, and total-shed auxiliary targets. Plain weighted multi-task
training exhibited negative transfer. Primary-protected PCGrad reduced formal
K95 but did not consistently improve relay or load-shed discovery across ten
new seeds. A validation-frozen GCN-UCB fallback was also mixed across five new
seeds. None replaces the tail hard-pairwise checkpoint from PR #24.
