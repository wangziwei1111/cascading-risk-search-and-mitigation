# IEEE118 Reuse of Original RTS-79 GCN Plan

This stage corrects the IEEE118 evaluation path: the earlier `GCN_smoke` is a lightweight NumPy/logistic smoke scorer, not the original RTS-79 GCN. It must not be reported as the main GCN result.

## Original RTS-79 GCN Contract

Original RTS-79 GCN file path:

- `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`

Original RTS-79 training script:

- `src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py`
- Step2-State reuse variant: `src/gcn_search/legacy_rts79/train_rts79_step2_state_gcn.py`
- PIO/physics-informed variant: `src/gcn_search/legacy_rts79/train_rts79_physics_gcn.py`

Original RTS-79 evaluation script:

- Paper-style search: `src/gcn_search/legacy_rts79/evaluate_rts79_paper_gcn_search.py`
- PIO-GCN Top-K path ranking: `src/gcn_search/legacy_rts79/evaluate_rts79_pio_gcn_topk.py`

Original model class name:

- `PaperGraphConvolution`
- `PaperStyleRts79Gcn`

Original input data format:

- Tensor shape: `num_states x num_branches x num_features`
- Label shape: `num_states x num_branches`
- Loss mask shape: `num_states x num_branches`
- Branch graph adjacency powers: `(K + 1) x num_branches x num_branches`

Original paper-style node/branch features:

- `branch_status_offline`
- `relay_loading_ratio = abs(PF) / (beta * RATE_A)`
- `abs_flow`
- `max_terminal_load`

PIO-GCN physics feature fields:

- `branch_status_offline`
- `relay_loading_ratio`
- `abs_flow`
- `max_terminal_load`
- `loading_ratio`
- `security_margin`
- `relay_margin`
- `is_online`
- `is_candidate`

Original loss:

- Weighted `torch.nn.CrossEntropyLoss(reduction="none")`
- Masked by the candidate/loss mask before averaging
- PIO-GCN optionally adds mask-invalid, relay-priority, loading-monotonic, and reachable pairwise ranking losses from `gcn_physics_constraints.py`

Original train/validation split:

- Scenario split when multiple scenarios exist in `train_rts79_paper_gcn.py`
- Random state split for Step2-State in `train_rts79_step2_state_gcn.py`

Original hyperparameters:

- `epochs=20`
- `batch_size=32`
- `learning_rate=0.005`
- `k_gcn=3`
- `first_layer_channels=16`
- `second_layer_channels=4`
- `positive_weight=20.0`
- `validation_fraction=0.2`
- `random_seed=20260512`

Original ranking score:

- Paper search uses `GCN_path_prob = first_probability * second_probability`
- PIO-GCN Top-K uses the same path-probability idea after applying candidate masks

Original baseline comparison methods:

- `random`
- `line_order`
- `LODF_yP`
- GCN probability/order variants
- PIO-GCN Top-K

## IEEE118 Adaptation

IEEE118 needs adapted data fields:

- `path`
- `first_line`
- `second_line`
- `label_critical`
- `label_relay_cascade`
- graph state features from `edge_features_json` and `node_features_json`
- branch endpoints for the IEEE118 branch adjacency matrix

The adapter script is:

- `src/gcn_search/ieee118/convert_ieee118_step2_to_rts79_gcn_format.py`

It converts IEEE118 Step2-State samples into the same tensor contract used by the RTS-79 GCN:

- `ieee118_rts79_gcn_dataset.npz`
- `ieee118_rts79_gcn_path_index.csv`
- `ieee118_rts79_gcn_feature_normalizer.json`
- `ieee118_rts79_gcn_dataset_metadata.json`

Wrapper script:

- `src/gcn_search/ieee118/train_ieee118_with_original_rts79_gcn.py`

The wrapper may load IEEE118 converted data, build the IEEE118 branch adjacency matrix, and call the original `PaperStyleRts79Gcn`. It must not define a replacement GCN model.

Cannot改动的模型部分:

- `PaperGraphConvolution`
- `PaperStyleRts79Gcn`
- two graph-convolution layers plus linear classifier architecture
- masked weighted cross-entropy training objective for the main supervised loss

Excluded leakage fields:

- `critical`
- `critical_mechanism`
- `has_overload_cascade`
- `relay_cascade`
- `total_load_shed_mw`
- `num_relay_trips`
- `max_event_loading_ratio`
- `max_pre_redispatch_loading_ratio`
- `label_critical`
- `label_relay_cascade`
- `label_load_shed_positive`

## Smoke Scorer Status

`GCN_smoke` is not the original RTS-79 GCN. It is only a smoke scorer and must not be reported as the main GCN result.

Formal IEEE118 GCN result names should be:

- `RTS79_GCN_reused_on_IEEE118`
- `RTS79_PIO_GCN_reused_on_IEEE118`

## Current Environment Note

The local default Python currently fails to import `torch` with a DLL path error. The wrapper therefore has an explicit blocked mode that writes `original_rts79_gcn_ieee118_metrics.json` with `status=blocked_torch_import`; it does not fall back to the NumPy/logistic smoke scorer. A working PyTorch environment is required to train the reused original RTS-79 GCN.
