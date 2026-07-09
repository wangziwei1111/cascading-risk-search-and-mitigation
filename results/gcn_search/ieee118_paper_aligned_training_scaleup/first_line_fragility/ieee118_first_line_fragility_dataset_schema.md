# IEEE118 First-Line Fragility Dataset Schema

- `x_gcn`: S0 graph features, shape `num_s0_samples x 186 x input_channels`.
- `y_fragile` / `y_gcn`: first-line fragility labels. A positive label means the first line is not first-step critical and has at least one valid critical second outage.
- `loss_mask`: known non-first-step-critical first-line labels used in fragility loss.
- `first_step_direct_shed_label`: direct S0 load-shed labels retained for diagnostics but excluded from fragility loss.
- Splits are inherited by seed from the paper-aligned dataset.
