"""Prepare IEEE39 all-remaining bus-fault batch readiness dry-run artifacts.

This script reads manual connection evidence and writes readiness dry-run
artifacts plus a next-round smoke plan manifest. It does not run simulation,
does not run actual smoke, does not export labels, does not train GCN, and does
not retrain any reranker.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BATCH_ID = "bus_fault_all_remaining_manual_wiring"
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
EVIDENCE_DIR = BASE / "manual_connection_evidence"
READINESS_DIR = BASE / "readiness_dry_run"
TARGETS_JSON = BASE / "ieee39_bus_fault_all_remaining_targets.json"


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> Any:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8") as handle:
        handle.write(text)


def _targets(requested: list[str]) -> list[str]:
    payload = _read_json(TARGETS_JSON)
    all_targets = list(payload["all_new_target_buses"])
    return all_targets if requested == ["all"] else requested


def _status(evidence: dict[str, Any]) -> tuple[str, bool, list[str]]:
    required_true = [
        "temp_model_exists",
        "fault_block_found",
        "fault_block_name_correct",
        "update_diagram_success",
        "human_verified_injection_point",
        "safe_to_run_smoke_recommendation",
    ]
    required_false = [
        "source_slx_modified",
        "temporary_slx_committed",
        "simulink_smoke_run",
        "labels_exported",
        "gcn_trained",
        "reranker_retrained",
    ]
    failed: list[str] = []
    for key in required_true:
        if evidence.get(key) is not True:
            failed.append(f"{key}_not_true")
    for key in required_false:
        if evidence.get(key) is not False:
            failed.append(f"{key}_not_false")
    ready = not failed
    return ("ready_for_next_round_actual_smoke" if ready else "blocked_before_smoke", ready, failed)


def _per_bus_md(payload: dict[str, Any]) -> str:
    return f"""# Readiness Dry-Run {payload['target_bus']}

This is a readiness dry-run only. It is not actual smoke, not simulation, not
label export, not GCN training, and not GCN usefulness audit.

| field | value |
| --- | --- |
| target_bus | `{payload['target_bus']}` |
| readiness_status | `{payload['readiness_status']}` |
| ready_for_next_round_actual_smoke | `{str(payload['ready_for_next_round_actual_smoke']).lower()}` |
| special_handling | `{str(payload['special_handling']).lower()}` |
| update_diagram_success | `{str(payload['update_diagram_success']).lower()}` |
| human_verified_injection_point | `{str(payload['human_verified_injection_point']).lower()}` |

Recommended next step: `{payload['recommended_next_step']}`
"""


def _summary_md(summary: dict[str, Any]) -> str:
    ready = ", ".join(summary["ready_buses"]) or "none"
    blocked = ", ".join(summary["blocked_buses"]) or "none"
    return f"""# IEEE39 All-Remaining Bus-Fault Batch Readiness Dry-Run

This round is a batch readiness dry-run. It did not run simulation, did not run
actual smoke, did not export labels, did not train GCN, did not retrain the
reranker, and did not run a GCN usefulness audit.

| metric | value |
| --- | ---: |
| total_targets | {summary['total_targets']} |
| num_manual_evidence_passed | {summary['num_manual_evidence_passed']} |
| num_readiness_dry_run_checked | {summary['num_readiness_dry_run_checked']} |
| num_ready_for_next_round_actual_smoke | {summary['num_ready_for_next_round_actual_smoke']} |
| num_blocked_before_smoke | {summary['num_blocked_before_smoke']} |

- ready buses: `{ready}`
- blocked buses: `{blocked}`
- recommended_next_step: `{summary['recommended_next_step']}`

The 37 new targets are not candidate labels and are not smoke success. B39/B26
remain existing candidate labels, not formal labels.
"""


def _manifest_md(manifest: dict[str, Any]) -> str:
    ready = ", ".join(manifest["ready_buses"]) or "none"
    return f"""# Next-Round Actual Smoke Plan Manifest

This is only a plan for a later round. Actual smoke was not run in this round.

- plan_scope: `{manifest['plan_scope']}`
- actual_smoke_run_this_round: `{str(manifest['actual_smoke_run_this_round']).lower()}`
- ready buses: `{ready}`
- output_dir_for_future_smoke: `{manifest['output_dir_for_future_smoke']}`

Do not export labels and do not train GCN from this plan alone.
"""


def _doc_md(summary: dict[str, Any]) -> str:
    return f"""# IEEE39 All-Remaining Bus-Fault Batch Readiness Dry-Run

This round is a batch readiness dry-run. It is not actual smoke, and no
simulation was run. It does not export labels, does not train GCN, does not
retrain the reranker, and does not run a GCN usefulness audit.

## Result

- total targets: `{summary['total_targets']}`
- readiness checked: `{summary['num_readiness_dry_run_checked']}`
- ready for next-round actual smoke: `{summary['num_ready_for_next_round_actual_smoke']}`
- blocked before smoke: `{summary['num_blocked_before_smoke']}`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

Only readiness-passed buses can enter the next actual smoke round. The 37 new
targets are still not candidate labels and are still not smoke success. B16
special handling is preserved, and the old fault was not moved.

B39/B26 remain existing candidate labels, not formal labels. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.
"""


def run(targets: list[str]) -> None:
    selected = _targets(targets)
    readiness_records: list[dict[str, Any]] = []
    for bus in selected:
        evidence = _read_json(EVIDENCE_DIR / f"manual_connection_evidence_{bus}.json")
        status, ready, failed = _status(evidence)
        failed_checks = list(evidence.get("failed_checks", [])) + failed
        warning_checks = list(evidence.get("warning_checks", []))
        payload = {
            "batch_id": BATCH_ID,
            "target_bus": bus,
            "special_handling": bool(evidence.get("special_handling")),
            "readiness_scope": "dry_run_only",
            "actual_smoke_run": False,
            "simulation_run": False,
            "labels_exported": False,
            "candidate_label_exported": False,
            "gcn_trained": False,
            "reranker_retrained": False,
            "gcn_usefulness_audit_run": False,
            "source_slx_modified": False,
            "temporary_slx_committed": False,
            "temp_model_path": evidence.get("temp_model_path"),
            "actual_checked_model_path": evidence.get("actual_checked_model_path"),
            "temp_model_exists": bool(evidence.get("temp_model_exists")),
            "selected_fault_block_path": f"Grid/Fault_{bus}_TEMP",
            "fault_block_found": bool(evidence.get("fault_block_found")),
            "fault_block_name_correct": bool(evidence.get("fault_block_name_correct")),
            "fault_block_connected_in_parallel": bool(evidence.get("fault_block_connected_in_parallel")),
            "original_network_connection_preserved": bool(evidence.get("original_network_connection_preserved")),
            "no_floating_ports": bool(evidence.get("no_floating_ports")),
            "no_unintended_bypass": bool(evidence.get("no_unintended_bypass")),
            "no_unintended_islanding": bool(evidence.get("no_unintended_islanding")),
            "update_diagram_success": bool(evidence.get("update_diagram_success")),
            "human_verified_injection_point": bool(evidence.get("human_verified_injection_point")),
            "safe_to_run_smoke_recommendation_from_manual_evidence": bool(evidence.get("safe_to_run_smoke_recommendation")),
            "fault_start_s": 0.5,
            "fault_clear_s": 0.58,
            "duration_s": 0.08,
            "R_pn_fault": "1e-3 Ohm",
            "R_ng_fault": "1e-3 Ohm",
            "enable_temporal_fault": True,
            "readiness_status": status,
            "ready_for_next_round_actual_smoke": ready,
            "failed_checks": failed_checks,
            "warning_checks": warning_checks,
            "recommended_next_step": "run actual temporary smoke in a separate round" if ready else "fix readiness blockers before smoke",
        }
        _write_json(READINESS_DIR / f"readiness_dry_run_{bus}.json", payload)
        _write_text(READINESS_DIR / f"readiness_dry_run_{bus}.md", _per_bus_md(payload))
        readiness_records.append(payload)

    ready_buses = [r["target_bus"] for r in readiness_records if r["ready_for_next_round_actual_smoke"]]
    blocked_buses = [r["target_bus"] for r in readiness_records if not r["ready_for_next_round_actual_smoke"]]
    blocked_reasons = {r["target_bus"]: r["failed_checks"] for r in readiness_records if not r["ready_for_next_round_actual_smoke"]}
    if len(ready_buses) == len(readiness_records):
        recommended = "run batch actual temporary smoke for all 37 ready targets in a separate round, without label export or training"
    elif ready_buses:
        recommended = "run actual smoke only for ready targets in a separate round and fix blocked targets separately"
    else:
        recommended = "fix readiness blockers before smoke"
    b16 = next((r for r in readiness_records if r["target_bus"] == "B16"), {})
    summary = {
        "batch_id": BATCH_ID,
        "readiness_scope": "dry_run_only",
        "total_targets": len(readiness_records),
        "normal_targets": 36,
        "special_targets": 1,
        "existing_completed_bus_faults": ["B39", "B26"],
        "current_candidate_count": 42,
        "old_formal_gate": "35 / 33 / 33",
        "num_manual_evidence_passed": sum(1 for r in readiness_records if r["safe_to_run_smoke_recommendation_from_manual_evidence"]),
        "num_readiness_dry_run_checked": len(readiness_records),
        "num_ready_for_next_round_actual_smoke": len(ready_buses),
        "num_blocked_before_smoke": len(blocked_buses),
        "ready_buses": ready_buses,
        "blocked_buses": blocked_buses,
        "blocked_reasons_by_bus": blocked_reasons,
        "b16_special_handling_preserved": bool(b16.get("special_handling")),
        "b16_old_fault_not_moved": True,
        "simulation_run": False,
        "actual_smoke_run": False,
        "labels_exported": False,
        "candidate_labels_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "should_run_actual_smoke_now": False,
        "should_export_labels_now": False,
        "should_train_now": False,
        "recommended_next_step": recommended,
    }
    _write_json(READINESS_DIR / "batch_readiness_dry_run_summary.json", summary)
    _write_text(READINESS_DIR / "batch_readiness_dry_run_summary.md", _summary_md(summary))
    with open(_fs_path(READINESS_DIR / "batch_readiness_dry_run_summary.csv"), "w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "target_bus",
            "special_handling",
            "readiness_status",
            "ready_for_next_round_actual_smoke",
            "failed_checks",
            "warning_checks",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in readiness_records:
            writer.writerow({key: record.get(key) for key in fieldnames})

    scenario_id_by_bus = {bus: f"BF_{bus}_TEMP_SMOKE" for bus in ready_buses}
    manifest = {
        "plan_scope": "next_round_actual_smoke_plan_only",
        "actual_smoke_run_this_round": False,
        "ready_buses": ready_buses,
        "blocked_buses": blocked_buses,
        "scenario_id_by_bus": scenario_id_by_bus,
        "target_bus_by_scenario": {scenario: bus for bus, scenario in scenario_id_by_bus.items()},
        "temp_model_path_by_bus": {r["target_bus"]: r["temp_model_path"] for r in readiness_records if r["ready_for_next_round_actual_smoke"]},
        "selected_fault_block_path_by_bus": {r["target_bus"]: r["selected_fault_block_path"] for r in readiness_records if r["ready_for_next_round_actual_smoke"]},
        "fault_start_s": 0.5,
        "fault_clear_s": 0.58,
        "duration_s": 0.08,
        "timeout_seconds": 240,
        "simulation_stop_time": 0.8,
        "output_dir_for_future_smoke": "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/batch_smoke_outputs",
        "should_run_smoke_now": False,
        "should_export_labels_now": False,
        "should_train_now": False,
    }
    _write_json(READINESS_DIR / "batch_actual_smoke_plan_manifest.json", manifest)
    _write_text(READINESS_DIR / "batch_actual_smoke_plan_manifest.md", _manifest_md(manifest))
    _write_text(ROOT / "docs/ieee39_all_remaining_bus_fault_batch_readiness_dry_run.md", _doc_md(summary))
    print(json.dumps({"ready": len(ready_buses), "blocked": len(blocked_buses), "summary": str(READINESS_DIR / "batch_readiness_dry_run_summary.json")}, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", nargs="+", default=["all"])
    parser.add_argument("--dry-run", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run(args.targets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
