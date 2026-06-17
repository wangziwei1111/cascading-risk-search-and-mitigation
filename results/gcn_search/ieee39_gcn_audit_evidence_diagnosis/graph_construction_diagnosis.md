# Graph Construction Diagnosis

```json
{
  "analysis_scope": "graph_construction_diagnosis",
  "sample_granularity": "candidate_as_node_in_one_dense_graph",
  "num_candidate_nodes": 79,
  "node_feature_count": 168,
  "node_feature_inputs": [
    "duration_s",
    "fault_start_s",
    "fault_clear_s",
    "one_hot(fault_type)",
    "one_hot(trip_implementation)",
    "one_hot(line_id)",
    "one_hot(target_bus)",
    "one_hot(target_bus_or_component)",
    "one_hot(source_model_type)"
  ],
  "edge_construction": "Dense normalized adjacency built by equality of line_id, target_bus, target_bus_or_component, fault_type, and source_model_type.",
  "edge_index_representation": "No sparse edge_index is used; the implementation uses a dense normalized adjacency matrix.",
  "message_passing_usage": "Message passing is norm_adj @ features, then norm_adj @ hidden states.",
  "adjacency_nonzero_entries": 3277,
  "adjacency_density": 0.5250761095978209,
  "gcn_hidden_dim": 32,
  "gcn_epochs_in_source_script": 250,
  "estimated_dense_gcn_parameter_count": 6530,
  "target_bus_enters_model_as": "one-hot categorical input and also contributes to equality-based graph edges.",
  "topology_message_passing_check": "Topology is not physical bus-branch electrical topology. Edges are candidate-similarity edges, so the graph may mainly propagate tabular category information.",
  "nominal_gcn_but_tabular_risk": true,
  "small_sample_risk": true,
  "repeated_graph_structure_risk": true,
  "weak_supervision_signal_risk": true,
  "parameter_to_sample_ratio": 82.65822784810126,
  "bus_fault_holdout_distribution_shift_risk": true,
  "target_bus_only_baseline_explains_signal": true,
  "diagnosis": "The current model is a real dense GCN computation, but the graph is built from categorical equality rather than electrical connectivity; with only 79 rows, this can make the GCN less stable than simpler tabular baselines."
}
```
