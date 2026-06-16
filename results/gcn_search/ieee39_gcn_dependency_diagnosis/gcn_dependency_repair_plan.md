# GCN Dependency Repair Plan

```json
{
  "plan_scope": "dependency_diagnosis_only",
  "current_blocker_summary": {
    "torch_spec_present": true,
    "torch_import_ok": false,
    "torch_import_error": "[WinError 87] 参数错误。: 'E:bin'",
    "torch_geometric_spec_present": false,
    "torch_geometric_import_ok": false,
    "suspected_primary_blocker": "windows_path_dll_issue"
  },
  "route_a_path_dll_cleanup_first": {
    "when_to_use": [
      "torch import fails",
      "WinError 87 appears",
      "PATH contains E:bin or other drive-relative entries"
    ],
    "steps": [
      "Do not modify repository files for PATH cleanup.",
      "Inspect the active shell PATH and remove suspicious drive-relative entries such as E:bin from the local session first.",
      "Verify that the active Python path, Scripts path, CUDA path, and any torch lib path do not conflict.",
      "Open a fresh shell after cleanup and rerun the import probes.",
      "Do not commit local environment-variable edits."
    ],
    "detected_suspicious_entries": []
  },
  "route_b_clean_virtualenv": {
    "powershell_example_only_do_not_auto_execute": [
      "python -m venv .venv-gcn-audit",
      ".\\.venv-gcn-audit\\Scripts\\Activate.ps1",
      "python -m pip install --upgrade pip",
      "python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu",
      "python -m pip install torch-geometric",
      "If torch-geometric needs extra compiled extensions, use the official matching wheel index for the detected torch/python platform."
    ]
  },
  "route_c_conda_optional": {
    "commands": [
      "conda create -n ieee39-gcn-audit python=3.11",
      "conda activate ieee39-gcn-audit",
      "Then choose CPU/GPU torch and matching PyG installation for the detected platform."
    ]
  },
  "verification_commands": [
    "python -c \"import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())\"",
    "python -c \"import torch_geometric; print(torch_geometric.__version__)\"",
    "python scripts/gcn_search/diagnose_ieee39_gcn_dependency_blocker.py --strict --write-report",
    "python scripts/gcn_search/run_ieee39_strict_no_leakage_gcn_usefulness_audit.py"
  ],
  "verification_note": "The last audit command should be used only after torch and torch_geometric import probes both pass.",
  "prohibited_actions": [
    "Do not commit .venv, site-packages, wheels, DLLs, torch cache, or model files.",
    "Do not modify Simulink files.",
    "Do not bypass the forbidden feature policy.",
    "Do not fake torch / torch_geometric success."
  ],
  "repo_dependency_context": {
    "dependency_files_found": [
      "requirements.txt",
      "README.md"
    ],
    "repo_dependency_file_details": {
      "requirements.txt": {
        "exists": true,
        "mentions_torch": true,
        "mentions_torch_geometric": false,
        "mentions_pyg_extensions": false
      },
      "pyproject.toml": {
        "exists": false
      },
      "environment.yml": {
        "exists": false
      },
      "setup.py": {
        "exists": false
      },
      "setup.cfg": {
        "exists": false
      },
      "README.md": {
        "exists": true,
        "mentions_torch": false,
        "mentions_torch_geometric": false,
        "mentions_pyg_extensions": false
      }
    },
    "torch_declared_in_repo": true,
    "torch_geometric_declared_in_repo": false,
    "pyg_extensions_declared_in_repo": false,
    "dependency_documentation_missing": false
  },
  "recommended_next_step": "fix Windows PATH / DLL path issue first, then reinstall or verify torch and torch_geometric in the active environment"
}
```
