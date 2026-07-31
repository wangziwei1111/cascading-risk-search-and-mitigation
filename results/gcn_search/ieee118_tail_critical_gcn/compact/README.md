# IEEE118 tail-critical GCN compact evidence

This directory contains only cross-run summaries. Local checkpoints, complete
prediction arrays, prospective query logs, and full-truth tables are excluded
from git.

The unchanged `PaperStyleRts79Gcn` backbone was fine-tuned with a validation-
selected hard-positive/hard-negative pairwise objective. A label-free active
selector supplied 6,197 additional physical labels (0.5% of available training
candidates); labels were revealed only after selection.

At equal 2,100-query prospective budgets, the tail model found one additional
critical path on each of seeds 20260709 and 20260710. The gain is repeatable but
small. The adaptive policy's roughly 86% recall on seed 20260709 must not be
attributed entirely to GCN: probe and promoted-family expansion supply nearly
all hits.

The fixed RRF application ablation combined tail-GCN, iterative LODF severity,
and ensemble uncertainty. It retained the same critical count as tail-GCN but
lost two relay-cascade hits, so it is not the primary method.
