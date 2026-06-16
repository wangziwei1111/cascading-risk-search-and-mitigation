# IEEE39 All-Remaining Bus-Fault Manual Connection Evidence

The user declared that 37 temporary local copies have been manually wired. This
round collects and reviews manual connection evidence. It does not run Simulink
simulation, does not run actual smoke, does not export labels, does not train
GCN, does not retrain the reranker, and does not run a GCN usefulness audit.

## Summary

- total targets: `37`
- temp models found: `37`
- fault blocks found: `37`
- Update Diagram success: `37`
- automated evidence check passed: `37`
- human verified injection point: `37`
- safe to run smoke recommendation: `37`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

Only buses that pass evidence should enter the next separate readiness dry-run
round. Do not directly jump to smoke, do not export labels, and do not train
GCN.

## B16

B16 is special handling. The old `Grid/Fault (Three-Phase)` must not be moved
or renamed, and the new selected fault block must be `Grid/Fault_B16_TEMP`.

## Boundary

B39/B26 remain existing candidate labels, not formal labels. The 37 new targets
are not candidate labels and are not smoke success. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.

## Readiness Dry-Run Follow-Up

The 37 manual evidence-passed targets have now completed a separate batch
readiness dry-run. This follow-up still did not run Simulink simulation, did
not run actual smoke, did not export labels, did not train GCN, did not retrain
the reranker, and did not run a GCN usefulness audit.

- readiness checked: `37`
- ready for next-round actual smoke: `37`
- blocked before smoke: `0`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

This only means the 37 temporary copies can be considered for a later actual
smoke round. The 37 new targets are still not candidate labels and still not
smoke success.

## Actual Smoke Follow-Up

The later batch actual smoke round attempted all 37 readiness-passed targets.
All 37 Simulink smoke runs succeeded and produced `voltage_speed_angle`
measurements. This still did not export labels, did not train GCN, did not
retrain the reranker, and did not run a GCN usefulness audit.

The next step is smoke quality review for successful buses before any label
export. The 37 new targets are still not candidate labels.

## Smoke Quality Review Follow-Up

The later smoke quality review checked the 37 already generated smoke reports.
It did not run Simulink, did not run actual smoke, did not export labels, did
not train GCN, did not retrain the reranker, and did not run a GCN usefulness
audit.

All 37 targets passed this review for a later candidate-only export round. They
are still not candidate labels in the quality-review round.
