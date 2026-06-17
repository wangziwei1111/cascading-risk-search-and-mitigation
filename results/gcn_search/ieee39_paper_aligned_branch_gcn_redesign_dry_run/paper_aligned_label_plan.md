# Paper-Aligned Label Plan

- `paper_label_type`: branch_vulnerability_binary_vector
- `label_shape`: num_states x num_branches
- `y_gcn_k_semantics`: whether disconnecting branch k from current state leads to load shedding / unacceptable dynamic risk
- `our_current_labels`: scenario-level dynamic_stress_score / unstable_flag
- `gap_between_paper_labels_and_current_labels`: current IEEE39 labels are scenario-level outcomes, not a per-state vector over every candidate branch k
- `can_build_paper_labels_from_existing_data`: False
- `missing_label_generation_requirements`:
  - state-wise branch candidate loop over L01-L34
  - paper-style label generator that applies next branch outage k from current state
  - documented proxy relation between OPA load shedding and Simulink dynamic instability
- `possible_adaptation`:
  - line-trip labels can be used first for branch outage vulnerability
  - bus-fault labels are not directly paper-aligned and should be separate extension
  - dynamic_stress_score can be mapped to binary unstable label only as output target, not input
  - load shedding in OPA is not identical to Simulink dynamic instability, so proxy semantics must be documented
- `bus_fault_labels_directly_paper_aligned`: False
- `line_trip_labels_first_priority`: True
