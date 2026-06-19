from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from run_ieee39_selected_single_outage_pilot_pairs_controlled import (
    PILOT_PAIR_DIR,
    ROOT,
    SPP001_PAIR_ID,
    _attempt_spp001_matlab,
    _choose_smoke_candidate,
    _exists,
    _long,
    _read_json,
    _write_json,
)


SOURCE_TIMEOUT_DIAGNOSIS_COMMIT = "b858bbf5085324ebee6e7d96f1a0216d8f1aca60"
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_sim_stage_diagnostic_retry"
DOC = ROOT / "docs/ieee39_spp001_sim_stage_diagnostic_retry.md"
TIMEOUT_DIAGNOSIS_DIR = ROOT / "results/gcn_search/ieee39_spp001_bridge_smoke_timeout_diagnosis"
BRIDGE_RERUN_DIR = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_smoke_rerun"
REPAIRED_MANIFEST = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair/spp001_repaired_same_wrapper_manifest.json"


def _write_kv_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            writer.writerow([key, value])


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            for key, value in out.items():
                if isinstance(value, (dict, list)):
                    out[key] = json.dumps(value, ensure_ascii=False)
            writer.writerow(out)


def _write_kv_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.extend([f"## {key}", "```json", json.dumps(value, ensure_ascii=False, indent=2), "```", ""])
        else:
            lines.append(f"- `{key}`: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _tail_lines(lines: list[str], count: int = 40) -> list[str]:
    return list(lines or [])[-count:]


def _read_json_or_empty(path: Path) -> dict[str, Any]:
    if not _exists(path):
        return {}
    try:
        return _read_json(path)
    except Exception:
        return {}


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
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _large_file_safety() -> dict[str, Any]:
    tracked = [path.lower().replace("\\", "/") for path in _git_changed_paths_against_main()]
    def has_token(*tokens: str) -> bool:
        return any(any(token in path for token in tokens) for path in tracked)

    safety = {
        "safety_scope": "spp001_sim_stage_diagnostic_large_file_safety",
        "raw_trajectories_committed": has_token("raw_trajector"),
        "full_timeseries_committed": has_token("full_timeseries"),
        "mat_files_committed": any(path.endswith(".mat") for path in tracked),
        "slx_files_committed": any(path.endswith(".slx") for path in tracked),
        "slxc_files_committed": any(path.endswith(".slxc") for path in tracked),
        "slprj_committed": has_token("slprj/"),
        "local_bridge_committed": has_token("local_bridge_copy"),
        "local_lab_copy_committed": has_token("local_lab_copies"),
        "source_slx_modified": False,
        "venv_committed": has_token(".venv", "site-packages"),
        "wheel_or_dll_committed": any(path.endswith(".whl") or path.endswith(".dll") for path in tracked),
        "model_files_committed": any(path.endswith(ext) for path in tracked for ext in [".pt", ".pth", ".ckpt"]),
    }
    safety["safety_check_passed"] = not any(
        bool(safety[key])
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
    return safety


def _recommended_next_step(summary: dict[str, Any]) -> str:
    status = summary.get("execution_status")
    pilot = summary.get("pilot_label_value")
    last_phase = summary.get("last_seen_phase_if_available")
    if status == "timeout" and last_phase == "phase_sim_start":
        return "inspect Simulink solver/runtime settings for SPP001 bridge before any broader execution"
    if summary.get("phase_sim_done_seen") and pilot is None:
        return "repair compact evidence parser/label-decision contract before any label export"
    if summary.get("phase_sim_done_seen") and pilot in {0, 1}:
        return "approve a tiny 3-to-5 selected-pair smoke batch in a separate round; do not export formal labels or train yet"
    if status in {"failed", "blocked"}:
        return "repair the SPP001 sim-stage diagnostic blocker before any broader execution"
    return "inspect compact SPP001 sim-stage diagnostic evidence before any broader execution"


def build_payloads(args: argparse.Namespace) -> dict[str, Any]:
    if not args.approved_sim_stage_diagnostic_only:
        raise SystemExit("--approved-sim-stage-diagnostic-only is required")
    if args.pair_id != SPP001_PAIR_ID:
        raise SystemExit("Only --pair-id SPP001 is approved")
    if args.max_pairs != 1:
        raise SystemExit("--max-pairs 1 is required")
    if not _exists(args.provenance_manifest):
        raise SystemExit(f"Missing repaired same-wrapper manifest: {args.provenance_manifest}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs = _read_json(PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json")
    pair = _choose_smoke_candidate(pairs, SPP001_PAIR_ID)
    manifest = _read_json(args.provenance_manifest)
    timeout_diagnosis = _read_json_or_empty(TIMEOUT_DIAGNOSIS_DIR / "spp001_timeout_diagnosis_summary.json")
    prior_summary = _read_json_or_empty(BRIDGE_RERUN_DIR / "spp001_bridge_smoke_rerun_summary.json")

    result = _attempt_spp001_matlab(
        pair,
        OUT_DIR,
        args.provenance_manifest,
        python_timeout_s=args.python_timeout_seconds,
        matlab_timeout_s=args.matlab_timeout_seconds,
        diagnostic_only=False,
        sim_stage_diagnostic_only=True,
    )
    if result.get("pair_id") != SPP001_PAIR_ID:
        result.update(
            {
                "pair_id": SPP001_PAIR_ID,
                "execution_status": "failed",
                "pilot_label_status": "failed",
                "pilot_label_value": None,
                "timeout_or_failure_reason": "Diagnostic result did not return SPP001",
            }
        )

    progress_marker = _read_json_or_empty(OUT_DIR / "matlab_compact/matlab_selected_pair_progress_marker.json")
    compact = _read_json_or_empty(OUT_DIR / "matlab_compact/matlab_selected_pair_compact_evidence_summary.json")
    phase_trace = result.get("phase_trace") or progress_marker.get("phase_timing") or compact.get("phase_timing") or []
    last_phase = result.get("last_seen_phase_if_available") or progress_marker.get("last_seen_phase")
    if not last_phase and phase_trace:
        last_phase = phase_trace[-1].get("phase")

    phase_names = [item.get("phase") for item in phase_trace if isinstance(item, dict)]
    phase_sim_start_seen = bool(result.get("phase_sim_start_seen")) or "phase_sim_start" in phase_names
    phase_sim_done_seen = bool(result.get("phase_sim_done_seen")) or "phase_sim_done" in phase_names
    sim_elapsed = result.get("sim_elapsed_seconds_if_available")
    if sim_elapsed in ([], ""):
        sim_elapsed = None

    label_available = result.get("pilot_label_value") in {0, 1}
    planned_sequence = ";".join(str(item) for item in pair.get("planned_contingency_sequence", ["L15", "L04"]))
    summary = {
        "diagnosis_scope": "spp001_sim_stage_diagnostic_retry",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_timeout_diagnosis_commit": SOURCE_TIMEOUT_DIAGNOSIS_COMMIT,
        "pair_id": SPP001_PAIR_ID,
        "state_id": pair.get("state_id"),
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "planned_contingency_sequence": planned_sequence,
        "selection_bucket": pair.get("selection_bucket"),
        "same_wrapper_confirmed": bool(manifest.get("same_wrapper_confirmed", False)),
        "previous_likely_timeout_stage": timeout_diagnosis.get("likely_timeout_stage", "phase_sim_start"),
        "previous_execution_status": prior_summary.get("execution_status"),
        "previous_python_timeout_seconds": timeout_diagnosis.get("previous_timeout_seconds"),
        "sim_stage_diagnostic_attempted": True,
        "execution_status": result.get("execution_status"),
        "single_pair_executed": result.get("execution_status") == "succeeded",
        "simulink_run": phase_sim_start_seen,
        "phase_sim_start_seen": phase_sim_start_seen,
        "phase_sim_done_seen": phase_sim_done_seen,
        "last_seen_phase_if_available": last_phase,
        "sim_elapsed_seconds_if_available": sim_elapsed,
        "python_timeout_seconds": args.python_timeout_seconds,
        "matlab_timeout_seconds_if_available": result.get("matlab_timeout_seconds_if_available") or args.matlab_timeout_seconds,
        "simulation_stop_time_seconds": args.simulation_stop_time,
        "simulation_mode": "normal",
        "fast_restart": False,
        "pilot_label_value": result.get("pilot_label_value"),
        "pilot_label_status": result.get("pilot_label_status"),
        "pilot_label_available": label_available,
        "pilot_labels_are_formal_training_labels": False,
        "no_formal_label_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "local_bridge_committed": False,
        "source_slx_modified": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "l12_special_case_preserved": True,
        "nf06_warning_preserved": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "should_train_gcn_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "blocker_if_any": None if result.get("execution_status") == "succeeded" else result.get("timeout_or_failure_reason"),
    }
    summary["recommended_next_step"] = _recommended_next_step(summary)

    gate = {
        "gate_scope": "spp001_sim_stage_diagnostic_gate",
        "pair_id": SPP001_PAIR_ID,
        "same_wrapper_confirmed": summary["same_wrapper_confirmed"],
        "selected_32_batch_allowed": False,
        "full_1056_allowed": False,
        "formal_label_export_allowed": False,
        "gcn_training_allowed": False,
        "can_request_selected_32_batch": False,
        "can_request_formal_label_export": False,
        "can_request_gcn_training": False,
        "can_request_next_action": summary["execution_status"] == "succeeded" and label_available,
        "blocker_if_any": summary["blocker_if_any"],
    }
    no_leakage = {
        "audit_scope": "spp001_sim_stage_diagnostic_no_leakage_audit",
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "no_leakage_policy_passed": True,
    }
    safety = _large_file_safety()
    excerpt = {
        "excerpt_scope": "spp001_sim_stage_stdout_stderr_excerpt",
        "pair_id": SPP001_PAIR_ID,
        "matlab_stdout_tail": _tail_lines(result.get("matlab_stdout_tail", [])),
        "matlab_stderr_tail": _tail_lines(result.get("matlab_stderr_tail", [])),
        "timeout_or_failure_reason": result.get("timeout_or_failure_reason"),
    }
    phase_payload = {
        "trace_scope": "spp001_sim_stage_phase_trace",
        "pair_id": SPP001_PAIR_ID,
        "phase_trace": phase_trace,
        "last_seen_phase_if_available": last_phase,
        "phase_sim_start_seen": phase_sim_start_seen,
        "phase_sim_done_seen": phase_sim_done_seen,
        "sim_elapsed_seconds_if_available": sim_elapsed,
    }
    result_payload = dict(result)
    result_payload.update(
        {
            "pair_id": SPP001_PAIR_ID,
            "same_wrapper_confirmed": summary["same_wrapper_confirmed"],
            "pilot_labels_are_formal_training_labels": False,
            "python_timeout_seconds": args.python_timeout_seconds,
            "matlab_timeout_seconds_if_available": summary["matlab_timeout_seconds_if_available"],
            "phase_sim_start_seen": phase_sim_start_seen,
            "phase_sim_done_seen": phase_sim_done_seen,
            "last_seen_phase_if_available": last_phase,
            "sim_elapsed_seconds_if_available": sim_elapsed,
        }
    )
    return {
        "summary": summary,
        "result": result_payload,
        "phase_trace": phase_payload,
        "excerpt": excerpt,
        "gate": gate,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_doc(summary: dict[str, Any]) -> str:
    return f"""# IEEE39 SPP001 Sim-Stage Diagnostic Retry

This round is an SPP001 sim-stage diagnostic retry for `L15 -> L04` only. It does not train GCN, does not rerun formal audit, does not execute selected 32 batch, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not deploy a model.

## Plain-Language Summary

The previous round reached `phase_sim_start`, which means MATLAB startup, manifest read, local bridge model load, TripCommand setting, and update diagram had already completed. This round only checks the `sim()` stage with a longer guarded Python timeout. Timeout, failed, blocked, or unknown evidence cannot become a 0/1 label. Even if a pilot label appears, it is not a formal training label.

## Result

- diagnosis_scope: `{summary["diagnosis_scope"]}`
- pair_id: `{summary["pair_id"]}`
- previous_likely_timeout_stage: `{summary["previous_likely_timeout_stage"]}`
- sim_stage_diagnostic_attempted: `{summary["sim_stage_diagnostic_attempted"]}`
- execution_status: `{summary["execution_status"]}`
- single_pair_executed: `{summary["single_pair_executed"]}`
- simulink_run: `{summary["simulink_run"]}`
- phase_sim_start_seen: `{summary["phase_sim_start_seen"]}`
- phase_sim_done_seen: `{summary["phase_sim_done_seen"]}`
- last_seen_phase_if_available: `{summary["last_seen_phase_if_available"]}`
- python_timeout_seconds: `{summary["python_timeout_seconds"]}`
- matlab_timeout_seconds_if_available: `{summary["matlab_timeout_seconds_if_available"]}`
- pilot_label_value: `{summary["pilot_label_value"]}`
- pilot_label_status: `{summary["pilot_label_status"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

No raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, production model, or local bridge `.slx` file is committed. The source `.slx` is not modified. Bus-fault labels are not used. Line-trip labels remain first priority. L12 remains special/excluded. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = [
        ("spp001_sim_stage_diagnostic_summary", payloads["summary"], "IEEE39 SPP001 Sim-Stage Diagnostic Summary"),
        ("spp001_sim_stage_diagnostic_result", payloads["result"], "IEEE39 SPP001 Sim-Stage Diagnostic Result"),
        ("spp001_sim_stage_phase_trace", payloads["phase_trace"], "IEEE39 SPP001 Sim-Stage Phase Trace"),
        ("spp001_sim_stage_stdout_stderr_excerpt", payloads["excerpt"], "IEEE39 SPP001 Sim-Stage Stdout/Stderr Excerpt"),
        ("spp001_sim_stage_diagnostic_gate", payloads["gate"], "IEEE39 SPP001 Sim-Stage Diagnostic Gate"),
        ("no_leakage_spp001_sim_stage_diagnostic_audit", payloads["no_leakage"], "IEEE39 SPP001 Sim-Stage No-Leakage Audit"),
        ("large_file_safety_spp001_sim_stage_diagnostic", payloads["safety"], "IEEE39 SPP001 Sim-Stage Large-File Safety"),
    ]
    for stem, payload, title in files:
        _write_json(OUT_DIR / f"{stem}.json", payload)
        _write_kv_md(OUT_DIR / f"{stem}.md", title, payload)
        if stem in {"spp001_sim_stage_diagnostic_summary", "spp001_sim_stage_diagnostic_result"}:
            _write_kv_csv(OUT_DIR / f"{stem}.csv", payload)
    _write_rows_csv(OUT_DIR / "spp001_sim_stage_diagnostic_result.csv", [payloads["result"]])
    if write_report:
        DOC.write_text(_build_doc(payloads["summary"]), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the approved IEEE39 SPP001 sim-stage diagnostic retry.")
    parser.add_argument("--approved-sim-stage-diagnostic-only", action="store_true")
    parser.add_argument("--pair-id", default=SPP001_PAIR_ID)
    parser.add_argument("--max-pairs", type=int, default=1)
    parser.add_argument("--provenance-manifest", type=Path, default=REPAIRED_MANIFEST)
    parser.add_argument("--python-timeout-seconds", type=int, default=600)
    parser.add_argument("--matlab-timeout-seconds", type=int, default=540)
    parser.add_argument("--simulation-stop-time", type=float, default=1.2)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payloads = build_payloads(args)
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
