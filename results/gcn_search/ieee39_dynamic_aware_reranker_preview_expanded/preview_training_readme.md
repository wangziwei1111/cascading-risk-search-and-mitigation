# IEEE39 Dynamic-Aware Reranker Preview Training

This is a preview-only sanity check, not a final dynamic performance conclusion.

- Model family: lightweight ridge regression with leave-one-out preview validation.
- Dataset: `results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_dataset.csv`
- Predictions: `results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_predictions.csv`
- Metrics: `results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_metrics.json`
- num_samples: 35
- num_training_ready_labels: 35
- num_handwired_line_trip_labels: 33
- L12 excluded: true, because it remains simulation_timeout / suspected islanding
- allowed_for_dynamic_aware_training: true
- ready_for_preview_training: true

Boundaries:

- The IEEE39 model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker workflow is pilot breaker-like validation, not engineering-grade protection.
- The current sample count is small, so metrics are workflow/sanity-check evidence only.
- `dynamic_stress_score` is a synthetic proxy target derived from compact dynamic measurements.
- Some features also come from compact dynamic measurements, so metrics may be optimistic.
- No `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries are committed.
