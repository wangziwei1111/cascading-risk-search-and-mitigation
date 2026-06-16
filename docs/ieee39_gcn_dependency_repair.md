# IEEE39 GCN Dependency Repair

This round is local dependency environment repair.

It did not train GCN.
It did not run the formal GCN audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not save any production model.

## Plain Summary

The previous blocker was not a modeling problem. It was a broken local Python
environment. The old active interpreter was:

- `E:\Scripts\python.exe`
- `sys.prefix = E:`

That broken bare-drive prefix caused `torch` to build an invalid DLL path like
`E:bin`, which produced the previous `WinError 87`.

This round avoids the broken interpreter by creating a clean repository-local
virtual environment:

- `.venv-gcn-audit`

Inside that clean environment:

- `torch` CPU version imports successfully
- `torch_geometric` imports successfully
- the old dependency blocker is resolved

## Repair Result

- repair scope: `local_dependency_environment_repair`
- new venv path: `C:\Users\24186\Documents\New project 7\simulink-dynamic-validation-worktree\.venv-gcn-audit`
- new Python executable: `.venv-gcn-audit\Scripts\python.exe`
- new `sys.prefix`: repository-local absolute path
- new Python prefix is absolute: `true`
- new Python prefix is not bare drive: `true`
- `torch` import success: `true`
- `torch version`: `2.12.0+cpu`
- `torch cuda version`: `None`
- `torch cuda available`: `false`
- `torch_geometric` import success: `true`
- `torch_geometric version`: `2.8.0`
- dependency blocker resolved: `true`

## Important Boundary Notes

- `.venv-gcn-audit` is local only and must not be committed
- wheel / DLL / site-packages / torch cache / model files must not be committed
- this round still does not prove GCN useful
- this round still does not prove GCN useless
- if the imports are fixed, the next round may rerun the strict no-leakage audit
- do not deploy anything yet
- do not retrain the reranker yet
- `phasor_RMS` is not EMT
- generator_speed_proxy is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Next Step

Because the dependency blocker is now resolved, the next round can rerun:

`python scripts/gcn_search/run_ieee39_strict_no_leakage_gcn_usefulness_audit.py`

That rerun must still be a separate round. This repair round itself does not
run the audit.
