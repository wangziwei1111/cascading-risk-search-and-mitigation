# Manual Bus-Fault Injection Review Template: B39

This template is for GUI review only. It is not smoke success and must not be
used to export labels, train GCN, or retrain the reranker.

## Candidate Blocks

- [ ] `Grid/Bus39`
- [ ] `Grid/B39 to B1`
- [ ] `Grid/B9 to B39`
- [ ] `Generators/Gen1@Bus39`
- [ ] `Grid/GB39B1F`
- [ ] `Grid/GB39B1T`
- [ ] `Grid/GB9B39F`
- [ ] `Grid/GB9B39T`

## Review Fields

| field | value |
| --- | --- |
| target_bus | B39 |
| reviewer |  |
| review_date |  |
| temp_model_path | `results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_B39_TEMP_LOCAL_ONLY.slx` |
| selected_injection_block_path |  |
| selected_injection_port_description |  |
| selected_fault_block_path |  |
| update_diagram_error |  |
| reviewer_notes |  |

## Safety Checklist

- [ ] source model opened read-only if referenced.
- [ ] source model was not saved.
- [ ] temporary model is not committed.
- [ ] target physical terminal is clear.
- [ ] `Fault (Three-Phase)` can be connected in parallel.
- [ ] original network connection is preserved.
- [ ] no unintended bypass is created.
- [ ] no floating ports are created.
- [ ] no unintended islanding is created.
- [ ] Update Diagram is attempted.
- [ ] Update Diagram succeeds.
- [ ] measurement signals are expected to remain available.
- [ ] screenshot or manual evidence is recorded.

Only if every safety item passes should the next round consider temporary
smoke. Default recommendation remains `do_not_run_smoke`.

Current defaults: `human_verified_injection_point = false`,
`safe_to_run_smoke_recommendation = false`, old formal gate `35 / 33 / 33`, v2
candidate count `40`.
