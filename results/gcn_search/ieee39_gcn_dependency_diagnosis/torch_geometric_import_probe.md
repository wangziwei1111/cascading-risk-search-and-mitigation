# Torch Geometric Import Probe

```json
{
  "module_name": "torch_geometric",
  "import_ok": false,
  "version": null,
  "module_file": null,
  "error": "No module named 'torch_geometric'",
  "traceback_tail": [
    "Traceback (most recent call last):",
    "  File \"C:\\Users\\24186\\Documents\\New project 7\\simulink-dynamic-validation-worktree\\scripts\\gcn_search\\diagnose_ieee39_gcn_dependency_blocker.py\", line 315, in _import_module_report",
    "    module = importlib.import_module(module_name)",
    "  File \"E:\\Lib\\importlib\\__init__.py\", line 88, in import_module",
    "    return _bootstrap._gcd_import(name[level:], package, level)",
    "           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",
    "  File \"<frozen importlib._bootstrap>\", line 1387, in _gcd_import",
    "  File \"<frozen importlib._bootstrap>\", line 1360, in _find_and_load",
    "  File \"<frozen importlib._bootstrap>\", line 1324, in _find_and_load_unlocked",
    "ModuleNotFoundError: No module named 'torch_geometric'"
  ],
  "likely_causes": [
    "torch_geometric is not installed in the active environment.",
    "torch_geometric is installed but depends on a torch environment that cannot import cleanly."
  ]
}
```
