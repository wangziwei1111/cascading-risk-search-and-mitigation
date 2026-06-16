# IEEE39 GCN Dependency Blocker Diagnosis

This round is dependency diagnosis only.

It did not train GCN.
It did not rerun the formal GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not save any production model.

## Plain Summary

The previous round already proved that the strict no-leakage audit framework can
run in baseline-only mode, but the GCN branch is still blocked by the local
Python dependency environment. So this round does not make any usefulness
conclusion. It only diagnoses why the local GCN environment cannot import.

The current blocker is not the dataset, not the strict holdout split design, and
not the audit logic. The blocker is local dependency readiness: `torch`
currently fails to import, `torch_geometric` is not available in the active
environment, and the Windows DLL search context is suspicious.

## Current Diagnosis Result

- diagnosis scope: `dependency_diagnosis_only`
- previous GCN dependency status: `blocked_by_missing_gcn_dependency`
- current Python executable: `E:\Scripts\python.exe`
- current `sys.prefix`: `E:`
- current `sys.base_prefix`: `E:`
- current `sys.exec_prefix`: `E:`
- `torch` spec present: `true`
- `torch` import success: `false`
- `torch` import error: `WinError 87` with `E:bin`
- `torch_geometric` spec present: `false`
- `torch_geometric` import success: `false`
- GCN dependency blocker still present: `true`

## Why `E:bin` Matters

The important new clue is that the active Python environment is not reporting a
normal rooted prefix such as `E:\...`. Instead, multiple Python prefix values
appear as bare `E:`. That is a drive-relative prefix, not a normal absolute
directory. When `torch` tries to assemble its DLL search directory, this can
turn into an illegal path like `E:bin`, which explains the current `WinError 87`
failure.

So the local blocker is currently best understood as:

1. the active Python environment itself is mis-resolved or incomplete;
2. `torch` therefore cannot finish DLL initialization;
3. `torch_geometric` is also absent, so even after `torch` is fixed, PyG still
   needs to be installed in the corrected environment.

## Safe Repair Direction

The recommended repair order is:

1. fix the active Windows Python / DLL path issue first;
2. verify `torch` import in the corrected active environment;
3. install or verify `torch_geometric` and matching PyG extensions only after
   `torch` imports cleanly;
4. rerun dependency diagnosis;
5. only after import probes pass, rerun the strict no-leakage audit in a later
   round.

Do the repair locally. Do not commit `.venv`, `site-packages`, wheels, DLLs,
torch cache, or model files.

## Important Boundary Notes

- previous round completed baseline-only audit only
- current round does not make any GCN usefulness conclusion
- post-fault dynamic measurements still must not be used as GCN input
- `phasor_RMS` is not EMT
- generator_speed_proxy is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Next Step

Use the generated diagnosis artifacts in:

`results/gcn_search/ieee39_gcn_dependency_diagnosis/`

Repair the local environment first, rerun the dependency diagnosis, and only
then consider rerunning the strict no-leakage GCN usefulness audit.

## Follow-Up Repair Note

In the next repair round, the blocker is resolved by creating a clean local
`.venv-gcn-audit` environment and avoiding the broken `E:\Scripts\python.exe`
launcher path. That repair round remains dependency-environment work only; it
still does not train GCN, does not run Simulink, and does not rerun the formal
audit in the same round.
