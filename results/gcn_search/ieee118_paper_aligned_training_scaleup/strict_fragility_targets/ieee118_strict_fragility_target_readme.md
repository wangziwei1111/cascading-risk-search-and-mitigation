# IEEE118 Strict First-Line Fragility Targets

This target builder replaces PR #17's degenerate any-critical label with top-quantile targets. It reuses existing paper-aligned/full-truth artifacts and does not rerun OPA. The generated NPZ is local-only.

First-step critical lines are excluded from training loss and retained as direct-shed diagnostics. The sampled pilot S1 data only stores second-step critical labels, so relay/load-shed strict targets are complete for the held-out full-truth seed and diagnostic for sampled train/validation seeds.
