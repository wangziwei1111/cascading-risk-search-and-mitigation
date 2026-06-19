# IEEE39 SPP001 Same-Wrapper Bridge Local Execution Checklist

- Obtain separate manual approval before building any local lab copy.
- Use only pair_id `SPP001`, prior `L15`, next `L04`.
- Build a local-only lab copy outside tracked Git artifacts.
- Confirm both `L15_TripCommand` and `L04_TripCommand` belong to the same model.
- Do not run SPP001 smoke in the bridge-build round.
- Do not export formal labels or train GCN.
- Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full timeseries.
- Remember: `phasor_RMS` is not EMT, `generator_speed_proxy` is not direct frequency, and temporary bus-fault injection is not engineering-grade protection.
