# IEEE39 Bus-Fault Injection Feasibility

This audit does not run Simulink, does not modify `.slx`, does not fix L12, does not train GCN, and does not retrain the reranker.

- old formal gate: `35 / 33 / 33`
- v2 candidate count unchanged: `40`
- target-bus selector supported: `False`
- source `.slx` modification required: `False`
- temporary lab copy needed: `True`

## Candidate Bus Classification

| target_bus | classification | runnable_now | uses_temporary_lab_copy | reason |
| --- | --- | ---: | ---: | --- |
| B16 | requires_temporary_lab_copy | False | True | NF07 requested bus; connected to B15/B17/B24 and near previous L12 exclusion edge, so it needs extra care. |
| B39 | requires_temporary_lab_copy | False | True | NF08 requested bus; high-number/reference-area bus and useful independent bus-fault candidate. |
| B21 | requires_temporary_lab_copy | False | True | Alternative candidate connected to B16/B22; useful if B16 is unsafe. |
| B26 | requires_temporary_lab_copy | False | True | Alternative mid/high-number bus connected to B25/B27/B28/B29. |
| B29 | requires_temporary_lab_copy | False | True | Alternative high-number load-area bus connected to B26/B28. |

## Key Boundaries

- B16/B39 are priority smoke candidates, but they are not executable until a safe bus injection point is verified.
- L12 remains excluded because it is a timeout / suspected islanding special case.
- Source `.slx` files are not committed because this round is a smoke feasibility step and source model licensing / physical wiring must stay untouched.
- The model remains phasor_RMS, not EMT.
- `generator_speed_proxy` is not direct frequency.
- relay proxy / handwired breaker is not engineering-grade protection.
- Bus-fault smoke candidates are not formal labels.

## Recommended Action

Do not run bus-fault smoke until a safe target-bus injection point is verified.
