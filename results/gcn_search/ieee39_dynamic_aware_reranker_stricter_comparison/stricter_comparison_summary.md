# IEEE39 Dynamic-Aware Stricter Comparison

This is a preview-only stricter comparison, not a final dynamic performance conclusion.

The expanded 35-sample preview is more complete than the historical 10-sample preview. However, the leaky dynamic measurement feature set can still be optimistic because the target is derived from compact dynamic measurements.

The no_dynamic_measurement_features and topology_only_features settings are closer to a realistic prediction scenario. If their metrics are worse than the leaky setting, that is an expected and important finding rather than a failure.

- num_samples: 35
- L12 excluded because it is timeout / suspected islanding.
- leakage gap summary: {'best_leaky_rmse': 0.03045480664099702, 'best_no_leakage_rmse': 0.10785453926718819, 'rmse_gap_no_leak_minus_leaky': 0.07739973262619117, 'interpretation': 'A positive gap indicates that removing dynamic measurement features makes the task harder, which is expected and important.'}
- phasor_RMS, not EMT.
- generator_speed_proxy is not direct frequency.
- handwired breaker is pilot breaker-like validation, not engineering-grade protection.
- Future work needs more fault types, independent test sets, more operating conditions, and stricter leakage checks.
