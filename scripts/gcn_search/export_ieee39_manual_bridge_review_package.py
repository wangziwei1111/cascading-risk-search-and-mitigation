from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MATLAB_EXPORTER = ROOT / "matlab/simulink_ieee39/export_ieee39_manual_bridge_review_package.m"
DEFAULT_OUTPUT_DIR = ROOT / "results/gcn_search/ieee39_manual_bridge_review_package"
DEFAULT_LOCAL_BRIDGE = (
    ROOT
    / "results/gcn_search/ieee39_spp001_manual_dynamic_validation/local_bridge_copy/"
    / "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_manual_physical_bridge.slx"
)
DEFAULT_L15_SOURCE = (
    ROOT
    / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/"
    / "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15.slx"
)
DEFAULT_L04_SOURCE = (
    ROOT
    / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/"
    / "IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx"
)

REQUIRED_PACKAGE_FILES = [
    "model_summary.json",
    "block_inventory.csv",
    "physical_port_connectivity.csv",
    "signal_port_connectivity.csv",
    "unconnected_ports.csv",
    "breaker_control_chain.json",
    "breaker_series_and_bypass_check.json",
    "l15_topology_comparison.json",
    "l04_topology_comparison.json",
    "model_configuration.json",
    "static_update_check.json",
    "review_manifest.json",
    "grid_overview.png",
]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _exists(path: Path) -> bool:
    return os.path.exists(_long(path))


def _read_json(path: Path) -> Any:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _tail(text: str, lines: int = 80) -> list[str]:
    return (text or "").splitlines()[-lines:]


def _run_matlab(command: str, timeout_s: int) -> dict[str, Any]:
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    try:
        proc = subprocess.Popen(
            ["matlab", "-batch", command],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, text=True)
            else:
                proc.kill()
            stdout, stderr = proc.communicate(timeout=10)
            return {
                "matlab_invoked": True,
                "matlab_timeout": True,
                "matlab_returncode": proc.returncode,
                "stdout_tail": _tail(stdout),
                "stderr_tail": _tail(stderr),
            }
        return {
            "matlab_invoked": True,
            "matlab_timeout": False,
            "matlab_returncode": proc.returncode,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }
    except FileNotFoundError:
        return {
            "matlab_invoked": False,
            "matlab_timeout": False,
            "matlab_returncode": None,
            "stdout_tail": [],
            "stderr_tail": ["MATLAB executable was not available on PATH"],
        }


def _assert_inputs(args: argparse.Namespace) -> None:
    if args.pair_id != "SPP001":
        raise SystemExit("Only --pair-id SPP001 is allowed.")
    if not args.no_sim:
        raise SystemExit("--no-sim is mandatory and must not be disabled.")
    for label, path in [
        ("local_bridge_path", args.local_bridge_path),
        ("l15_source_lab_path", args.l15_source_lab_path),
        ("l04_source_lab_path", args.l04_source_lab_path),
        ("MATLAB exporter", MATLAB_EXPORTER),
    ]:
        if not _exists(path):
            raise SystemExit(f"Missing {label}: {path}")


def _build_command(args: argparse.Namespace) -> str:
    strict = "true" if args.strict else "false"
    return (
        "addpath('matlab/simulink_ieee39'); "
        "export_ieee39_manual_bridge_review_package("
        f"'{args.local_bridge_path.as_posix()}',"
        f"'{args.l15_source_lab_path.as_posix()}',"
        f"'{args.l04_source_lab_path.as_posix()}',"
        f"'{args.output_dir.as_posix()}',"
        f"'{args.pair_id}',"
        f"'strict',{strict},'no_sim',true);"
    )


def _augment_manifest(args: argparse.Namespace, matlab_status: dict[str, Any], zip_path: Path | None) -> dict[str, Any]:
    manifest_path = args.output_dir / "review_manifest.json"
    manifest = _read_json(manifest_path) if _exists(manifest_path) else {}
    model_summary = _read_json(args.output_dir / "model_summary.json") if _exists(args.output_dir / "model_summary.json") else {}
    present = [name for name in REQUIRED_PACKAGE_FILES if _exists(args.output_dir / name)]
    forbidden_in_dir = []
    for path in args.output_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".slx", ".slxc", ".mat", ".pt", ".pth", ".ckpt", ".dll", ".whl"}:
            forbidden_in_dir.append(str(path.relative_to(args.output_dir)).replace("\\", "/"))
        lowered = str(path).lower().replace("\\", "/")
        if any(token in lowered for token in ["raw_trajector", "full_timeseries", "slprj"]):
            forbidden_in_dir.append(str(path.relative_to(args.output_dir)).replace("\\", "/"))
    manifest.update(
        {
            "manifest_scope": "ieee39_manual_bridge_review_manifest",
            "local_bridge_path": str(args.local_bridge_path.resolve()),
            "l15_source_lab_path": str(args.l15_source_lab_path.resolve()),
            "l04_source_lab_path": str(args.l04_source_lab_path.resolve()),
            "output_dir": str(args.output_dir.resolve()),
            "zip_path": str(zip_path.resolve()) if zip_path else None,
            "required_files_present": present,
            "required_files_missing": [name for name in REQUIRED_PACKAGE_FILES if name not in present],
            "forbidden_files_in_review_package_dir": forbidden_in_dir,
            "sim_called": False,
            "gcn_training_run": False,
            "selected_32_batch_executed": False,
            "full_1056_generation_run": False,
            "labels_exported": False,
            "formal_labels_exported": False,
            "source_slx_modified": False,
            "local_bridge_slx_included": False,
            "block_existence_only_is_sufficient": False,
            "no_leakage_policy_passed": model_summary.get("no_leakage_policy_passed", True),
            "physical_bridge_valid": model_summary.get("physical_bridge_valid", False),
            "matlab_status": matlab_status,
        }
    )
    _write_json(manifest_path, manifest)
    return manifest


def _zip_package(output_dir: Path) -> Path:
    zip_path = output_dir / "spp001_manual_bridge_review_package.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in REQUIRED_PACKAGE_FILES:
            path = output_dir / name
            if path.exists():
                archive.write(path, arcname=name)
    return zip_path


def export_package(args: argparse.Namespace) -> Path:
    _assert_inputs(args)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    status = _run_matlab(_build_command(args), args.matlab_timeout_seconds)
    if status["matlab_timeout"]:
        _write_json(args.output_dir / "matlab_invocation_status.json", status)
        raise SystemExit("MATLAB review exporter timed out; no sim() was requested.")
    if status["matlab_returncode"] not in (0, None):
        _write_json(args.output_dir / "matlab_invocation_status.json", status)
        raise SystemExit("MATLAB review exporter failed; see matlab_invocation_status.json.")
    _write_json(args.output_dir / "matlab_invocation_status.json", status)
    zip_path = _zip_package(args.output_dir) if args.zip_review_package else args.output_dir / "spp001_manual_bridge_review_package.zip"
    _augment_manifest(args, status, zip_path if args.zip_review_package else None)
    if args.zip_review_package:
        zip_path = _zip_package(args.output_dir)
        _augment_manifest(args, status, zip_path)
    print(f"REVIEW_PACKAGE_READY={zip_path.resolve()}")
    return zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export IEEE39 manual bridge static review package.")
    parser.add_argument("--local-bridge-path", type=Path, default=DEFAULT_LOCAL_BRIDGE)
    parser.add_argument("--l15-source-lab-path", type=Path, default=DEFAULT_L15_SOURCE)
    parser.add_argument("--l04-source-lab-path", type=Path, default=DEFAULT_L04_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pair-id", default="SPP001")
    parser.add_argument("--strict", action="store_true", default=True)
    parser.add_argument("--zip-review-package", action="store_true")
    parser.add_argument("--no-sim", action="store_true", default=True)
    parser.add_argument("--matlab-timeout-seconds", type=int, default=240)
    return parser.parse_args()


def main() -> None:
    export_package(parse_args())


if __name__ == "__main__":
    main()
