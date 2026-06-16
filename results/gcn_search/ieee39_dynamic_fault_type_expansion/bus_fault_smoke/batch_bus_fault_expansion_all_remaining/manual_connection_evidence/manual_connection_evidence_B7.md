# Manual Connection Evidence B7

This evidence is for manual connection review only. It is not actual smoke,
not label export, not GCN training, and not GCN usefulness audit.

| field | value |
| --- | --- |
| target_bus | `B7` |
| special_handling | `false` |
| temp_model_exists | `true` |
| fault_block_found | `true` |
| fault_block_name_correct | `true` |
| update_diagram_success | `true` |
| automated_evidence_check_passed | `true` |
| human_verified_injection_point | `true` |
| safe_to_run_smoke_recommendation | `true` |

## Checks

- failed_checks: `[]`
- warning_checks: `[]`
- selected_fault_block_path: `Grid/Fault_B7_TEMP`
- selected_injection_block_path: `[2376.06457519531 2199.06457519531]`
- selected_injection_port_description: `[2376.06457519531 2199.06457519531]`

## Boundary

`simulink_smoke_run=false`, `smoke_success=false`, `labels_exported=false`,
`candidate_label_exported=false`, `gcn_trained=false`, and
`reranker_retrained=false`.
