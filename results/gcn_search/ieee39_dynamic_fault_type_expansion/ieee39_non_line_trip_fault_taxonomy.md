# IEEE39 Non-Line-Trip Fault Taxonomy

This file prepares additional IEEE39 dynamic-label fault types without running Simulink or modifying `.slx` files.

Current audit:
- existing three-phase fault script: `True`
- fault_start_s / fault_clear_s parameterization: `True`
- different bus fault selector without `.slx` change: `False`
- load-step support without `.slx` change: `False`
- generator-trip / mechanical-power-step support without `.slx` change: `False`

| fault_type | requires_slx_modification | runnable_with_existing_scripts | recommended_first_batch | description |
|---|---:|---:|---:|---|
| `three_phase_bus_fault_clear` | False | True | True | Use the existing Simscape Fault (Three-Phase) block and clear it after a short duration. |
| `fault_duration_sweep` | False | True | True | Vary fault_clear_s while keeping fault_start_s fixed to test sensitivity to clearing time. |
| `relay_proxy_fault` | False | True | True | Use the existing basic relay proxy case as a non-engineering-grade relay-like disturbance. |
| `load_step_disturbance` | True | False | False | Apply a small load increase/decrease at a selected bus. |
| `generator_trip_or_mechanical_power_step` | True | False | False | Trip a generator or perturb its mechanical power input. |
| `bus_voltage_disturbance_or_reference_event` | True | False | False | Perturb a voltage reference or bus voltage disturbance input if a safe model input exists. |

Boundaries:
- This preparation does not create new training-ready labels.
- This preparation does not run Simulink.
- This preparation does not modify `.slx` files or Simscape physical wiring.
- L12 remains excluded and is not fixed here.
- The model remains `phasor_RMS`, not EMT.
- `generator_speed_proxy` is not direct frequency.
- The handwired breaker workflow is pilot breaker-like validation, not engineering-grade protection.
