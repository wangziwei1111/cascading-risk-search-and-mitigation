# Leakage Notes

`leaky_dynamic_measurement_features` includes compact dynamic measurement
columns such as voltage, frequency proxy, speed deviation, and rotor-angle
separation. Because `dynamic_stress_score` is synthesized from the same compact
measurements, this setting is an optimistic preview upper-bound, not credible
generalization evidence.

`no_dynamic_measurement_features` removes those measurement columns but may
still include line identity, source-model category, and topology-derived
features. It is less leaky but still only preview evidence.

`topology_only_features` uses line-map / topology / fault-setup information and
avoids compact measurements and line_id one-hot features. This is the most
conservative preview feature set in this round.

No Simulink simulation was run. No `.slx` was modified. L12 remains excluded.
The result remains phasor_RMS preview evidence, not EMT. It is not a final
dynamic performance conclusion.
`generator_speed_proxy` is not direct frequency. The handwired breaker remains
pilot breaker-like validation, not engineering-grade protection.
