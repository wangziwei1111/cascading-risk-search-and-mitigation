# IEEE118 Original RTS-79 GCN Reuse

This directory contains compact outputs for the formal IEEE118 `flow_scaled=8.00` run that reuses the original RTS-79 `PaperStyleRts79Gcn` model class.

Completed method: `RTS79_GCN_reused_on_IEEE118`.

`GCN_smoke` is not used as a formal result. PIO-GCN full reuse is not completed in this stage.

Key checks:

- Torch import succeeded in `.venv` with `torch 2.11.0+cpu`.
- Converted paths: 34,410.
- Critical labels: 1,859.
- Relay-cascade labels: 1,659.
- Top-5000 critical recall: 0.5697 for reused RTS-79 GCN vs 0.2673 for LODF_yP.
- Top-5000 relay-cascade recall: 0.6034 for reused RTS-79 GCN vs 0.2731 for LODF_yP.

Large local files intentionally not committed: raw full-truth CSV, 2.7GB Step2-State CSV, full predictions CSV, and model checkpoint.
