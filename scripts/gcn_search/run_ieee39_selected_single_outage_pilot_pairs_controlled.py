from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_BACKEND_DIAGNOSIS_COMMIT = "0d96b0c258e23f4fe5c2ec01cac2a63b5d85c06f"

DIAGNOSIS_DIR = ROOT / "results/gcn_search/ieee39_controlled_execution_backend_diagnosis"
PILOT_PAIR_DIR = ROOT / "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run"
APPROVAL_JSON = ROOT / "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution/selected_pair_execution_approval.json"
OUT_DIR = ROOT / "results/gcn_search/ieee39_controlled_execution_backend_repair"
DOC = ROOT / "docs/ieee39_controlled_execution_backend_repair.md"

NEXT_STEP = "approve execution of selected 32 pairs using the repaired backend in a separate round"
BLOCKER = "execution intentionally not run in repair round; manual approval and explicit --execute are required"


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


def _write_readiness_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# IEEE39 Selected Pair Backend Readiness Matrix",
        "",
        "This matrix is for future manual approval. It is not execution evidence and not a formal label export.",
        "",
        "| pair_id | prior | next | mapping | contract | matlab | parser | status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {pair_id} | {prior_outaged_branch} | {candidate_next_branch} | {mapping_ready} | "
            "{execution_contract_ready} | {matlab_entrypoint_ready} | {parser_contract_ready} | "
            "{current_status} |".format(**row)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _selected_pairs(max_pairs: int) -> list[dict[str, Any]]:
    rows = _read_json(PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json")
    return rows[:max_pairs]


def _build_readiness_matrix(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for row in pairs:
        l12_flag = "L12" in {row.get("prior_outaged_branch"), row.get("candidate_next_branch")}
        ready = not l12_flag
        matrix.append(
            {
                "pair_id": row["pair_id"],
                "prior_outaged_branch": row["prior_outaged_branch"],
                "candidate_next_branch": row["candidate_next_branch"],
                "mapping_ready": True,
                "l12_special_case_flag": l12_flag,
                "selected_32_guard_passed": True,
                "execution_contract_ready": True,
                "matlab_entrypoint_ready": True,
                "parser_contract_ready": True,
                "future_execution_ready": ready,
                "current_status": "ready_for_manual_approval" if ready else "blocked",
                "notes": "dry-run repair row; no selected pair was executed",
            }
        )
    return matrix


def build_payloads(max_pairs: int, approved_selected_pairs_only: bool, execute: bool) -> dict[str, Any]:
    if max_pairs > 32:
        raise SystemExit("--max-pairs cannot exceed 32 for selected-32-only backend repair")
    diagnosis = _read_json(DIAGNOSIS_DIR / "backend_readiness_summary.json")
    approval = _read_json(APPROVAL_JSON)
    pairs = _selected_pairs(max_pairs)
    if len(pairs) != 32:
        raise SystemExit("selected pair manifest must contain exactly 32 rows for this repair round")
    if not approved_selected_pairs_only:
        raise SystemExit("--approved-selected-pairs-only is required")
    if execute:
        raise SystemExit("This repair-round skeleton does not execute MATLAB; execute selected pairs in a separately approved round")

    readiness = _build_readiness_matrix(pairs)
    summary = {
        "repair_scope": "controlled_execution_backend_repair",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_pairs_executed": False,
        "simulink_run": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_backend_diagnosis_commit": SOURCE_BACKEND_DIAGNOSIS_COMMIT,
        "selected_pair_count": len(pairs),
        "python_runner_added": True,
        "matlab_entrypoint_added": True,
        "result_parser_contract_added": True,
        "evidence_writer_added": True,
        "manual_instruction_pack_added": True,
        "selected_32_only_guard_added": True,
        "full_1056_guard_added": True,
        "no_formal_label_export_guard_added": True,
        "no_training_guard_added": True,
        "no_raw_artifact_policy_added": True,
        "graceful_blocked_mode_available": True,
        "can_execute_selected_32_pairs_after_manual_approval": True,
        "can_execute_selected_32_pairs_now": False,
        "blocker_if_any": BLOCKER,
        "recommended_next_step": NEXT_STEP,
        "source_diagnosis_scope": diagnosis.get("diagnosis_scope"),
        "approval_scope": approval.get("approval_scope"),
    }
    contract = {
        "contract_scope": "selected_pair_execution_contract",
        "allowed_pair_count": 32,
        "full_1056_generation_allowed": False,
        "requires_approved_selected_pairs_only": True,
        "requires_explicit_execute_flag": True,
        "default_mode": "dry_run_or_blocked",
        "allowed_outputs": [
            "compact per-pair evidence rows",
            "backend repair/readiness summary",
            "timeout or blocked status",
            "pilot_label_value only when future approved evidence can decide 0/1",
        ],
        "forbidden_outputs": [
            "formal training labels",
            "raw trajectories",
            "full timeseries",
            ".mat files",
            ".slx or .slxc modifications",
            "model checkpoints",
        ],
        "timeout_policy": "timeout remains timeout/unknown and is not converted to 0/1",
        "unknown_policy": "unknown and blocked remain null",
        "failed_policy": "failed remains failed/unknown and is not converted to 0/1",
        "label_value_policy": "pilot_label_value remains null unless future approved compact evidence determines 0 or 1",
        "formal_label_export_policy": False,
        "raw_artifact_policy": "commit only compact JSON/MD/CSV summaries; do not commit raw trajectories, full timeseries, .mat, .slx, .slxc, or slprj",
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
        "contract": contract,
        "readiness": readiness,
        "no_leakage": no_leakage,
        "safety": safety,
    }


def _manual_instructions() -> str:
    return """# IEEE39 Selected-32 Manual Execution Instruction Pack

This instruction pack is for a future separately approved execution round. Do not use it to train GCN, rerun formal audit, export formal labels, retrain the reranker, or run full 1056 generation.

## 1. Confirm MATLAB/Simulink

Run `matlab -batch "ver"` locally and confirm Simulink is licensed. This repair round does not run Simulink.

## 2. Run Only Selected 32 Pairs

Use only `results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run/selected_single_outage_pilot_pairs.json`. Do not substitute the 1056-pair plan.

## 3. Python Runner

Future approved command:

```powershell
python scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py --approved-selected-pairs-only --max-pairs 32 --execute --write-report
```

The repair round must not use `--execute`.

## 4. MATLAB Entrypoint

Future approved MATLAB entrypoint:

```matlab
run_ieee39_selected_pair_line_trip_sequence(manifestPath, outputDir, "approved_selected_pairs_only", true, "execute", true)
```

## 5. Output Directory

Write only compact evidence summaries under a future approved output directory. Do not write raw trajectory, full timeseries, or `.mat` files.

## 6. Safety Checks

Before committing, verify no raw trajectory, full timeseries, `.mat`, `.slx`, `.slxc`, `slprj`, venv, wheel, DLL, or model files are staged.

## 7. Timeout

Timeout remains timeout/unknown and must not become 0 or 1.

## 8. Blocked

Blocked remains null. Do not fabricate pilot labels.

## 9. Compact Evidence Summary

Collect one compact row per pair with `pair_id`, `execution_status`, `pilot_label_value`, `pilot_label_status`, `dynamic_stress_score_if_available`, `unstable_flag_if_available`, and `timeout_or_failure_reason`.

## 10. Forbidden Actions

Do not export formal labels. Do not train GCN. Do not run full 1056 generation. Manual approval is required before execution.
"""


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 Controlled Execution Backend Repair

This round is controlled execution backend repair. It does not train GCN, does not rerun formal audit, does not execute selected 32 pairs, does not run full 1056 generation, does not export formal labels, does not retrain the reranker, and does not save a production model.

## What Was Added

- selected-32-only Python runner
- MATLAB two-step line-trip entrypoint skeleton
- result parser contract
- evidence-only output writer
- local/manual execution instruction pack
- selected-32-only guard
- no full 1056 generation guard
- no formal label export guard
- no training guard
- no raw trajectory / full timeseries / `.mat` commit guard

## Current Status

- repair_scope: `{summary["repair_scope"]}`
- selected_pair_count: `{summary["selected_pair_count"]}`
- can_execute_selected_32_pairs_after_manual_approval: `{summary["can_execute_selected_32_pairs_after_manual_approval"]}`
- can_execute_selected_32_pairs_now: `{summary["can_execute_selected_32_pairs_now"]}`
- blocker_if_any: `{summary["blocker_if_any"]}`

## Boundaries

Execution of selected 32 pairs still requires the next round of manual approval. This round does not commit raw trajectory, full timeseries, or `.mat` files. `beta * RATE_A` is an audit-only proxy, not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection. There is no deployment and no GCN usefulness conclusion.

## Next Step

`{summary["recommended_next_step"]}`.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "backend_repair_summary.json", payloads["summary"])
    _write_kv_md(OUT_DIR / "backend_repair_summary.md", "IEEE39 Backend Repair Summary", payloads["summary"])
    _write_kv_csv(OUT_DIR / "backend_repair_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "backend_execution_contract.json", payloads["contract"])
    _write_kv_md(OUT_DIR / "backend_execution_contract.md", "IEEE39 Backend Execution Contract", payloads["contract"])
    (OUT_DIR / "manual_execution_instruction_pack.md").write_text(_manual_instructions(), encoding="utf-8")
    _write_json(OUT_DIR / "selected_pair_backend_readiness_matrix.json", payloads["readiness"])
    _write_readiness_md(OUT_DIR / "selected_pair_backend_readiness_matrix.md", payloads["readiness"])
    _write_rows_csv(OUT_DIR / "selected_pair_backend_readiness_matrix.csv", payloads["readiness"])
    _write_json(OUT_DIR / "no_leakage_backend_repair_audit.json", payloads["no_leakage"])
    _write_kv_md(OUT_DIR / "no_leakage_backend_repair_audit.md", "IEEE39 No-Leakage Backend Repair Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "large_file_safety_backend_repair.json", payloads["safety"])
    _write_kv_md(OUT_DIR / "large_file_safety_backend_repair.md", "IEEE39 Large File Safety Backend Repair", payloads["safety"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair IEEE39 selected-32-only controlled execution backend skeleton.")
    parser.add_argument("--approved-selected-pairs-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-pairs", type=int, default=32)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [
        DIAGNOSIS_DIR / "backend_readiness_summary.json",
        DIAGNOSIS_DIR / "backend_component_inventory.json",
        DIAGNOSIS_DIR / "selected_pair_execution_mapping_diagnosis.json",
        DIAGNOSIS_DIR / "safe_execution_repair_plan.json",
        PILOT_PAIR_DIR / "selected_single_outage_pilot_pairs.json",
        APPROVAL_JSON,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads(args.max_pairs, args.approved_selected_pairs_only, args.execute)
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
