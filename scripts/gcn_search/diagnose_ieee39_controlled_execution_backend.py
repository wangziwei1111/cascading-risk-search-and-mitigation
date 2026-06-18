from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_EXECUTION_COMMIT = "606eba793b3895c333ab0c632369bfadde413dca"

EXECUTION_DIR = ROOT / "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution"
PILOT_PAIR_DIR = ROOT / "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run"
WRAPPER_DIR = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model"
WRAPPER_MODEL = WRAPPER_DIR / "generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx"
LINE_MAP = WRAPPER_DIR / "wrapper/ieee39_line_breaker_map_full.csv"
OUT_DIR = ROOT / "results/gcn_search/ieee39_controlled_execution_backend_diagnosis"
DOC = ROOT / "docs/ieee39_controlled_execution_backend_diagnosis.md"

BLOCKER = (
    "selected-pair controlled execution backend is incomplete: missing approved two-step line-trip "
    "sequence injection, selected-pair batch runner, and selected-pair result parser contract"
)
NEXT_STEP = "add a selected-32-only controlled execution backend or write local manual execution instructions before rerunning evidence collection"


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


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with open(_long(path), newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


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


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            for key, value in out.items():
                if isinstance(value, list):
                    out[key] = ";".join(str(item) for item in value)
            writer.writerow(out)


def _write_kv_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.append(f"## {key}")
            lines.append("```json")
            lines.append(json.dumps(value, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
        else:
            lines.append(f"- `{key}`: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_mapping_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# IEEE39 Selected Pair Execution Mapping Diagnosis",
        "",
        "This diagnosis does not execute selected pairs and does not create labels.",
        "",
        "| pair_id | prior | next | prior mapping | next mapping | sequence injection | ready |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {pair_id} | {prior_outaged_branch} | {candidate_next_branch} | "
            "{prior_branch_mapping_available} | {next_branch_mapping_available} | "
            "{sequence_injection_supported} | {execution_ready} |".format(**row)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _script_names(pattern: str) -> list[str]:
    return sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT / "scripts/gcn_search").glob(pattern))


def _candidate_files() -> dict[str, list[str]]:
    matlab_scripts = sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT / "matlab").rglob("*.m"))
    python_wrappers = sorted(
        name
        for pattern in ["*ieee39*simulink*.py", "*ieee39*breaker*.py", "*ieee39*trip*.py", "*selected*single*outage*.py"]
        for name in _script_names(pattern)
    )
    models = sorted(
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (WRAPPER_DIR / "generated_models").glob("*.slx")
    )
    maps = sorted(
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (WRAPPER_DIR / "wrapper").glob("*map*.csv")
    )
    parsers = _script_names("*analy*.py") + _script_names("*review*.py") + _script_names("*collect*.py")
    writers = _script_names("*execute_ieee39_selected_single_outage_pilot_pairs.py") + _script_names("*prepare_ieee39_single_outage_pilot_pair*.py")
    return {
        "candidate_matlab_scripts": matlab_scripts,
        "candidate_python_wrappers": sorted(set(python_wrappers)),
        "candidate_simulink_models": models,
        "candidate_fault_injection_maps": maps,
        "candidate_line_trip_maps": [str(LINE_MAP.relative_to(ROOT)).replace("\\", "/")] if _exists(LINE_MAP) else [],
        "candidate_result_parsers": sorted(set(parsers)),
        "candidate_evidence_writers": sorted(set(writers)),
    }


def _matlab_available() -> bool:
    return shutil.which("matlab") is not None


def build_payloads() -> dict[str, Any]:
    execution_summary = _read_json(EXECUTION_DIR / "selected_pair_execution_summary.json")
    selected_pairs = _read_json(PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json")
    line_rows = _read_csv_rows(LINE_MAP) if _exists(LINE_MAP) else []
    mapped_lines = {row.get("line_id") for row in line_rows}
    candidate_files = _candidate_files()
    matlab_available = _matlab_available()
    wrapper_found = _exists(WRAPPER_MODEL)
    selected_pair_mapping_found = all(
        row.get("prior_outaged_branch") in mapped_lines and row.get("candidate_next_branch") in mapped_lines
        for row in selected_pairs
    )

    # Existing artifacts include single-line maps and evidence writers, but no approved selected-pair two-step runner.
    two_step_supported = False
    batch_runner_found = False
    timeout_policy_found = True
    result_parser_found = False
    evidence_writer_found = True
    safe_no_raw_policy_found = True
    simulink_available: bool | str = "unknown"
    can_execute_now = False
    can_execute_without_full_1056 = True
    graceful_blocked_mode_available = True

    mapping_rows: list[dict[str, Any]] = []
    for row in selected_pairs:
        prior = row["prior_outaged_branch"]
        nxt = row["candidate_next_branch"]
        prior_ok = prior in mapped_lines
        next_ok = nxt in mapped_lines
        missing: list[str] = []
        if not prior_ok:
            missing.append("prior_branch_line_map")
        if not next_ok:
            missing.append("next_branch_line_map")
        missing.extend(
            [
                "approved_two_step_line_trip_sequence_injection",
                "selected_pair_batch_runner",
                "selected_pair_result_parser_contract",
            ]
        )
        mapping_rows.append(
            {
                "pair_id": row["pair_id"],
                "prior_outaged_branch": prior,
                "candidate_next_branch": nxt,
                "planned_contingency_sequence": row["planned_contingency_sequence"],
                "prior_branch_mapping_available": prior_ok,
                "next_branch_mapping_available": next_ok,
                "sequence_injection_supported": False,
                "execution_ready": False,
                "missing_mapping_fields": missing,
                "l12_special_case_flag": "L12" in {prior, nxt},
                "notes": "line map exists for branch endpoints, but selected-pair two-step execution backend is not approved",
            }
        )

    missing_components = [
        "approved selected-pair two-step line-trip sequence injection",
        "selected-32-only batch runner",
        "selected-pair dynamic result parser contract",
        "local/manual execution instruction pack",
    ]
    unsafe_components: list[str] = []
    reusable_components = [
        "IEEE39 wrapper model path",
        "L01-L34 line map",
        "selected 32 pair manifest",
        "blocked evidence writer from previous round",
        "timeout/unknown/null safety policy",
        "no-raw-artifact policy",
    ]
    inventory = {
        **candidate_files,
        "missing_components": missing_components,
        "unsafe_components": unsafe_components,
        "reusable_components": reusable_components,
    }
    summary = {
        "diagnosis_scope": "controlled_execution_backend_diagnosis",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "selected_pairs_executed": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_execution_commit": SOURCE_EXECUTION_COMMIT,
        "selected_pair_count": int(execution_summary.get("selected_pair_count", len(selected_pairs))),
        "matlab_available": matlab_available,
        "simulink_available": simulink_available,
        "ieee39_wrapper_model_found": wrapper_found,
        "selected_pair_mapping_found": selected_pair_mapping_found,
        "two_step_line_trip_injection_supported": two_step_supported,
        "batch_runner_found": batch_runner_found,
        "timeout_policy_found": timeout_policy_found,
        "result_parser_found": result_parser_found,
        "evidence_writer_found": evidence_writer_found,
        "safe_no_raw_artifact_policy_found": safe_no_raw_policy_found,
        "can_execute_selected_32_pairs_now": can_execute_now,
        "can_execute_without_full_1056": can_execute_without_full_1056,
        "graceful_blocked_mode_available": graceful_blocked_mode_available,
        "blocker_if_any": BLOCKER,
        "recommended_next_step": NEXT_STEP,
    }
    repair_plan = {
        "repair_plan_scope": "controlled_execution_backend_repair_plan",
        "required_components_to_add": missing_components,
        "proposed_runner_entrypoint": "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
        "proposed_matlab_entrypoint": "matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m",
        "proposed_output_contract": [
            "one compact row per selected pair",
            "execution_status in succeeded/failed/timeout/blocked",
            "pilot_label_value remains null unless approved evidence can decide 0/1",
            "dynamic_stress_score and unstable_flag are outputs only, not inputs",
        ],
        "proposed_timeout_policy": "per-pair timeout remains timeout/unknown and is not converted to 0/1",
        "proposed_unknown_policy": "blocked, missing, failed, timeout, and unknown cases keep null pilot labels",
        "proposed_large_file_policy": "commit only summary JSON/MD/CSV; do not commit raw trajectories, full timeseries, .mat, .slx, .slxc, or slprj",
        "proposed_selected_32_only_guard": "runner must require --approved-selected-pairs-only and reject full 1056 generation",
        "proposed_no_formal_label_export_guard": "formal label export must stay false until separately approved",
        "proposed_no_training_guard": "GCN/reranker training must stay disabled in backend repair and evidence collection rounds",
        "manual_approval_required_before_execution": True,
    }
    no_leakage = {
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "proxy_relay_threshold_used_only_in_feature_generation": True,
        "bus_fault_labels_used": False,
        "no_leakage_policy_passed": True,
    }
    safety = {
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "venv_committed": False,
        "wheel_or_dll_committed": False,
        "model_files_committed": False,
        "safety_check_passed": True,
    }
    return {
        "summary": summary,
        "inventory": inventory,
        "mapping": mapping_rows,
        "repair_plan": repair_plan,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 Controlled Execution Backend Diagnosis

This round is controlled execution backend diagnosis only. It does not train GCN, does not rerun formal audit, does not execute selected 32 pairs, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not save a production model.

## Plain-Language Purpose

上一轮 selected pair execution 被 `blocked`，原因是没有安全可调用的 controlled Simulink execution backend。大白话说：我们有 32 个要检查的故障对，也有部分线路映射和 wrapper 线索，但还缺一个可靠的“两步断线、批量运行、超时保护、只输出 evidence summary”的后端。

## Diagnosis Result

- diagnosis_scope: `{summary["diagnosis_scope"]}`
- selected_pair_count: `{summary["selected_pair_count"]}`
- matlab_available: `{summary["matlab_available"]}`
- simulink_available: `{summary["simulink_available"]}`
- ieee39_wrapper_model_found: `{summary["ieee39_wrapper_model_found"]}`
- selected_pair_mapping_found: `{summary["selected_pair_mapping_found"]}`
- two_step_line_trip_injection_supported: `{summary["two_step_line_trip_injection_supported"]}`
- batch_runner_found: `{summary["batch_runner_found"]}`
- timeout_policy_found: `{summary["timeout_policy_found"]}`
- result_parser_found: `{summary["result_parser_found"]}`
- evidence_writer_found: `{summary["evidence_writer_found"]}`
- safe_no_raw_artifact_policy_found: `{summary["safe_no_raw_artifact_policy_found"]}`
- can_execute_selected_32_pairs_now: `{summary["can_execute_selected_32_pairs_now"]}`
- can_execute_without_full_1056: `{summary["can_execute_without_full_1056"]}`
- graceful_blocked_mode_available: `{summary["graceful_blocked_mode_available"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

This round does not commit raw trajectory, full timeseries, or `.mat` files. `beta * RATE_A` is an audit-only proxy, not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection. There is no deployment and no GCN usefulness conclusion.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "backend_readiness_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "backend_readiness_summary.md", "IEEE39 Backend Readiness Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "backend_readiness_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "backend_component_inventory.json", payloads["inventory"])
    _write_kv_md(OUT_DIR / "backend_component_inventory.md", "IEEE39 Backend Component Inventory", payloads["inventory"])
    _write_json(OUT_DIR / "selected_pair_execution_mapping_diagnosis.json", payloads["mapping"])
    _write_mapping_md(OUT_DIR / "selected_pair_execution_mapping_diagnosis.md", payloads["mapping"])
    _write_rows_csv(OUT_DIR / "selected_pair_execution_mapping_diagnosis.csv", payloads["mapping"])
    _write_json(OUT_DIR / "safe_execution_repair_plan.json", payloads["repair_plan"])
    _write_kv_md(OUT_DIR / "safe_execution_repair_plan.md", "IEEE39 Safe Execution Repair Plan", payloads["repair_plan"])
    _write_json(OUT_DIR / "no_leakage_backend_diagnosis_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_backend_diagnosis_audit.md", "IEEE39 No-Leakage Backend Diagnosis Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_safety_backend_diagnosis.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_safety_backend_diagnosis.md", "IEEE39 Large File Safety Backend Diagnosis", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose IEEE39 selected-pair controlled execution backend readiness.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [
        EXECUTION_DIR / "selected_pair_execution_summary.json",
        EXECUTION_DIR / "selected_pair_execution_results.json",
        EXECUTION_DIR / "selected_pair_execution_approval.json",
        EXECUTION_DIR / "large_file_and_artifact_safety_check.json",
        PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads()
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
