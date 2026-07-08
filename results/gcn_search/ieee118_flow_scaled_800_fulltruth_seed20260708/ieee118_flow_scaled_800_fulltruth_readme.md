# IEEE118 Flow-Scaled 8.00 Full-Truth Audit

This directory contains compact audit outputs for the IEEE118 ordered N-2 full-truth run with synthetic OPA-style thermal limits.

## Configuration

- Case: IEEE118
- Seed: 20260708
- Limit mode: `flow_scaled`
- Flow-limit scale: 8.00
- Minimum RATE_A: 1.0 MW
- Candidate ordered N-2 paths: 34,410

Command:

```bash
python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py \
  --seeds 20260708 \
  --limit-mode flow_scaled \
  --flow-limit-scale 8.00 \
  --min-rate-a 1.0 \
  --output-dir results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708 \
  --resume \
  --checkpoint-every 500
```

## Summary

- Total rows: 34,410
- Converged rows: 34,410
- Error rows: 0
- Critical rows: 1,859
- Critical ratio: 0.054025
- Relay-cascade rows: 1,659
- Relay-cascade ratio: 0.048213
- Island-only rows: 200
- Redispatch-shed rows: 2
- Mixed rows: 1,659
- Maximum load shed path: `L121->L125`
- Maximum load shed: 111.760638 MW
- Maximum relay trips per path: 20

The full raw 34,410-row CSV is intentionally kept local and is not committed. This stage is still full-truth preparation; it is not IEEE118 GCN training or search-efficiency evaluation.
