# IEEE39 B26 Manual Bus-Fault Verification Plan

This document prepares the next independent bus-fault sample workflow. The
priority target is `B26`, but this round does not run Simulink, does not submit
`.slx`, does not submit `.slx` artifacts, does not train GCN, does not retrain
the reranker, does not retrain the reranker, and does not export labels.

## Why B26 Next

The B39 holdout result shows weak bus-fault / fault-family generalization:
dynamic_stress_score is underestimated by about `0.211603`, even though the
unstable probability is high. Therefore the next useful step is to prepare
another independent bus-fault sample, not to immediately connect the dynamic
labels back to the main GCN/reranker workflow.

## Current B26 Status

- B26 is the next priority bus-fault sample.
- B26 remains unverified.
- B26 is not smoke success.
- B26 is not a candidate label.
- `human_verified_injection_point = false`
- `safe_to_run_smoke_recommendation = false`

## Candidate Blocks To Inspect

- `Grid/Bus26_1`
- `Grid/Bus26_2`
- `Grid/B25 to B26`
- `Grid/B26 to B28`
- `Grid/B26 to B29`
- `Grid/B27 to B26`

## Lessons From B39

- Prefer the real busbar physical node.
- Do not cut original lines.
- Prefer parallel fault injection.
- Do not move the old fault block in the source model.
- Work only inside the ignored temporary local copy.
- Click Update Diagram first; do not directly Run.

## Manual Tasks For The User

1. Open the B26 temporary local copy in Simulink GUI.
2. Inspect `Grid/Bus26_1` and `Grid/Bus26_2`.
3. Record each block's `BlockType`, `MaskType`, `MaskNames`, `MaskValues`, and
   `PortConnectivity`.
4. Decide which block is the real busbar physical node.
5. Copy or create a temporary fault block named `Grid/Fault_B26_TEMP`.
6. Use initial settings `fault_start_time = 0.5 s` and `fault_duration = 0.08 s`.
7. Try Update Diagram only.
8. If Update Diagram succeeds, fill the manual review template.

## What Codex Should Not Do This Round

Codex should not run Simulink, should not claim B26 is verified, should not
claim B26 smoke success, and should not export any B26 label.

## Boundaries

The old formal gate remains `35 / 33 / 33`; the v2-plus-B39 count remains `41`.
The model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.
