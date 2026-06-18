# IEEE39 Future Controlled Generation Run Plan

- `run_plan_scope`: future_controlled_single_outage_pilot_generation
- `dry_run_only_this_round`: True
- `new_simulink_run_this_round`: False
- `future_runner_entrypoint`: future script should execute selected_single_outage_pilot_pairs after manual approval
- `selected_pair_count`: 32
## expected_outputs_per_pair
```json
[
  "pair execution summary",
  "label evidence summary",
  "timeout/error status",
  "no raw trajectory committed",
  "label_value remains withheld unless an approved label export round follows"
]
```

- `timeout_policy`: timeouts remain unknown/null and are not converted to 0/1
- `unknown_policy`: unknown, missing, timeout, or failed cases remain null/planned/blocked
- `l12_exclusion_policy`: any pair with L12 as prior or candidate branch stays excluded
- `no_raw_trajectory_commit_policy`: True
- `no_formal_label_export_this_round`: True
- `required_manual_approval_before_execution`: True
