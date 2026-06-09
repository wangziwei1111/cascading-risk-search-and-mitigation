# Relay Threshold vs Security Constraint

## Core Distinction

`L_m^max` is the long-term line security limit used by OPF/security constraints.

`beta * L_m^max` is the relay tripping threshold. In this project the default `beta` is `1.2`.

The loading ratio is:

```text
loading_ratio = |flow| / L_m^max
```

Therefore:

- `loading_ratio <= 1.0`: the line is within the long-term security constraint.
- `1.0 < loading_ratio <= beta`: the line violates the security constraint, but it does not trip by relay logic.
- `loading_ratio > beta`: the relay threshold is exceeded and passive relay trip may be triggered.

In other words, exceeding `L_m^max` is not the same as relay tripping. The prototype must not turn every `loading_ratio > 1.0` line into an offline branch.

## L27 -> L2 -> L6 Interpretation

For the RTS-79 example often described as `L27 -> L2`, the important point is that `L6` may exceed the long-term security limit. That does not necessarily mean `L6` exceeds the relay threshold.

If:

```text
1.0 < loading_ratio(L6) <= beta
```

then the correct interpretation is a security-constraint violation. The system should first try redispatch / load shedding approximation to reduce the `L6` flow back toward `loading_ratio <= 1.0`. This is a flow-constraint-driven load-shedding mechanism, not an `L6` relay-trip islanding mechanism.

Only if:

```text
loading_ratio(L6) > beta
```

should the passive relay trip logic open `L6`.

## Current Simulink Prototype

The current Simulink dynamic validation uses an approximation:

- `loading_ratio > beta`: records `passive_relay_trip`.
- `1.0 < loading_ratio <= beta`: records `security_redispatch_or_load_shed`.
- security redispatch/load shedding is approximated by reducing load near the overloaded line terminal buses.

This redispatch/load shedding approximation is not a full AC OPF or DC OPF. It is only a prototype hook to preserve the physical distinction between security constraints and relay thresholds.
