# IEEE39 SPP001 L15 Bridge Connectivity Inventory

- `inventory_scope`: l15_bridge_connectivity_inventory
## bridge
```json
{
  "model": "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab",
  "line_id": "L15",
  "breaker_name": "L15_HandwiredTimedBreaker",
  "command_name": "L15_TripCommand",
  "breaker_block_exists": true,
  "trip_command_block_exists": true,
  "breaker_block_path": "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/L15_HandwiredTimedBreaker",
  "trip_command_block_path": "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/L15_TripCommand",
  "trip_command_to_breaker_control_connected": false,
  "breaker_physical_ports_connected": false,
  "breaker_in_series_with_actual_branch": false,
  "breaker_physical_port_inventory": [
    {
      "port_kind": "LConn",
      "port_handle": 3902.0001220703125,
      "line_handle": -1,
      "connected": false,
      "neighbor_blocks": []
    },
    {
      "port_kind": "LConn",
      "port_handle": 3903.0001220703125,
      "line_handle": -1,
      "connected": false,
      "neighbor_blocks": []
    },
    {
      "port_kind": "RConn",
      "port_handle": 3904.0001220703125,
      "line_handle": -1,
      "connected": false,
      "neighbor_blocks": []
    }
  ],
  "trip_command_signal_trace": [],
  "breaker_neighbor_signature": [],
  "branch_name_matches_line_context": false,
  "unconnected_ports": [
    {
      "block": "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/L15_HandwiredTimedBreaker",
      "port_kind": "LConn",
      "port_handle": 3902.0001220703125,
      "line_handle": -1
    },
    {
      "block": "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/L15_HandwiredTimedBreaker",
      "port_kind": "LConn",
      "port_handle": 3903.0001220703125,
      "line_handle": -1
    },
    {
      "block": "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_same_wrapper_bridge_lab/Grid/L15_HandwiredTimedBreaker",
      "port_kind": "RConn",
      "port_handle": 3904.0001220703125,
      "line_handle": -1
    }
  ],
  "audit_note": "static block-port and line-handle audit only; no sim()"
}
```

## source
```json
{
  "model": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15",
  "line_id": "L15",
  "breaker_name": "L15_HandwiredTimedBreaker",
  "command_name": "L15_TripCommand",
  "breaker_block_exists": true,
  "trip_command_block_exists": true,
  "breaker_block_path": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/L15_HandwiredTimedBreaker",
  "trip_command_block_path": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/L15_TripCommand",
  "trip_command_to_breaker_control_connected": true,
  "breaker_physical_ports_connected": true,
  "breaker_in_series_with_actual_branch": true,
  "breaker_physical_port_inventory": [
    {
      "port_kind": "LConn",
      "port_handle": 8157.0001220703125,
      "line_handle": 8531.000366210938,
      "connected": true,
      "neighbor_blocks": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/Simulink-PS\nConverter"
    },
    {
      "port_kind": "LConn",
      "port_handle": 8158.0001220703125,
      "line_handle": 8533.000366210938,
      "connected": true,
      "neighbor_blocks": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/Bus21"
    },
    {
      "port_kind": "RConn",
      "port_handle": 8159.0001220703125,
      "line_handle": 8534.000366210938,
      "connected": true,
      "neighbor_blocks": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/B21 to B22"
    }
  ],
  "trip_command_signal_trace": [
    {
      "from_block": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/L15_TripCommand",
      "to_block": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/Simulink-PS\nConverter",
      "line_handle": 8532.000366210938
    },
    {
      "from_block": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/Simulink-PS\nConverter",
      "to_block": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/L15_HandwiredTimedBreaker",
      "line_handle": 8531.000366210938
    }
  ],
  "breaker_neighbor_signature": [
    "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/B21 to B22",
    "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/Bus21",
    "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15/Grid/Simulink-PS\nConverter"
  ],
  "branch_name_matches_line_context": true,
  "unconnected_ports": [],
  "audit_note": "static block-port and line-handle audit only; no sim()"
}
```

## comparison
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
