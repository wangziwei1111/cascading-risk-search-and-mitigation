# IEEE39 Single Pair Smoke Execution Contract

- `contract_scope`: single_pair_smoke_execution_contract
- `allowed_pair_count`: 1
- `selected_32_batch_execution_allowed`: False
- `full_1056_generation_allowed`: False
- `requires_manual_approval`: True
- `requires_explicit_execute`: True
- `timeout_policy`: timeout remains timeout/null and must not become 0/1
- `unknown_policy`: unknown remains null
- `failed_policy`: failed remains null
- `blocked_policy`: blocked remains null
- `label_value_policy`: pilot_label_value is only 0/1 when compact evidence can decide it; otherwise null
- `compact_evidence_only`: True
- `raw_artifact_policy`: do not save or commit raw trajectories, full timeseries, .mat, .slx, .slxc, or slprj
