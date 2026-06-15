"""Prepare temp-lab bus-fault smoke only when readiness gates allow it."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs"
SUMMARY_FIELDS = [
    "scenario_id",
    "target_bus",
    "fault_start_s",
    "fault_clear_s",
    "duration_s",
    "temp_model_used",
    "source_slx_modified",
    "temporary_slx_committed",
    "simulation_success",
    "physical_fault_or_breaker_action_executed",
    "measurement_extraction_status",
    "training_ready_candidate_smoke",
    "timeout_or_error_message",
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "unstable_flag",
    "signal_source_summary",
    "note",
]


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _is_ignored_temp(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/").lower()
    return "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/" in normalized


def _write_outputs(out_dir: Path, row: dict[str, Any], report: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "ieee39_bus_fault_temp_lab_smoke_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    (out_dir / "ieee39_bus_fault_temp_lab_smoke_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=True) + "\n", encoding="utf-8"
    )
    md = [
        "# IEEE39 Bus-Fault Temp Lab Smoke Report",
        "",
        "This report is preview-only and not a final dynamic performance conclusion.",
        "",
        f"- target_bus: `{row['target_bus']}`",
        f"- simulation_success: `{row['simulation_success']}`",
        f"- safe_to_run_smoke: `{report['safe_to_run_smoke']}`",
        f"- smoke_not_run_reason: `{report.get('smoke_not_run_reason', '')}`",
        "- no labels exported",
        "- no training run",
    ]
    (out_dir / "ieee39_bus_fault_temp_lab_smoke_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _write_b39_readiness_outputs(out_dir: Path, report: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "ieee39_b39_temp_smoke_dry_run_readiness.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# IEEE39 B39 Temp Smoke Dry-Run Readiness",
        "",
        "This is a dry-run readiness report only. It does not run Simulink smoke,",
        "does not modify or commit any `.slx`, does not export labels, does not",
        "train GCN, and does not retrain the reranker.",
        "",
        f"- target_bus: `{report['target_bus']}`",
        f"- dry_run: `{report['dry_run']}`",
        f"- readiness_status: `{report['readiness_status']}`",
        f"- would_run_smoke_next_round: `{report['would_run_smoke_next_round']}`",
        f"- actual_simulink_run: `{report['actual_simulink_run']}`",
        f"- selected_injection_block_path: `{report['selected_injection_block_path']}`",
        f"- selected_fault_block_path: `{report['selected_fault_block_path']}`",
        f"- fault window: `{report['fault_start_s']}` s to `{report['fault_clear_s']}` s",
        f"- formal_label_gate: `{report['formal_label_gate']}`",
        f"- v2_candidate_count: `{report['v2_candidate_count']}`",
        "",
        "Boundary: B39 is ready for a separate next-round temporary smoke attempt,",
        "but B39 is still not smoke success.",
    ]
    (out_dir / "ieee39_b39_temp_smoke_dry_run_readiness.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def _human_readiness_ready(readiness: dict[str, Any]) -> tuple[bool, str]:
    required_exact = {
        "target_bus": "B39",
        "selected_injection_block_path": "Grid/Bus39",
        "selected_fault_block_path": "Grid/Fault_B39_TEMP",
        "formal_label_gate": "35 / 33 / 33",
        "v2_candidate_count": 40,
        "b26_status": "unverified",
    }
    for key, expected in required_exact.items():
        if readiness.get(key) != expected:
            return False, f"human readiness {key}={readiness.get(key)!r}, expected {expected!r}"
    for key in [
        "human_verified_injection_point",
        "safe_to_run_smoke_recommendation",
        "update_diagram_success",
    ]:
        if readiness.get(key) is not True:
            return False, f"human readiness {key} must be true"
    for key in [
        "source_model_saved",
        "temporary_model_committed",
        "source_slx_modified",
        "temporary_slx_committed",
        "simulink_smoke_run",
        "smoke_success",
        "labels_exported",
        "gcn_trained",
        "reranker_retrained",
        "l12_touched",
    ]:
        if readiness.get(key) is not False:
            return False, f"human readiness {key} must be false"
    return True, ""


def run(args: argparse.Namespace) -> dict[str, Any]:
    plan = _read(args.temp_lab_plan)
    inventory = _read(args.matlab_inventory) if args.matlab_inventory else {}
    manual_summary = _read(args.manual_review_summary) if args.manual_review_summary else {}
    human_readiness = _read(args.human_readiness_json) if args.human_readiness_json else {}
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    target_bus = str(args.target_bus or plan["target_bus"])
    temp_model = str(plan["temporary_model_path"])
    reason = ""
    safe = bool(inventory.get("safe_to_run_smoke", False))
    human_ready = False
    if human_readiness:
        human_ready, reason = _human_readiness_ready(human_readiness)
        safe = human_ready
    if target_bus not in {"B39", "B26"}:
        reason = "target_bus is not allowed in this round"
        safe = False
    elif target_bus != str(plan["target_bus"]):
        reason = "target_bus does not match temp lab plan"
        safe = False
    elif human_readiness and target_bus != "B39":
        reason = "human readiness dry-run is only allowed for B39"
        safe = False
    elif human_readiness and manual_summary.get("recommendation") != "manual_review_supports_next_round_inventory_update":
        reason = "manual review summary does not support next-round inventory update"
        safe = False
    elif plan.get("source_slx_modified") is True or inventory.get("source_model_modified") is True:
        reason = "source_slx_modified=true is forbidden"
        safe = False
    elif not _is_ignored_temp(temp_model):
        reason = "temporary model is not under ignored local_lab_copies directory"
        safe = False
    elif not safe:
        reason = "safe_to_run_smoke=false; refusing execution"
    elif args.dry_run:
        reason = "ready_for_next_round_temp_smoke" if human_readiness else "dry-run only"
    else:
        reason = "actual Simulink execution is intentionally disabled in this readiness round"
        safe = False

    row = {
        "scenario_id": f"TEMP_{target_bus}",
        "target_bus": target_bus,
        "fault_start_s": float(plan["fault_start_s"]),
        "fault_clear_s": float(plan["fault_clear_s"]),
        "duration_s": float(plan["duration_s"]),
        "temp_model_used": temp_model,
        "source_slx_modified": False,
        "temporary_slx_committed": False,
        "simulation_success": False,
        "physical_fault_or_breaker_action_executed": False,
        "measurement_extraction_status": "smoke_not_run",
        "training_ready_candidate_smoke": False,
        "timeout_or_error_message": reason,
        "min_voltage_pu": math.nan,
        "max_voltage_pu": math.nan,
        "min_frequency_hz": math.nan,
        "max_frequency_hz": math.nan,
        "max_speed_deviation": math.nan,
        "max_rotor_angle_separation_deg": math.nan,
        "unstable_flag": False,
        "signal_source_summary": "",
        "note": "temporary lab smoke not run; no labels exported and no training run",
    }
    report = {
        "preview_only": True,
        "target_bus": target_bus,
        "safe_to_run_smoke": bool(inventory.get("safe_to_run_smoke", False)),
        "human_readiness_used": bool(human_readiness),
        "human_readiness_ready": bool(human_ready),
        "smoke_executed": False,
        "smoke_not_run_reason": reason,
        "source_slx_modified": False,
        "temporary_slx_committed": False,
        "formal_label_gate_changed": False,
        "v2_candidate_count_changed": False,
        "reranker_retrained": False,
        "gcn_trained": False,
        "labels_exported": False,
        "l12_touched": False,
        "summary_csv": _rel(out_dir / "ieee39_bus_fault_temp_lab_smoke_summary.csv"),
    }
    _write_outputs(out_dir, row, report)
    if human_readiness:
        readiness_report = {
            "target_bus": target_bus,
            "dry_run": bool(args.dry_run),
            "would_run_smoke_next_round": bool(args.dry_run and human_ready and safe),
            "actual_simulink_run": False,
            "source_slx_modified": False,
            "temporary_slx_committed": False,
            "labels_exported": False,
            "gcn_trained": False,
            "reranker_retrained": False,
            "formal_label_gate": human_readiness.get("formal_label_gate", "35 / 33 / 33"),
            "v2_candidate_count": human_readiness.get("v2_candidate_count", 40),
            "selected_fault_block_path": human_readiness.get("selected_fault_block_path", ""),
            "selected_injection_block_path": human_readiness.get("selected_injection_block_path", ""),
            "fault_start_s": human_readiness.get("fault_start_s"),
            "fault_clear_s": human_readiness.get("fault_clear_s"),
            "duration_s": human_readiness.get("duration_s"),
            "readiness_status": "ready_for_next_round_temp_smoke"
            if args.dry_run and human_ready and safe
            else "not_ready_for_next_round_temp_smoke",
            "recommended_next_step": "run actual B39 temporary smoke in a separate round"
            if args.dry_run and human_ready and safe
            else "fix readiness inputs before smoke",
            "manual_review_recommendation": manual_summary.get("recommendation", ""),
            "simulink_smoke_run": False,
            "smoke_success": False,
            "source_model_saved": False,
            "temporary_model_committed": False,
            "source_model_path": plan.get("source_model_path", ""),
            "temporary_model_path": temp_model,
            "note": "dry-run readiness only; no Simulink execution in this round",
        }
        _write_b39_readiness_outputs(out_dir, readiness_report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-lab-plan", type=Path, required=True)
    parser.add_argument("--matlab-inventory", type=Path)
    parser.add_argument("--manual-review-summary", type=Path)
    parser.add_argument("--human-readiness-json", type=Path)
    parser.add_argument("--target-bus", choices=["B39", "B26"])
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--simulation-stop-time", type=float, default=0.8)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    run(parse_args())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
