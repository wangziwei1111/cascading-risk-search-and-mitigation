# IEEE39 Non-Line-Trip Fault Smoke-Test Report

- requested: NF01, NF02, NF03, NF04, NF06
- completed: NF01, NF02, NF03, NF04, NF06
- successful smoke candidates: NF01, NF02, NF03, NF04, NF06
- failed: none
- timeout: none
- formal label gate changed: False
- reranker retrained: False
- `.slx` modified: False
- L12 touched: False

Smoke-test success is not a formal dynamic-label merge. The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct frequency. The relay proxy is not engineering-grade protection.

Recommended next step:

Create a separate merge/export round for non-line-trip candidate labels, keeping them separate from handwired line-trip labels.
