# IEEE118 Paper-Aligned Positive-Weight Sweep

This sweep retrains the original RTS-79 `PaperStyleRts79Gcn` with different positive class weights. `positive_weight=20` is the original RTS-79 default and remains the main paper-aligned baseline. Higher weights are IEEE118 sensitivity checks and should be reported separately.

- Dataset: `results\gcn_search\ieee118_paper_aligned_training_scaleup\pilot_2000\ieee118_paper_gcn_dataset.npz`
- Epochs: 20
- Batch size: 32
- Best sensitivity by average precision: positive_weight=20.0
- Model checkpoints are local-only and should not be committed.
