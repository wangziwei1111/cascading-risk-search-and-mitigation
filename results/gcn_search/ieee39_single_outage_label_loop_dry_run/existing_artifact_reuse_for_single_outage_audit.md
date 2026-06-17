# IEEE39 Existing Artifact Reuse For Single-Outage Audit

- `existing_multi_line_or_path_labels_found`: False
- `reusable_for_single_outage_count`: 0
## reusable_sequences
```json
[]
```

- `non_reusable_reason`: Existing approved artifacts provide base_state x branch pilot labels only. They do not provide controlled single_outage_state x next_branch labels.
- `bus_fault_labels_used`: False
- `scenario_level_label_limitation`: Scenario-level dynamic outputs may be used as future labels/targets only, not as GCN inputs.
- `l12_excluded_or_special`: True
- `recommended_generation_strategy`: implement controlled generation runner for selected single-outage pilot pairs in a separate round
