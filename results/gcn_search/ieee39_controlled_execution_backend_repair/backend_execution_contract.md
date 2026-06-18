# IEEE39 Backend Execution Contract

- `contract_scope`: selected_pair_execution_contract
- `allowed_pair_count`: 32
- `full_1056_generation_allowed`: False
- `requires_approved_selected_pairs_only`: True
- `requires_explicit_execute_flag`: True
- `default_mode`: dry_run_or_blocked
## allowed_outputs
```json
[
  "compact per-pair evidence rows",
  "backend repair/readiness summary",
  "timeout or blocked status",
  "pilot_label_value only when future approved evidence can decide 0/1"
]
```

## forbidden_outputs
```json
[
  "formal training labels",
  "raw trajectories",
  "full timeseries",
  ".mat files",
  ".slx or .slxc modifications",
  "model checkpoints"
]
```

- `timeout_policy`: timeout remains timeout/unknown and is not converted to 0/1
- `unknown_policy`: unknown and blocked remain null
- `failed_policy`: failed remains failed/unknown and is not converted to 0/1
- `label_value_policy`: pilot_label_value remains null unless future approved compact evidence determines 0 or 1
- `formal_label_export_policy`: False
- `raw_artifact_policy`: commit only compact JSON/MD/CSV summaries; do not commit raw trajectories, full timeseries, .mat, .slx, .slxc, or slprj
