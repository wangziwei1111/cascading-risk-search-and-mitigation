from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose the local Python/PyTorch environment for IEEE118 GCN runs.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval",
    )
    return parser.parse_args()


def diagnose_torch_environment() -> dict[str, Any]:
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    result: dict[str, Any] = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "sys_exec_prefix": sys.exec_prefix,
        "sys_base_exec_prefix": getattr(sys, "base_exec_prefix", ""),
        "sys_path": list(sys.path),
        "path_contains_literal_E_colon_bin": any(part == "E:bin" for part in path_parts),
        "path_entries_containing_E_drive": [part for part in path_parts if "E:" in part or part == "E"],
        "conda_prefix": os.environ.get("CONDA_PREFIX"),
        "virtual_env": os.environ.get("VIRTUAL_ENV"),
        "torch_import_success": False,
        "torch_version": None,
        "torch_cuda_available": None,
        "torch_file": None,
        "torch_import_error": None,
    }
    try:
        import torch

        result.update(
            {
                "torch_import_success": True,
                "torch_version": getattr(torch, "__version__", None),
                "torch_cuda_available": bool(torch.cuda.is_available()),
                "torch_file": getattr(torch, "__file__", None),
            }
        )
    except Exception as exc:  # pragma: no cover - environment-dependent.
        result["torch_import_error"] = repr(exc)
    return result


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    diagnosis = diagnose_torch_environment()
    output = args.output_dir / "torch_environment_diagnosis.json"
    output.write_text(json.dumps(diagnosis, indent=2), encoding="utf-8")
    print(json.dumps(diagnosis, indent=2))


if __name__ == "__main__":
    main()
