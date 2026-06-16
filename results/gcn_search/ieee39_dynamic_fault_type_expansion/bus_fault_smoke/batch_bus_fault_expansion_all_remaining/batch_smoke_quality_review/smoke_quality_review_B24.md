# Smoke Quality Review: B24

This is a smoke output quality review only. It did not run Simulink, did not
run actual smoke, did not export labels, did not train GCN, did not retrain the
reranker, and did not run a GCN usefulness audit.

- scenario: `BF_B24_TEMP_SMOKE`
- selected fault block: `Grid/Fault_B24_TEMP`
- quality review passed for candidate export: `True`
- candidate export eligible next round: `True`
- measurement extraction status: `voltage_speed_angle`
- metrics all finite: `True`
- signal source has frequency proxy: `True`
- unstable_flag: `True`
- failed checks: `none`
- warning checks: `none`

The `unstable_flag` value is a compact smoke threshold marker, not a final
stability conclusion. `generator_speed_proxy` is not direct frequency, and the
model remains phasor_RMS, not EMT.
