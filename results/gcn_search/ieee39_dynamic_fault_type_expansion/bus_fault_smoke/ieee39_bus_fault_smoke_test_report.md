# IEEE39 Bus-Fault Smoke-Test Report

This report is preview-only. It is not a final dynamic performance conclusion.

- requested: BF01, BF02, BF03, BF04
- runnable: none
- successful: none
- failed/skipped: BF01, BF02, BF03, BF04
- timeout: none
- source `.slx` modified: false
- formal label gate changed: false
- reranker retrained: false
- GCN trained: false
- L12 touched: false

The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct frequency. relay proxy / handwired breaker is not engineering-grade protection.

Recommended next step:

Verify a safe bus-fault injection point on a temporary lab copy before running bus-specific smoke tests.
