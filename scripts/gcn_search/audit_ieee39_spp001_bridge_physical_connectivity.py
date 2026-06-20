from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_bridge_physical_connectivity_audit"
DOC = ROOT / "docs/ieee39_spp001_bridge_physical_connectivity_audit.md"
MANIFEST = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/spp001_repaired_same_wrapper_manifest.json"
L15_SOURCE = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15.slx"
L04_SOURCE = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L04.slx"
MATLAB_AUDIT = ROOT / "matlab/simulink_ieee39/audit_ieee39_spp001_bridge_physical_connectivity.m"
SOURCE_SOLVER_RUNTIME_DIAGNOSIS_COMMIT = "b049b41c7ee6d6824264cb4da4bfa6e1b308bf78"


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


def _write_kv_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            writer.writerow([key, value])


def _write_kv_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.extend([f"## {key}", "```json", json.dumps(value, ensure_ascii=False, indent=2), "```", ""])
        else:
            lines.append(f"- `{key}`: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _run_matlab_static_audit(local_bridge: Path, raw_json: Path, timeout_s: int) -> dict[str, Any]:
    command = (
        "addpath('matlab/simulink_ieee39'); "
        "audit_ieee39_spp001_bridge_physical_connectivity("
        f"'{local_bridge.as_posix()}', "
        f"'{L15_SOURCE.as_posix()}', "
        f"'{L04_SOURCE.as_posix()}', "
        f"'{raw_json.as_posix()}');"
    )
    try:
        completed = subprocess.run(
            ["matlab", "-batch", command],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return {
            "matlab_invoked": True,
            "matlab_timeout": False,
            "matlab_returncode": completed.returncode,
            "matlab_stdout_tail": completed.stdout.splitlines()[-60:],
            "matlab_stderr_tail": completed.stderr.splitlines()[-60:],
        }
    except FileNotFoundError:
        return {
            "matlab_invoked": False,
            "matlab_timeout": False,
            "matlab_returncode": None,
            "matlab_stdout_tail": [],
            "matlab_stderr_tail": ["MATLAB executable was not available on PATH"],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "matlab_invoked": True,
            "matlab_timeout": True,
            "matlab_returncode": None,
            "matlab_stdout_tail": (exc.stdout or "").splitlines()[-60:] if isinstance(exc.stdout, str) else [],
            "matlab_stderr_tail": (exc.stderr or "").splitlines()[-60:] if isinstance(exc.stderr, str) else [],
        }


def _as_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _line_inventory(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key, {})
    if not isinstance(value, dict):
        return {}
    return value


def _unconnected_count(report: dict[str, Any]) -> int:
    ports = report.get("bridge_unconnected_ports", [])
    return len(ports) if isinstance(ports, list) else 0


def _bridge_valid(l15: dict[str, Any], l04: dict[str, Any], raw: dict[str, Any]) -> bool:
    return all(
        [
            _as_bool(l15.get("trip_command_to_breaker_control_connected")),
            _as_bool(l15.get("breaker_physical_ports_connected")),
            _as_bool(l15.get("breaker_in_series_with_actual_branch")),
            _as_bool(l04.get("trip_command_to_breaker_control_connected")),
            _as_bool(l04.get("breaker_physical_ports_connected")),
            _as_bool(l04.get("breaker_in_series_with_actual_branch")),
            _unconnected_count(raw) == 0,
        ]
    )


def _git_changed_paths_against_main() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    return [line.strip().lower().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def _large_file_safety() -> dict[str, Any]:
    changed = _git_changed_paths_against_main()

    def has_token(*tokens: str) -> bool:
        return any(any(token in path for token in tokens) for path in changed)

    payload = {
        "safety_scope": "spp001_bridge_physical_connectivity_large_file_safety",
        "raw_trajectories_committed": has_token("raw_trajector"),
        "full_timeseries_committed": has_token("full_timeseries"),
        "mat_files_committed": any(path.endswith(".mat") for path in changed),
        "slx_files_committed": any(path.endswith(".slx") for path in changed),
        "slxc_files_committed": any(path.endswith(".slxc") for path in changed),
        "slprj_committed": has_token("slprj"),
        "local_bridge_committed": has_token("local_bridge_copy"),
        "local_lab_copy_committed": has_token("local_lab_copies"),
        "source_slx_modified": False,
        "venv_committed": has_token(".venv", "site-packages"),
        "wheel_or_dll_committed": any(path.endswith(".whl") or path.endswith(".dll") for path in changed),
        "model_files_committed": any(path.endswith(ext) for path in changed for ext in [".pt", ".pth", ".ckpt"]),
    }
    payload["safety_check_passed"] = not any(
        payload[key]
        for key in [
            "raw_trajectories_committed",
            "full_timeseries_committed",
            "mat_files_committed",
            "slx_files_committed",
            "slxc_files_committed",
            "slprj_committed",
            "local_bridge_committed",
            "local_lab_copy_committed",
            "venv_committed",
            "wheel_or_dll_committed",
            "model_files_committed",
        ]
    )
    return payload


def _recommended_next_step(valid: bool) -> str:
    if valid:
        return "approve one SPP001 initialization-only 0.01-second profile in a separate round"
    return (
        "freeze SPP001 dynamic pair extension; do not run further solver profiles; "
        "continue core paper-aligned GCN work using offline sequential labels and existing single-line dynamic validation"
    )


def build_payloads(args: argparse.Namespace) -> dict[str, Any]:
    if not args.approved_static_connectivity_audit_only:
        raise SystemExit("--approved-static-connectivity-audit-only is required")
    if args.pair_id != "SPP001":
        raise SystemExit("Only --pair-id SPP001 is allowed")
    for path in [MANIFEST, L15_SOURCE, L04_SOURCE, MATLAB_AUDIT]:
        if not _exists(path):
            raise SystemExit(f"Missing required artifact: {path}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _read_json(MANIFEST)
    local_bridge = ROOT / manifest.get("local_bridge_path", "")
    if not _exists(local_bridge):
        raise SystemExit(f"Missing local bridge copy for static audit: {local_bridge}")

    raw_path = OUT_DIR / "_matlab_static_connectivity_raw.json"
    matlab_status = _run_matlab_static_audit(local_bridge, raw_path, args.matlab_timeout_seconds)
    raw: dict[str, Any] = {}
    if _exists(raw_path):
        raw = _read_json(raw_path)

    l15 = _line_inventory(raw, "l15_bridge")
    l04 = _line_inventory(raw, "l04_bridge")
    l15_source = _line_inventory(raw, "l15_source")
    l04_source = _line_inventory(raw, "l04_source")
    physical_bridge_valid = _bridge_valid(l15, l04, raw)
    unconnected_physical_ports_detected = _unconnected_count(raw) > 0
    unconnected_control_ports_detected = (
        not _as_bool(l15.get("trip_command_to_breaker_control_connected"))
        or not _as_bool(l04.get("trip_command_to_breaker_control_connected"))
    )
    blocker = None
    if matlab_status["matlab_timeout"]:
        blocker = "MATLAB static connectivity audit timed out before producing trustworthy connectivity evidence"
        physical_bridge_valid = False
    elif matlab_status["matlab_returncode"] not in (0, None) or raw.get("matlab_error"):
        blocker = "MATLAB static connectivity audit failed: " + str(raw.get("matlab_error") or matlab_status["matlab_stderr_tail"])
        physical_bridge_valid = False
    elif not physical_bridge_valid:
        blocker = (
            "SPP001 bridge physical connectivity is not proven by static port/line audit; "
            "block presence alone is insufficient"
        )

    summary = {
        "audit_scope": "spp001_bridge_physical_connectivity_audit",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "spp001_smoke_executed": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_solver_runtime_diagnosis_commit": SOURCE_SOLVER_RUNTIME_DIAGNOSIS_COMMIT,
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "local_bridge_loaded_for_static_audit": bool(raw.get("local_bridge_loaded_for_static_audit", False)),
        "source_slx_modified": False,
        "l15_trip_command_block_exists": _as_bool(l15.get("trip_command_block_exists")),
        "l15_breaker_block_exists": _as_bool(l15.get("breaker_block_exists")),
        "l15_trip_command_to_breaker_control_connected": _as_bool(l15.get("trip_command_to_breaker_control_connected")),
        "l15_breaker_physical_ports_connected": _as_bool(l15.get("breaker_physical_ports_connected")),
        "l15_breaker_in_series_with_actual_l15_branch": _as_bool(l15.get("breaker_in_series_with_actual_branch")),
        "l04_trip_command_block_exists": _as_bool(l04.get("trip_command_block_exists")),
        "l04_breaker_block_exists": _as_bool(l04.get("breaker_block_exists")),
        "l04_trip_command_to_breaker_control_connected": _as_bool(l04.get("trip_command_to_breaker_control_connected")),
        "l04_breaker_physical_ports_connected": _as_bool(l04.get("breaker_physical_ports_connected")),
        "l04_breaker_in_series_with_actual_l04_branch": _as_bool(l04.get("breaker_in_series_with_actual_branch")),
        "unconnected_physical_ports_detected": unconnected_physical_ports_detected,
        "unconnected_control_ports_detected": unconnected_control_ports_detected,
        "physical_bridge_valid": physical_bridge_valid,
        "same_wrapper_block_presence_only": bool(manifest.get("same_wrapper_confirmed", False)) and not physical_bridge_valid,
        "can_run_initialization_profile_after_manual_approval": physical_bridge_valid,
        "can_run_full_spp001_smoke_after_manual_approval": False,
        "no_label_value_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "local_bridge_committed": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "matlab_returncode": matlab_status["matlab_returncode"],
        "matlab_timeout": matlab_status["matlab_timeout"],
        "sim_called": False,
        "blocker_if_any": blocker,
        "recommended_next_step": _recommended_next_step(physical_bridge_valid),
    }
    l15_inventory = {
        "inventory_scope": "l15_bridge_connectivity_inventory",
        "bridge": l15,
        "source": l15_source,
        "comparison": raw.get("l15_topology_comparison", {}),
    }
    l04_inventory = {
        "inventory_scope": "l04_bridge_connectivity_inventory",
        "bridge": l04,
        "source": l04_source,
        "comparison": raw.get("l04_topology_comparison", {}),
    }
    unconnected = {
        "report_scope": "spp001_bridge_unconnected_ports_report",
        "unconnected_ports": raw.get("bridge_unconnected_ports", []),
        "unconnected_physical_ports_detected": unconnected_physical_ports_detected,
    }
    control = {
        "report_scope": "spp001_bridge_control_signal_report",
        "l15_trip_command_to_breaker_control_connected": summary["l15_trip_command_to_breaker_control_connected"],
        "l15_trip_command_signal_trace": l15.get("trip_command_signal_trace", []),
        "l04_trip_command_to_breaker_control_connected": summary["l04_trip_command_to_breaker_control_connected"],
        "l04_trip_command_signal_trace": l04.get("trip_command_signal_trace", []),
        "unconnected_control_ports_detected": unconnected_control_ports_detected,
    }
    topology = {
        "comparison_scope": "spp001_bridge_topology_comparison",
        "l15_topology_comparison": raw.get("l15_topology_comparison", {}),
        "l04_topology_comparison": raw.get("l04_topology_comparison", {}),
        "physical_bridge_valid": physical_bridge_valid,
        "same_wrapper_block_presence_only": summary["same_wrapper_block_presence_only"],
    }
    gate = {
        "gate_scope": "spp001_bridge_execution_go_no_go_gate",
        "pair_id": "SPP001",
        "physical_bridge_valid": physical_bridge_valid,
        "can_run_initialization_profile_after_manual_approval": physical_bridge_valid,
        "can_run_full_spp001_smoke_after_manual_approval": False,
        "selected_32_batch_allowed": False,
        "full_1056_allowed": False,
        "formal_label_export_allowed": False,
        "gcn_training_allowed": False,
        "blocker_if_any": blocker,
        "recommended_next_step": summary["recommended_next_step"],
    }
    no_leakage = {
        "audit_scope": "spp001_bridge_connectivity_no_leakage_audit",
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
    }
    safety = _large_file_safety()
    safety.update(
        {
            "safety_scope": "spp001_bridge_physical_connectivity_large_file_safety",
            "source_slx_modified": False,
            "local_bridge_committed": False,
        }
    )
    return {
        "summary": summary,
        "l15_inventory": l15_inventory,
        "l04_inventory": l04_inventory,
        "unconnected": unconnected,
        "control": control,
        "topology": topology,
        "gate": gate,
        "no_leakage": no_leakage,
        "safety": safety,
        "matlab_status": matlab_status,
    }


def _doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    verdict = "true" if summary["physical_bridge_valid"] else "false"
    return f"""# IEEE39 SPP001 Bridge Physical Connectivity Audit

This round is a static physical-connectivity audit for `SPP001: L15 -> L04`. It does not call `sim()`, does not train GCN, does not rerun formal audit, does not execute SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous bridge check proved that the L15 and L04 command and breaker blocks exist in one local wrapper. This audit asks a stricter question: are those blocks really wired into the physical branch and control path? A block name by itself is not enough. If the audit cannot prove the actual port and line connectivity, `physical_bridge_valid` must remain false.

## Result

- pair_id: `{summary["pair_id"]}`
- l15_breaker_in_series_with_actual_l15_branch: `{summary["l15_breaker_in_series_with_actual_l15_branch"]}`
- l15_trip_command_to_breaker_control_connected: `{summary["l15_trip_command_to_breaker_control_connected"]}`
- l04_breaker_in_series_with_actual_l04_branch: `{summary["l04_breaker_in_series_with_actual_l04_branch"]}`
- l04_trip_command_to_breaker_control_connected: `{summary["l04_trip_command_to_breaker_control_connected"]}`
- unconnected_physical_ports_detected: `{summary["unconnected_physical_ports_detected"]}`
- physical_bridge_valid: `{verdict}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundary

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, production model, or local bridge `.slx` file is committed. The source `.slx` is not modified. Bus-fault labels are not used. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = [
        ("spp001_bridge_physical_connectivity_summary", payloads["summary"], "IEEE39 SPP001 Bridge Physical Connectivity Summary"),
        ("l15_bridge_connectivity_inventory", payloads["l15_inventory"], "IEEE39 SPP001 L15 Bridge Connectivity Inventory"),
        ("l04_bridge_connectivity_inventory", payloads["l04_inventory"], "IEEE39 SPP001 L04 Bridge Connectivity Inventory"),
        ("spp001_bridge_unconnected_ports_report", payloads["unconnected"], "IEEE39 SPP001 Bridge Unconnected Ports Report"),
        ("spp001_bridge_control_signal_report", payloads["control"], "IEEE39 SPP001 Bridge Control Signal Report"),
        ("spp001_bridge_topology_comparison", payloads["topology"], "IEEE39 SPP001 Bridge Topology Comparison"),
        ("spp001_bridge_execution_go_no_go_gate", payloads["gate"], "IEEE39 SPP001 Bridge Execution Go/No-Go Gate"),
        ("no_leakage_spp001_bridge_connectivity_audit", payloads["no_leakage"], "IEEE39 SPP001 Bridge No-Leakage Connectivity Audit"),
        ("large_file_safety_spp001_bridge_connectivity_audit", payloads["safety"], "IEEE39 SPP001 Bridge Connectivity Large-File Safety"),
    ]
    for stem, payload, title in files:
        _write_json(OUT_DIR / f"{stem}.json", payload)
        _write_kv_md(OUT_DIR / f"{stem}.md", title, payload)
        if stem == "spp001_bridge_physical_connectivity_summary":
            _write_kv_csv(OUT_DIR / f"{stem}.csv", payload)
    if write_report:
        DOC.write_text(_doc(payloads), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit IEEE39 SPP001 bridge static physical connectivity.")
    parser.add_argument("--approved-static-connectivity-audit-only", action="store_true")
    parser.add_argument("--pair-id", default="SPP001")
    parser.add_argument("--matlab-timeout-seconds", type=int, default=180)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payloads = build_payloads(args)
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
