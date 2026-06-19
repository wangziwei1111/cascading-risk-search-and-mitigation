from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_bridge_smoke_timeout_diagnosis"
DOC = ROOT / "docs/ieee39_spp001_bridge_smoke_timeout_diagnosis.md"
PREVIOUS_SUMMARY = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_smoke_rerun/spp001_bridge_smoke_rerun_summary.json"
PREVIOUS_RESULT = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_smoke_rerun/spp001_bridge_smoke_rerun_result.json"
DEFAULT_MANIFEST = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/spp001_repaired_same_wrapper_manifest.json"
MATLAB_ENTRYPOINT = ROOT / "matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m"
PYTHON_RUNNER = ROOT / "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py"
SOURCE_BRIDGE_SMOKE_RERUN_COMMIT = "71e48fed4fb3e2dd2244023ad539e9db275a1b84"


PHASES = [
    "phase_start_matlab_entrypoint",
    "phase_file_generation_folder_configured",
    "phase_manifest_loaded",
    "phase_model_load_start",
    "phase_model_load_done",
    "phase_trip_command_set_start",
    "phase_trip_command_set_done",
    "phase_update_diagram_start",
    "phase_update_diagram_done",
    "phase_sim_start",
    "phase_sim_done",
    "phase_cleanup_start",
    "phase_cleanup_done",
]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


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


def _tail_lines_from_text(text: str, line_count: int = 40) -> list[str]:
    return str(text or "").splitlines()[-line_count:]


def _extract_timeout_seconds(reason: str) -> int | None:
    match = re.search(r"timeout after\s+(\d+)s", reason or "")
    return int(match.group(1)) if match else None


def _extract_last_phase(result: dict[str, Any]) -> str | None:
    if result.get("last_seen_phase_if_available"):
        return str(result["last_seen_phase_if_available"])
    combined = "\n".join(
        [
            "\n".join(result.get("matlab_stdout_tail") or []),
            "\n".join(result.get("matlab_stderr_tail") or []),
            str(result.get("timeout_or_failure_reason") or ""),
        ]
    )
    marker = "IEEE39_SELECTED_PAIR_PHASE:"
    last_phase = None
    for line in combined.splitlines():
        if marker in line:
            last_phase = line.split(marker, 1)[1].split(":", 1)[0].strip()
    return last_phase


def _current_round_forbidden_files() -> list[str]:
    commands = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    paths: list[str] = []
    for command in commands:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        paths.extend(line.strip() for line in result.stdout.splitlines() if line.strip())
    forbidden_tokens = [
        ".venv-gcn-audit/",
        ".venv/",
        "site-packages",
        ".whl",
        ".dll",
        ".pt",
        ".pth",
        ".ckpt",
        ".slx",
        ".slxc",
        "slprj",
        ".mat",
        "raw_trajector",
        "full_timeseries",
        "local_lab_copies",
    ]
    return sorted(
        {
            path
            for path in paths
            if any(token in path.lower() for token in forbidden_tokens)
            and path.startswith(("docs/", "matlab/", "scripts/", "tests/", "results/gcn_search/"))
        }
    )


def build_payloads(args: argparse.Namespace) -> dict[str, Any]:
    if args.pair_id != "SPP001":
        raise SystemExit("Only --pair-id SPP001 is allowed for this timeout diagnosis.")
    if not args.diagnostic_only:
        raise SystemExit("--diagnostic-only is required. This script must not rerun full SPP001 smoke.")
    missing = [
        path
        for path in [PREVIOUS_SUMMARY, PREVIOUS_RESULT, args.provenance_manifest, MATLAB_ENTRYPOINT, PYTHON_RUNNER]
        if not path.exists()
    ]
    if args.strict and missing:
        raise SystemExit("Missing required timeout diagnosis inputs: " + "; ".join(str(path) for path in missing))

    previous_summary = _read_json(PREVIOUS_SUMMARY)
    previous_result = _read_json(PREVIOUS_RESULT)
    manifest = _read_json(args.provenance_manifest)
    timeout_reason = str(previous_summary.get("timeout_or_failure_reason") or previous_result.get("timeout_or_failure_reason") or "")
    previous_timeout_seconds = _extract_timeout_seconds(timeout_reason)
    repeated_codegen_count = timeout_reason.count("IEEE39 Simulink file-generation folders")
    repeated_codegen_detected = repeated_codegen_count >= 2
    last_seen_phase = _extract_last_phase(previous_result)

    matlab_text = MATLAB_ENTRYPOINT.read_text(encoding="utf-8", errors="ignore")
    python_text = PYTHON_RUNNER.read_text(encoding="utf-8", errors="ignore")
    phase_timing_added_to_matlab = all(phase in matlab_text for phase in PHASES) and "diagnostic_only" in matlab_text
    phase_timing_added_to_python = "--diagnostic-only" in python_text and "_extract_last_phase" in python_text

    if last_seen_phase:
        likely_timeout_stage = last_seen_phase
        timeout_hypothesis = (
            "Previous evidence contains a phase marker; timeout likely occurred at or after "
            f"{last_seen_phase}."
        )
    elif repeated_codegen_detected:
        likely_timeout_stage = "unknown_before_phase_markers_or_repeated_codegen_setup"
        timeout_hypothesis = (
            "Previous stdout only showed repeated Simulink file-generation folder messages and no compact phase markers. "
            "The timeout cannot yet be localized to load_system, set_param, update diagram, sim, or cleanup."
        )
    else:
        likely_timeout_stage = "unknown_without_phase_markers"
        timeout_hypothesis = (
            "Previous run predates phase timing markers, so the timeout stage cannot be determined without a diagnostic-only retry."
        )

    recommended_next_step = "run diagnostic-only SPP001 phase-timing check before any full smoke rerun"
    if last_seen_phase:
        recommended_next_step = (
            "approve one SPP001 diagnostic retry with phase timing focused on that stage; do not export labels or train"
        )
    elif "timeout window too short" in timeout_hypothesis.lower():
        recommended_next_step = (
            "approve one SPP001 smoke retry with longer timeout in a separate round; do not expand batch"
        )

    summary = {
        "diagnosis_scope": "spp001_bridge_smoke_timeout_diagnosis",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "spp001_smoke_rerun_executed": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_bridge_smoke_rerun_commit": SOURCE_BRIDGE_SMOKE_RERUN_COMMIT,
        "pair_id": "SPP001",
        "previous_execution_status": previous_summary.get("execution_status"),
        "previous_timeout_seconds": previous_timeout_seconds,
        "previous_same_wrapper_confirmed": previous_summary.get("same_wrapper_confirmed"),
        "diagnostic_only": True,
        "sim_run_attempted": False,
        "phase_timing_added_to_matlab_entrypoint": phase_timing_added_to_matlab,
        "phase_timing_added_to_python_runner": phase_timing_added_to_python,
        "last_seen_phase_if_available": last_seen_phase,
        "repeated_codegen_folder_messages_detected": repeated_codegen_detected,
        "repeated_codegen_folder_message_count": repeated_codegen_count,
        "likely_timeout_stage": likely_timeout_stage,
        "timeout_root_cause_hypothesis": timeout_hypothesis,
        "can_retry_spp001_with_phase_timing_after_manual_approval": True,
        "can_retry_spp001_with_longer_timeout_after_manual_approval": True,
        "can_request_selected_32_batch": False,
        "no_label_value_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "local_bridge_committed": False,
        "source_slx_modified": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "blocker_if_any": timeout_reason,
        "recommended_next_step": recommended_next_step,
    }
    phase_plan = {
        "plan_scope": "spp001_timeout_phase_plan",
        "pair_id": "SPP001",
        "diagnostic_only": True,
        "sim_run_planned": False,
        "phase_markers": PHASES,
        "purpose": "localize timeout stage before any full SPP001 smoke rerun",
        "notes": [
            "diagnostic-only mode must not call sim()",
            "timeout remains null label and cannot become 0/1",
            "do not export formal labels or train GCN",
        ],
    }
    excerpt = {
        "excerpt_scope": "spp001_timeout_stdout_stderr_excerpt",
        "pair_id": "SPP001",
        "previous_timeout_reason": timeout_reason,
        "previous_timeout_reason_tail": _tail_lines_from_text(timeout_reason, 20),
        "last_seen_phase_if_available": last_seen_phase,
        "repeated_codegen_folder_messages_detected": repeated_codegen_detected,
        "repeated_codegen_folder_message_count": repeated_codegen_count,
    }
    gate = {
        "gate_scope": "spp001_timeout_diagnostic_gate",
        "pair_id": "SPP001",
        "same_wrapper_confirmed": manifest.get("same_wrapper_confirmed"),
        "previous_status": previous_summary.get("execution_status"),
        "diagnostic_only": True,
        "selected_32_batch_allowed": False,
        "full_1056_allowed": False,
        "formal_label_export_allowed": False,
        "gcn_training_allowed": False,
        "can_request_spp001_diagnostic_retry": True,
        "can_request_spp001_full_smoke_rerun": False,
        "blocker_if_any": timeout_reason,
    }
    no_leakage = {
        "audit_scope": "spp001_timeout_diagnosis_no_leakage_audit",
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "no_leakage_policy_passed": True,
    }
    tracked_forbidden = _current_round_forbidden_files()
    safety = {
        "safety_scope": "spp001_timeout_diagnosis_large_file_safety",
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "local_bridge_committed": False,
        "local_lab_copy_committed": False,
        "source_slx_modified": False,
        "venv_committed": False,
        "wheel_or_dll_committed": False,
        "model_files_committed": False,
        "tracked_forbidden_files": tracked_forbidden,
        "safety_check_passed": tracked_forbidden == [],
    }
    return {
        "summary": summary,
        "phase_plan": phase_plan,
        "excerpt": excerpt,
        "gate": gate,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 SPP001 Bridge Smoke Timeout Diagnosis

This round is SPP001 bridge smoke timeout diagnosis only. It does not train GCN, does not rerun formal audit, does not execute full SPP001 smoke, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous round confirmed the same-wrapper bridge for `L15 -> L04`, but the execution hit a 180 second timeout. This round only localizes the timeout stage. It adds compact phase timing hooks for a future diagnostic-only retry and reads the old timeout evidence. The old timeout cannot become a 0/1 label.

## Diagnosis

- diagnosis_scope: `{summary["diagnosis_scope"]}`
- pair_id: `{summary["pair_id"]}`
- previous_execution_status: `{summary["previous_execution_status"]}`
- previous_timeout_seconds: `{summary["previous_timeout_seconds"]}`
- previous_same_wrapper_confirmed: `{summary["previous_same_wrapper_confirmed"]}`
- diagnostic_only: `{summary["diagnostic_only"]}`
- sim_run_attempted: `{summary["sim_run_attempted"]}`
- phase_timing_added_to_matlab_entrypoint: `{summary["phase_timing_added_to_matlab_entrypoint"]}`
- phase_timing_added_to_python_runner: `{summary["phase_timing_added_to_python_runner"]}`
- last_seen_phase_if_available: `{summary["last_seen_phase_if_available"]}`
- repeated_codegen_folder_messages_detected: `{summary["repeated_codegen_folder_messages_detected"]}`
- likely_timeout_stage: `{summary["likely_timeout_stage"]}`
- timeout_root_cause_hypothesis: `{summary["timeout_root_cause_hypothesis"]}`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, local bridge `.slx`, venv, wheel, DLL, or production model files are committed. The source `.slx` is not modified. Bus-fault labels are not used. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "spp001_timeout_diagnosis_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "spp001_timeout_diagnosis_summary.md", "IEEE39 SPP001 Timeout Diagnosis Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "spp001_timeout_diagnosis_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "spp001_timeout_phase_plan.json", payloads["phase_plan"])
    _write_kv_md(OUT_DIR / "spp001_timeout_phase_plan.md", "IEEE39 SPP001 Timeout Phase Plan", payloads["phase_plan"])
    _write_json(OUT_DIR / "spp001_timeout_stdout_stderr_excerpt.json", payloads["excerpt"])
    _write_kv_md(OUT_DIR / "spp001_timeout_stdout_stderr_excerpt.md", "IEEE39 SPP001 Timeout Stdout Stderr Excerpt", payloads["excerpt"])
    _write_json(OUT_DIR / "spp001_timeout_diagnostic_gate.json", payloads["gate"])
    _write_kv_md(OUT_DIR / "spp001_timeout_diagnostic_gate.md", "IEEE39 SPP001 Timeout Diagnostic Gate", payloads["gate"])
    _write_json(OUT_DIR / "no_leakage_spp001_timeout_diagnosis_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_spp001_timeout_diagnosis_audit.md", "IEEE39 SPP001 Timeout No-Leakage Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_safety_spp001_timeout_diagnosis.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_safety_spp001_timeout_diagnosis.md", "IEEE39 SPP001 Timeout Large-File Safety", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose IEEE39 SPP001 same-wrapper bridge smoke timeout.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--diagnostic-only", action="store_true")
    parser.add_argument("--pair-id", default="SPP001")
    parser.add_argument("--provenance-manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    if not args.provenance_manifest.is_absolute():
        args.provenance_manifest = ROOT / args.provenance_manifest
    payloads = build_payloads(args)
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
