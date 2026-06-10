# IEEE39 Graphical Dynamic Model Plan

## Why Round 26 Changes Direction

Previous RTS-79 dynamic validation used a simplified swing-equation prototype. That prototype is useful for diagnostics, but it does not contain a full graphical network with machine, exciter, governor, line, load, and measurement subsystems.

Round 26 therefore shifts the future dynamic-aware reranker backend toward an existing IEEE 39-bus / New England 10-machine graphical Simulink model.

## Target Backend

Primary candidate:

`C:/Users/24186/Documents/MATLAB/Examples/R2024b/simscapeelectrical/IEEE39BusSystemExample/IEEE39BusSystem.slx`

The source model is kept unchanged. The wrapper script copies it to a generated results directory and writes an interface summary.

## Planned Data Flow

1. Inventory local IEEE39 / New England Simulink models.
2. Check MATLAB toolboxes.
3. Select a primary model.
4. Generate a wrapper copy under `results/gcn_search/ieee39_graphical_dynamic_model/generated_models/`.
5. Add or map fault-injection and line/breaker trip interfaces in the wrapper.
6. Run no-fault, N-1, N-2, fault-clearing, and relay-trip tests.
7. Export summary CSV and event-log CSV.
8. Convert those outputs into `ieee39_dynamic_label_preview.csv` and `ieee39_dynamic_label_schema.json`.
9. Only after label credibility is improved, train an IEEE39 dynamic-aware reranker.

## Current Interface Fields

The dynamic-label schema contains:

- `path`
- `first_line`
- `second_line`
- `dynamic_unstable`
- `dynamic_stress_score`
- `min_frequency_hz`
- `min_voltage_pu`
- `max_rotor_angle_separation_deg`
- `relay_trip_count`
- `breaker_trip_count`

## Claim Boundaries

- If the selected model is phasor/RMS, do not call it EMT.
- If protection settings are incomplete, do not call it an engineering-grade protection model.
- If real machine and protection parameters are incomplete, do not report engineering-grade stability conclusions.
- This round builds a reusable dynamic-label generator interface. It does not train the dynamic-aware reranker.

## Next Step

The next technical step is to wire real fault and breaker injection into the generated IEEE39 wrapper, rerun fault tests with physical signal outputs, and then train the dynamic-aware reranker on IEEE39 dynamic labels.

## Round 27 Plan Refinement

Round 27 adds a pilot wrapper path:

- use the existing `Fault (Three-Phase)` block for temporal fault injection;
- map at least five transmission-line blocks for pilot line outage tests;
- record missing breaker paths as `manual_required`;
- add a basic relay proxy with undervoltage, underfrequency, and optional overcurrent thresholds;
- export relay settings, event logs, signal summaries, and dynamic-label quality summary.

Dynamic-aware reranker training remains blocked until the quality gate reports enough physical executed and simulation-successful labels.
