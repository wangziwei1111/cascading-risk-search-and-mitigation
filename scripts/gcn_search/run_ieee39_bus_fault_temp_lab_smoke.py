"""Run a temp-lab bus-fault smoke only when MATLAB inventory marks it safe."""

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


def run(args: argparse.Namespace) -> dict[str, Any]:
    plan = _read(args.temp_lab_plan)
    inventory = _read(args.matlab_inventory)
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    target_bus = str(plan["target_bus"])
    temp_model = str(plan["temporary_model_path"])
    reason = ""
    safe = bool(inventory.get("safe_to_run_smoke", False))
    if target_bus not in {"B39", "B26"}:
        reason = "target_bus is not allowed in this round"
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
        reason = "dry-run only"
        safe = False
    else:
        reason = "safe_to_run_smoke=true, but execution is intentionally not implemented until wiring is reviewed"
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
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-lab-plan", type=Path, required=True)
    parser.add_argument("--matlab-inventory", type=Path, required=True)
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

