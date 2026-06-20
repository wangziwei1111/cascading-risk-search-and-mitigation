# IEEE39 SPP001 Bridge Topology Comparison

- `comparison_scope`: spp001_bridge_topology_comparison
## l15_topology_comparison
```json
{
  "line_id": "L15",
  "bridge_neighbors": [],
  "source_neighbors": [
    "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/B21 to B22",
    "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/Bus21",
    "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/Simulink-PS\nConverter"
  ],
  "same_neighbor_count": false,
  "shared_neighbor_count": 0,
  "topology_signature_matches_source": false,
  "audit_note": "name-normalized graph comparison is conservative; mismatch blocks execution"
}
```

## l04_topology_comparison
```json
{
  "line_id": "L04",
  "bridge_neighbors": [
    "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/B11 to B6",
    "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/Bus6",
    "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/Simulink-PS\nConverter3"
  ],
  "source_neighbors": [
    "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L04/Grid/B11 to B6",
    "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L04/Grid/Bus11",
    "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L04/Grid/Simulink-PS\nConverter"
  ],
  "same_neighbor_count": true,
  "shared_neighbor_count": 0,
  "topology_signature_matches_source": false,
  "audit_note": "name-normalized graph comparison is conservative; mismatch blocks execution"
}
```

- `physical_bridge_valid`: False
- `same_wrapper_block_presence_only`: True
