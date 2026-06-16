"""Diagnose the local IEEE39 GCN dependency blocker without training or simulation.

This script is environment-diagnosis only. It does not train GCN, does not run
the formal GCN usefulness audit, does not run Simulink, does not export labels,
and does not save any model artifact.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import importlib.util
import json
import os
import platform
import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis"
EXECUTION_SUMMARY_PATH = (
    ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_execution/gcn_usefulness_audit_execution_summary.json"
)
DEPENDENCY_BLOCKER_PATH = (
    ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_execution/dependency_blocker_report.json"
)
DRY_RUN_SUMMARY_PATH = (
    ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/gcn_audit_dry_run_validator_summary.json"
)
POLICY_PATH = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan/no_leakage_feature_policy.json"
SPLIT_MANIFEST_PATH = (
    ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan/strict_holdout_split_manifest.json"
)
AUDIT_DOC_PATH = ROOT / "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md"
ROUND_DOC_PATH = ROOT / "docs/ieee39_gcn_dependency_blocker_diagnosis.md"

SOURCE_COMMIT = "6c89098a2f4a127102b16d1ef990ec66e4b9d16c"
REPO_DEPENDENCY_FILES = [
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "setup.py",
    "setup.cfg",
    "README.md",
]
PROBE_MODULES = [
    "torch",
    "torch_geometric",
    "torch_scatter",
    "torch_sparse",
    "torch_cluster",
    "torch_spline_conv",
    "numpy",
    "pandas",
    "sklearn",
    "scipy",
]
PIP_SHOW_PACKAGES = [
    "torch",
    "torch-geometric",
    "torch-scatter",
    "torch-sparse",
    "torch-cluster",
    "torch-spline-conv",
]
IMPORT_PROBES = {
    "torch_import_probe": [
        sys.executable,
        "-c",
        "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())",
    ],
    "torch_geometric_import_probe": [
        sys.executable,
        "-c",
        "import torch_geometric; print(torch_geometric.__version__)",
    ],
    "torch_and_pyg_import_probe": [
        sys.executable,
        "-c",
        "import torch; import torch_geometric; print('torch_and_pyg_import_ok')",
    ],
}
DRIVE_RELATIVE_PATTERN = re.compile(r"^[A-Za-z]:[^\\/]")
BARE_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:$")
SUSPICIOUS_LITERAL_PATHS = {"E:bin", "E:\\bin", "E:/bin"}


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _write_summary_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["field", "value"])
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                writer.writerow([key, json.dumps(value, ensure_ascii=False)])
            else:
                writer.writerow([key, value])


def _report_md(title: str, payload: dict[str, Any]) -> str:
    return f"# {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n"


def _run_command(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except Exception as exc:  # pragma: no cover - defensive path
        return {
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "exception": str(exc),
            "traceback_tail": traceback.format_exc().splitlines()[-8:],
        }


def _git_check_ignore(path: Path) -> bool:
    try:
        completed = subprocess.run(
            ["git", "check-ignore", str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
        return completed.returncode == 0
    except Exception:
        return False


def _split_path_entries() -> list[str]:
    raw = os.environ.get("PATH", "")
    return raw.split(os.pathsep) if raw else []


def _probe_python_environment() -> dict[str, Any]:
    path_entries = _split_path_entries()
    suspicious_path_entries: list[str] = []
    invalid_path_entries: list[str] = []
    drive_relative_path_entries: list[str] = []
    empty_path_entries: list[str] = []
    python_path_entries: list[str] = []
    conda_or_venv_script_entries: list[str] = []
    cuda_path_entries: list[str] = []
    torch_lib_related_entries: list[str] = []
    unresolved_envvar_entries: list[str] = []

    for index, raw_entry in enumerate(path_entries):
        entry = raw_entry.strip().strip('"')
        if not entry:
            empty_path_entries.append(f"<empty@{index}>")
            continue
        if entry in SUSPICIOUS_LITERAL_PATHS:
            suspicious_path_entries.append(entry)
        if DRIVE_RELATIVE_PATTERN.match(entry):
            drive_relative_path_entries.append(entry)
            suspicious_path_entries.append(entry)
        if "%" in entry:
            unresolved_envvar_entries.append(entry)
        lowered = entry.lower()
        if "python" in lowered:
            python_path_entries.append(entry)
        if "\\scripts" in lowered or "/scripts" in lowered:
            if "conda" in lowered or ".venv" in lowered or "venv" in lowered:
                conda_or_venv_script_entries.append(entry)
        if "cuda" in lowered:
            cuda_path_entries.append(entry)
        if "torch" in lowered and ("\\lib" in lowered or "/lib" in lowered):
            torch_lib_related_entries.append(entry)
        path_obj = Path(entry)
        if not DRIVE_RELATIVE_PATTERN.match(entry) and "%" not in entry and not path_obj.exists():
            invalid_path_entries.append(entry)

    suspicious_path_entries = sorted(dict.fromkeys(suspicious_path_entries))
    invalid_path_entries = sorted(dict.fromkeys(invalid_path_entries))
    drive_relative_path_entries = sorted(dict.fromkeys(drive_relative_path_entries))

    sys_prefix = sys.prefix
    sys_base_prefix = getattr(sys, "base_prefix", "")
    sys_exec_prefix = sys.exec_prefix
    python_prefix_is_absolute = Path(sys_prefix).is_absolute()
    python_prefix_bare_drive = bool(BARE_DRIVE_PATTERN.match(sys_prefix))
    python_prefix_suspicious = bool(
        python_prefix_bare_drive or DRIVE_RELATIVE_PATTERN.match(sys_prefix)
    )
    repair_venv = ROOT / ".venv-gcn-audit"
    repair_venv_python = repair_venv / "Scripts" / "python.exe"
    drive_relative_prefix_fields = {
        "sys.prefix": sys_prefix if DRIVE_RELATIVE_PATTERN.match(sys_prefix) or BARE_DRIVE_PATTERN.match(sys_prefix) else "",
        "sys.base_prefix": sys_base_prefix
        if DRIVE_RELATIVE_PATTERN.match(sys_base_prefix) or BARE_DRIVE_PATTERN.match(sys_base_prefix)
        else "",
        "sys.exec_prefix": sys_exec_prefix
        if DRIVE_RELATIVE_PATTERN.match(sys_exec_prefix) or BARE_DRIVE_PATTERN.match(sys_exec_prefix)
        else "",
    }
    drive_relative_prefix_fields = {key: value for key, value in drive_relative_prefix_fields.items() if value}

    likely_winerror87_path_cause = bool(
        drive_relative_path_entries
        or any(item in suspicious_path_entries for item in SUSPICIOUS_LITERAL_PATHS)
        or drive_relative_prefix_fields
    )
    if likely_winerror87_path_cause:
        recommended_path_fix = (
            "Inspect drive-relative Python prefix values and PATH / DLL search paths first, because the active Python "
            "environment may be resolving DLL folders as E:bin instead of E:\\bin. Reopen the shell after fixing the "
            "active environment and rerun the import probes."
        )
    elif invalid_path_entries:
        recommended_path_fix = (
            "Clean invalid PATH entries and verify that the active Python / Scripts / CUDA paths do not conflict."
        )
    else:
        recommended_path_fix = (
            "PATH does not show the classic E:bin pattern; verify the active environment and torch installation next."
        )

    return {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "sys_prefix": sys_prefix,
        "sys_base_prefix": sys_base_prefix,
        "sys_exec_prefix": sys_exec_prefix,
        "python_prefix_is_absolute": python_prefix_is_absolute,
        "python_prefix_bare_drive": python_prefix_bare_drive,
        "python_prefix_suspicious": python_prefix_suspicious,
        "repair_environment_detected": sys_prefix.lower().endswith(".venv-gcn-audit"),
        "repair_venv_exists": repair_venv.exists(),
        "repair_venv_python_path": str(repair_venv_python.resolve()) if repair_venv_python.exists() else str(repair_venv_python),
        "repair_venv_gitignored": _git_check_ignore(repair_venv),
        "drive_relative_prefix_fields": drive_relative_prefix_fields,
        "platform": platform.platform(),
        "platform_machine": platform.machine(),
        "os_name": os.name,
        "cwd": str(ROOT),
        "virtual_env_detected": bool(os.environ.get("VIRTUAL_ENV")),
        "virtual_env_path": os.environ.get("VIRTUAL_ENV", ""),
        "conda_env_detected": bool(os.environ.get("CONDA_PREFIX")),
        "conda_prefix": os.environ.get("CONDA_PREFIX", ""),
        "pythonpath": os.environ.get("PYTHONPATH", ""),
        "path_entry_count": len(path_entries),
        "path_first_entries": path_entries[:12],
        "suspicious_path_entries": suspicious_path_entries,
        "invalid_path_entries": invalid_path_entries,
        "drive_relative_path_entries": drive_relative_path_entries,
        "empty_path_entries": empty_path_entries,
        "python_path_entries": python_path_entries,
        "conda_or_venv_script_entries": conda_or_venv_script_entries,
        "cuda_path_entries": cuda_path_entries,
        "torch_lib_related_entries": torch_lib_related_entries,
        "unresolved_envvar_entries": unresolved_envvar_entries,
        "likely_winerror87_path_cause": likely_winerror87_path_cause,
        "recommended_path_fix": recommended_path_fix,
    }


def _probe_pip_and_specs() -> dict[str, Any]:
    package_specs: dict[str, Any] = {}
    for module_name in PROBE_MODULES:
        try:
            spec = importlib.util.find_spec(module_name)
        except Exception as exc:
            package_specs[module_name] = {
                "spec_present": False,
                "spec_error": str(exc),
                "origin": "",
                "submodule_search_locations": [],
            }
            continue
        package_specs[module_name] = {
            "spec_present": spec is not None,
            "origin": "" if spec is None else str(spec.origin),
            "submodule_search_locations": []
            if spec is None or spec.submodule_search_locations is None
            else [str(item) for item in spec.submodule_search_locations],
        }

    pip_probe = {
        "pip_version": _run_command([sys.executable, "-m", "pip", "--version"]),
        "pip_list": _run_command([sys.executable, "-m", "pip", "list"]),
        "pip_show": {name: _run_command([sys.executable, "-m", "pip", "show", name]) for name in PIP_SHOW_PACKAGES},
        "package_specs": package_specs,
    }
    return pip_probe


def _import_module_report(module_name: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "module_name": module_name,
        "import_ok": False,
        "version": None,
        "module_file": None,
        "error": "",
        "traceback_tail": [],
    }
    try:
        module = importlib.import_module(module_name)
        report["import_ok"] = True
        report["version"] = getattr(module, "__version__", None)
        report["module_file"] = getattr(module, "__file__", None)
        if module_name == "torch":
            report["torch_cuda_version"] = getattr(getattr(module, "version", None), "cuda", None)
            report["torch_cuda_available"] = bool(module.cuda.is_available())
            mps_backend = getattr(getattr(module, "backends", None), "mps", None)
            report["torch_mps_available"] = bool(mps_backend.is_available()) if mps_backend is not None else None
            torch_file = getattr(module, "__file__", "")
            if torch_file:
                report["torch_lib_path"] = str(Path(torch_file).resolve().parent / "lib")
        return report
    except Exception as exc:
        report["error"] = str(exc)
        report["traceback_tail"] = traceback.format_exc().splitlines()[-12:]
        if module_name == "torch":
            report["likely_causes"] = [
                "Windows PATH contains drive-relative or invalid DLL search entries.",
                "Torch binary and active Python environment are incompatible.",
                "A conflicting Python / conda / venv environment is shadowing the intended torch install.",
            ]
        elif module_name == "torch_geometric":
            report["likely_causes"] = [
                "torch_geometric is not installed in the active environment.",
                "torch_geometric is installed but depends on a torch environment that cannot import cleanly.",
            ]
        return report


def _probe_imports() -> dict[str, Any]:
    return {
        "torch": _import_module_report("torch"),
        "torch_geometric": _import_module_report("torch_geometric"),
        "command_probes": {name: _run_command(command) for name, command in IMPORT_PROBES.items()},
    }


def _probe_repo_dependency_files() -> dict[str, Any]:
    found: list[str] = []
    combined_text_parts: list[str] = []
    detailed_files: dict[str, Any] = {}
    for rel_path in REPO_DEPENDENCY_FILES:
        path = ROOT / rel_path
        if path.exists():
            found.append(rel_path)
            text = path.read_text(encoding="utf-8", errors="ignore")
            combined_text_parts.append(text)
            detailed_files[rel_path] = {
                "exists": True,
                "mentions_torch": "torch" in text.lower(),
                "mentions_torch_geometric": "torch-geometric" in text.lower() or "torch_geometric" in text.lower(),
                "mentions_pyg_extensions": any(
                    token in text.lower()
                    for token in ["torch-scatter", "torch_sparse", "torch-cluster", "torch-spline-conv"]
                ),
            }
        else:
            detailed_files[rel_path] = {"exists": False}

    combined_text = "\n".join(combined_text_parts).lower()
    return {
        "dependency_files_found": found,
        "repo_dependency_file_details": detailed_files,
        "torch_declared_in_repo": "torch" in combined_text,
        "torch_geometric_declared_in_repo": "torch-geometric" in combined_text or "torch_geometric" in combined_text,
        "pyg_extensions_declared_in_repo": any(
            token in combined_text for token in ["torch-scatter", "torch_sparse", "torch-cluster", "torch-spline-conv"]
        ),
        "dependency_documentation_missing": not found,
    }


def _derive_previous_blocker(execution_summary: dict[str, Any], blocker_report: dict[str, Any]) -> dict[str, Any]:
    previous = {
        "previous_gcn_dependency_status": blocker_report.get(
            "status",
            execution_summary.get("gcn_dependency_status", "blocked_by_missing_gcn_dependency"),
        ),
        "previous_torch_spec_present": blocker_report.get("torch_spec_present"),
        "previous_torch_geometric_spec_present": blocker_report.get("torch_geometric_spec_present"),
        "previous_torch_import_ok": blocker_report.get("torch_import_ok"),
        "previous_torch_import_error": blocker_report.get("torch_import_error", ""),
    }
    return previous


def _recommended_next_step(summary: dict[str, Any]) -> str:
    if summary["torch_import_ok"] is False and summary["likely_winerror87_path_cause"]:
        return "fix Windows PATH / DLL path issue first, then reinstall or verify torch and torch_geometric in the active environment"
    if summary["torch_import_ok"] and not summary["torch_geometric_import_ok"]:
        return "install torch_geometric and matching PyG extension wheels for the detected torch/python platform, then rerun dependency diagnosis"
    if summary["torch_import_ok"] and summary["torch_geometric_import_ok"]:
        return "rerun strict no-leakage GCN usefulness audit in a separate round"
    return "collect missing environment diagnostics before reinstalling dependencies"


def _build_repair_plan(summary: dict[str, Any], env_probe: dict[str, Any], repo_probe: dict[str, Any]) -> dict[str, Any]:
    suspected_primary_blocker = (
        "windows_path_dll_issue"
        if summary["likely_winerror87_path_cause"]
        else ("missing_torch_geometric" if summary["torch_import_ok"] and not summary["torch_geometric_import_ok"] else "active_environment_not_ready")
    )
    cpu_install_example = (
        "python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"
    )
    return {
        "plan_scope": "dependency_diagnosis_only",
        "current_blocker_summary": {
            "torch_spec_present": summary["torch_spec_present"],
            "torch_import_ok": summary["torch_import_ok"],
            "torch_import_error": summary["torch_import_error"],
            "torch_geometric_spec_present": summary["torch_geometric_spec_present"],
            "torch_geometric_import_ok": summary["torch_geometric_import_ok"],
            "suspected_primary_blocker": suspected_primary_blocker,
        },
        "route_a_path_dll_cleanup_first": {
            "when_to_use": [
                "torch import fails",
                "WinError 87 appears",
                "PATH contains E:bin or other drive-relative entries",
            ],
            "steps": [
                "Do not modify repository files for PATH cleanup.",
                "Inspect the active shell PATH and remove suspicious drive-relative entries such as E:bin from the local session first.",
                "Verify that the active Python path, Scripts path, CUDA path, and any torch lib path do not conflict.",
                "Open a fresh shell after cleanup and rerun the import probes.",
                "Do not commit local environment-variable edits.",
            ],
            "detected_suspicious_entries": env_probe["suspicious_path_entries"],
        },
        "route_b_clean_virtualenv": {
            "powershell_example_only_do_not_auto_execute": [
                "python -m venv .venv-gcn-audit",
                ".\\.venv-gcn-audit\\Scripts\\Activate.ps1",
                "python -m pip install --upgrade pip",
                cpu_install_example,
                "python -m pip install torch-geometric",
                "If torch-geometric needs extra compiled extensions, use the official matching wheel index for the detected torch/python platform.",
            ]
        },
        "route_c_conda_optional": {
            "commands": [
                "conda create -n ieee39-gcn-audit python=3.11",
                "conda activate ieee39-gcn-audit",
                "Then choose CPU/GPU torch and matching PyG installation for the detected platform.",
            ]
        },
        "verification_commands": [
            'python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"',
            'python -c "import torch_geometric; print(torch_geometric.__version__)"',
            "python scripts/gcn_search/diagnose_ieee39_gcn_dependency_blocker.py --strict --write-report",
            "python scripts/gcn_search/run_ieee39_strict_no_leakage_gcn_usefulness_audit.py",
        ],
        "verification_note": "The last audit command should be used only after torch and torch_geometric import probes both pass.",
        "prohibited_actions": [
            "Do not commit .venv, site-packages, wheels, DLLs, torch cache, or model files.",
            "Do not modify Simulink files.",
            "Do not bypass the forbidden feature policy.",
            "Do not fake torch / torch_geometric success.",
        ],
        "repo_dependency_context": repo_probe,
        "recommended_next_step": summary["recommended_next_step"],
    }


def _summary_markdown(summary: dict[str, Any]) -> str:
    return f"""# IEEE39 GCN Dependency Blocker Diagnosis

This round is dependency diagnosis only.
It did not train GCN.
It did not rerun the formal GCN usefulness audit.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not save any production model.

## Core Summary

- diagnosis_scope: `{summary["diagnosis_scope"]}`
- previous_gcn_dependency_status: `{summary["previous_gcn_dependency_status"]}`
- torch_spec_present: `{str(summary["torch_spec_present"]).lower()}`
- torch_import_ok: `{str(summary["torch_import_ok"]).lower()}`
- torch_import_error: `{summary["torch_import_error"]}`
- torch_geometric_spec_present: `{str(summary["torch_geometric_spec_present"]).lower()}`
- torch_geometric_import_ok: `{str(summary["torch_geometric_import_ok"]).lower()}`
- suspicious_path_entries: `{json.dumps(summary["suspicious_path_entries"], ensure_ascii=False)}`
- drive_relative_path_entries: `{json.dumps(summary["drive_relative_path_entries"], ensure_ascii=False)}`
- likely_winerror87_path_cause: `{str(summary["likely_winerror87_path_cause"]).lower()}`
- gcn_dependency_blocker_still_present: `{str(summary["gcn_dependency_blocker_still_present"]).lower()}`
- dependency_repair_plan_generated: `{str(summary["dependency_repair_plan_generated"]).lower()}`

## Important Notes

- previous round only completed baseline-only audit
- current GCN conclusion is blocked by the local dependency environment
- current blocker is torch / torch_geometric / Windows DLL PATH related
- WinError 87 and `E:bin` are priority checks
- fix locally first; do not commit large dependency files
- rerun dependency diagnosis after local repair
- rerun the strict audit only after import probes pass
- post-fault dynamic measurements still must not enter GCN inputs
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection

## Recommended Next Step

{summary["recommended_next_step"]}
"""


def run_diagnosis(args: argparse.Namespace) -> dict[str, Any]:
    execution_summary = _read_json(EXECUTION_SUMMARY_PATH)
    if DEPENDENCY_BLOCKER_PATH.exists():
        blocker_report = _read_json(DEPENDENCY_BLOCKER_PATH)
    else:
        blocker_report = {
            "audit_only": True,
            "status": execution_summary.get("gcn_dependency_status", "blocked_by_missing_gcn_dependency"),
            "torch_spec_present": execution_summary.get("torch_spec_present"),
            "torch_geometric_spec_present": execution_summary.get("torch_geometric_spec_present"),
            "torch_import_ok": execution_summary.get("torch_import_ok"),
            "torch_import_error": execution_summary.get("torch_import_error", ""),
        }
        _write_json(DEPENDENCY_BLOCKER_PATH, blocker_report)
    _ = _read_json(DRY_RUN_SUMMARY_PATH)
    _ = _read_json(POLICY_PATH)
    _ = _read_json(SPLIT_MANIFEST_PATH)
    _ = AUDIT_DOC_PATH.read_text(encoding="utf-8", errors="ignore")

    env_probe = _probe_python_environment()
    pip_probe = _probe_pip_and_specs()
    import_probe = _probe_imports()
    repo_probe = _probe_repo_dependency_files()
    previous = _derive_previous_blocker(execution_summary, blocker_report)

    torch_spec = pip_probe["package_specs"]["torch"]
    pyg_spec = pip_probe["package_specs"]["torch_geometric"]
    torch_report = import_probe["torch"]
    pyg_report = import_probe["torch_geometric"]
    summary = {
        "diagnosis_scope": "dependency_diagnosis_only",
        "gcn_training_run": False,
        "formal_gcn_audit_run": False,
        "simulink_run": False,
        "labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_commit": SOURCE_COMMIT,
        **previous,
        "current_python_executable": sys.executable,
        "current_python_version": sys.version,
        "current_platform": platform.platform(),
        "current_sys_prefix": env_probe["sys_prefix"],
        "current_sys_base_prefix": env_probe["sys_base_prefix"],
        "current_sys_exec_prefix": env_probe["sys_exec_prefix"],
        "python_prefix_is_absolute": env_probe["python_prefix_is_absolute"],
        "python_prefix_bare_drive": env_probe["python_prefix_bare_drive"],
        "python_prefix_suspicious": env_probe["python_prefix_suspicious"],
        "repair_environment_detected": env_probe["repair_environment_detected"],
        "repair_venv_exists": env_probe["repair_venv_exists"],
        "repair_venv_python_path": env_probe["repair_venv_python_path"],
        "repair_venv_gitignored": env_probe["repair_venv_gitignored"],
        "virtual_env_detected": env_probe["virtual_env_detected"],
        "conda_env_detected": env_probe["conda_env_detected"],
        "torch_spec_present": torch_spec["spec_present"],
        "torch_import_ok": torch_report["import_ok"],
        "torch_version": torch_report.get("version"),
        "torch_cuda_version": torch_report.get("torch_cuda_version"),
        "torch_cuda_available": torch_report.get("torch_cuda_available"),
        "torch_import_error": torch_report.get("error", ""),
        "torch_geometric_spec_present": pyg_spec["spec_present"],
        "torch_geometric_import_ok": pyg_report["import_ok"],
        "torch_geometric_version": pyg_report.get("version"),
        "torch_geometric_import_error": pyg_report.get("error", ""),
        "pyg_extension_specs": {
            name: pip_probe["package_specs"][name]
            for name in ["torch_scatter", "torch_sparse", "torch_cluster", "torch_spline_conv"]
        },
        "suspicious_path_entries": env_probe["suspicious_path_entries"],
        "invalid_path_entries": env_probe["invalid_path_entries"],
        "drive_relative_path_entries": env_probe["drive_relative_path_entries"],
        "likely_winerror87_path_cause": env_probe["likely_winerror87_path_cause"],
        "gcn_dependency_blocker_still_present": not (torch_report["import_ok"] and pyg_report["import_ok"]),
        "dependency_repair_plan_generated": True,
        "should_train_gcn_now": False,
        "should_rerun_formal_gcn_audit_now": False,
    }
    summary["recommended_next_step"] = _recommended_next_step(summary)

    windows_path_probe = {
        "probe_scope": "windows_path_dll_diagnosis_only",
        "suspicious_path_entries": env_probe["suspicious_path_entries"],
        "invalid_path_entries": env_probe["invalid_path_entries"],
        "drive_relative_path_entries": env_probe["drive_relative_path_entries"],
        "likely_winerror87_path_cause": env_probe["likely_winerror87_path_cause"],
        "recommended_path_fix": env_probe["recommended_path_fix"],
        "python_path_entries": env_probe["python_path_entries"],
        "conda_or_venv_script_entries": env_probe["conda_or_venv_script_entries"],
        "cuda_path_entries": env_probe["cuda_path_entries"],
        "torch_lib_related_entries": env_probe["torch_lib_related_entries"],
        "unresolved_envvar_entries": env_probe["unresolved_envvar_entries"],
        "drive_relative_prefix_fields": env_probe["drive_relative_prefix_fields"],
        "python_prefix_is_absolute": env_probe["python_prefix_is_absolute"],
        "python_prefix_bare_drive": env_probe["python_prefix_bare_drive"],
        "python_prefix_suspicious": env_probe["python_prefix_suspicious"],
        "repair_environment_detected": env_probe["repair_environment_detected"],
        "repair_venv_exists": env_probe["repair_venv_exists"],
        "repair_venv_python_path": env_probe["repair_venv_python_path"],
        "repair_venv_gitignored": env_probe["repair_venv_gitignored"],
    }
    repair_plan = _build_repair_plan(summary, env_probe, repo_probe)

    if args.write_report:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(args.output_dir / "gcn_dependency_diagnosis_summary.json", summary)
        _write_text(args.output_dir / "gcn_dependency_diagnosis_summary.md", _summary_markdown(summary))
        _write_summary_csv(args.output_dir / "gcn_dependency_diagnosis_summary.csv", summary)
        _write_json(args.output_dir / "python_environment_probe.json", env_probe)
        _write_text(args.output_dir / "python_environment_probe.md", _report_md("Python Environment Probe", env_probe))
        _write_json(args.output_dir / "torch_import_probe.json", import_probe["torch"])
        _write_text(args.output_dir / "torch_import_probe.md", _report_md("Torch Import Probe", import_probe["torch"]))
        _write_json(args.output_dir / "torch_geometric_import_probe.json", import_probe["torch_geometric"])
        _write_text(
            args.output_dir / "torch_geometric_import_probe.md",
            _report_md("Torch Geometric Import Probe", import_probe["torch_geometric"]),
        )
        _write_json(args.output_dir / "windows_path_dll_probe.json", windows_path_probe)
        _write_text(args.output_dir / "windows_path_dll_probe.md", _report_md("Windows PATH DLL Probe", windows_path_probe))
        _write_json(args.output_dir / "gcn_dependency_repair_plan.json", repair_plan)
        _write_text(args.output_dir / "gcn_dependency_repair_plan.md", _report_md("GCN Dependency Repair Plan", repair_plan))

    return {
        "summary": summary,
        "env_probe": env_probe,
        "pip_probe": pip_probe,
        "import_probe": import_probe,
        "windows_path_probe": windows_path_probe,
        "repair_plan": repair_plan,
        "repo_probe": repo_probe,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--strict", action="store_true", help="Reserved for deterministic audit-style invocation.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary to stdout.")
    parser.add_argument("--write-report", action="store_true", help="Write diagnosis artifacts to disk.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.write_report:
        args.write_report = True
    payload = run_diagnosis(args)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
