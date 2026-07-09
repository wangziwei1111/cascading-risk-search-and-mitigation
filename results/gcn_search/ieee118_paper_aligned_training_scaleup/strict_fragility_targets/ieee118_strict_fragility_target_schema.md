# IEEE118 Strict Fragility Target Schema

- `critical_count_topq`: top quantile by number of critical second outages.
- `relay_count_topq`: top quantile by relay-cascade second outages.
- `max_shed_topq`: top quantile by maximum load shed.
- `composite_topq`: top quantile by z-scored critical count, relay count, max shed, and sum shed.
- First-step critical lines are excluded from loss and retained as direct-shed diagnostics.

Note: sampled train/validation S1 labels from the pilot dataset contain critical labels, but not relay-specific labels or load-shed severity. The held-out 20260708 seed uses complete full-truth relay/load-shed fields; sampled relay/load-shed targets should therefore be treated as pilot diagnostics, not final severity labels.
