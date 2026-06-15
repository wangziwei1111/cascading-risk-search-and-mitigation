"""Run or skip IEEE39 bus-fault smoke candidates from a manifest.

The runner refuses source `.slx` modification and does not merge smoke results
into dynamic labels. If no scenario is currently runnable, it writes skipped
summary/report rows instead of forcing a Simulink run.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
    "ieee39_bus_fault_smoke_scenario_manifest.csv"
)
DEFAULT_OUTPUT_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/smoke_outputs"
BASE_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"
SUMMARY_CSV = BASE_DIR / "ieee39_bus_fault_smoke_test_summary.csv"
SUMMARY_JSON = BASE_DIR / "ieee39_bus_fault_smoke_test_summary.json"
REPORT_JSON = BASE_DIR / "ieee39_bus_fault_smoke_test_report.json"
REPORT_MD = BASE_DIR / "ieee39_bus_fault_smoke_test_report.md"

SUMMARY_FIELDS = [
    "scenario_id",
    "fault_type",
    "target_bus",
    "fault_start_s",
    "fault_clear_s",
    "duration_s",
    "injection_strategy",
    "uses_temporary_lab_copy",
    "source_slx_modified",
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
    "output_summary_path",
    "output_event_log_path",
    "note",
]


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _float_or_nan(value: Any) -> float:
    try:
        if value is None or str(value).strip() == "":
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _safe_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {row["scenario_id"]: row for row in csv.DictReader(f)}


def validate_selected(manifest: dict[str, dict[str, str]], scenario_ids: list[str]) -> list[dict[str, str]]:
    rows = []
    for scenario_id in scenario_ids:
        if scenario_id not in manifest:
            raise ValueError(f"Unknown scenario_id: {scenario_id}")
        row = manifest[scenario_id]
        text = json.dumps(row).lower()
        if "l12" in text:
            raise ValueError(f"{scenario_id} contains L12 and is forbidden.")
        if "handwired" in text or "line-trip" in text or "single_line_trip" in text:
            raise ValueError(f"{scenario_id} looks like a handwired line-trip scenario and is forbidden.")
        if _boolish(row.get("requires_source_slx_modification")):
            raise ValueError(f"{scenario_id} requires source .slx modification and is forbidden.")
        rows.append(row)
    return rows


def skipped_result(row: dict[str, str], output_dir: Path, reason: str) -> dict[str, Any]:
    scenario_dir = output_dir / row["scenario_id"]
    return {
        "scenario_id": row["scenario_id"],
        "fault_type": row["fault_type"],
        "target_bus": row["target_bus"],
        "fault_start_s": _float_or_nan(row["fault_start_s"]),
        "fault_clear_s": _float_or_nan(row["fault_clear_s"]),
        "duration_s": _float_or_nan(row["duration_s"]),
        "injection_strategy": row["injection_strategy"],
        "uses_temporary_lab_copy": _boolish(row.get("uses_temporary_lab_copy")),
        "source_slx_modified": False,
        "simulation_success": False,
        "physical_fault_or_breaker_action_executed": False,
        "measurement_extraction_status": "not_runnable_until_bus_injection_verified",
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
        "output_summary_path": _safe_rel(scenario_dir / "ieee39_bus_fault_smoke_summary.csv"),
        "output_event_log_path": _safe_rel(scenario_dir / "ieee39_bus_fault_event_log.csv"),
        "note": "skipped bus-fault smoke candidate only; no formal label merge and no reranker training",
    }


def write_summary(rows: list[dict[str, Any]]) -> None:
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    SUMMARY_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2, allow_nan=True) + "\n", encoding="utf-8")


def write_report(requested: list[str], runnable: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row["scenario_id"] for row in rows if row["training_ready_candidate_smoke"] is True]
    timeout = [row["scenario_id"] for row in rows if row["measurement_extraction_status"] == "simulation_timeout"]
    failed = [row["scenario_id"] for row in rows if row["scenario_id"] not in successful and row["scenario_id"] not in timeout]
    report = {
        "preview_only": True,
        "scenario_ids_requested": requested,
        "scenario_ids_runnable": runnable,
        "scenario_ids_completed": [row["scenario_id"] for row in rows],
        "scenario_ids_successful": successful,
        "scenario_ids_failed": failed,
        "scenario_ids_timeout": timeout,
        "num_successful_bus_fault_smoke_candidates": len(successful),
        "whether_source_slx_modified": False,
        "whether_formal_label_gate_changed": False,
        "whether_reranker_retrained": False,
        "whether_gcn_trained": False,
        "whether_l12_touched": False,
        "old_formal_gate": "35 / 33 / 33",
        "v2_candidate_count_unchanged": 40,
        "recommended_next_step": (
            "Verify a safe bus-fault injection point on a temporary lab copy before running bus-specific smoke tests."
            if not successful
            else "In a separate round, review successful bus-fault smoke rows before exporting candidate labels."
        ),
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# IEEE39 Bus-Fault Smoke-Test Report",
        "",
        "This report is preview-only. It is not a final dynamic performance conclusion.",
        "",
        f"- requested: {', '.join(requested)}",
        f"- runnable: {', '.join(runnable) if runnable else 'none'}",
        f"- successful: {', '.join(successful) if successful else 'none'}",
        f"- failed/skipped: {', '.join(failed) if failed else 'none'}",
        f"- timeout: {', '.join(timeout) if timeout else 'none'}",
        "- source `.slx` modified: false",
        "- formal label gate changed: false",
        "- reranker retrained: false",
        "- GCN trained: false",
        "- L12 touched: false",
        "",
        "The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct frequency. relay proxy / handwired breaker is not engineering-grade protection.",
        "",
        "Recommended next step:",
        "",
        report["recommended_next_step"],
    ]
    REPORT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def run(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_manifest(args.scenario_manifest)
    selected = validate_selected(manifest, args.scenario_ids)
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    runnable: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    for row in selected:
        scenario_dir = output_dir / row["scenario_id"]
        scenario_dir.mkdir(parents=True, exist_ok=True)
        if not _boolish(row.get("runnable_now")):
            rows.append(skipped_result(row, output_dir, "scenario runnable_now=false; safe bus injection point not verified"))
            continue
        if _boolish(row.get("uses_temporary_lab_copy")) and not args.allow_temporary_lab_copy:
            rows.append(skipped_result(row, output_dir, "temporary lab copy required but --allow-temporary-lab-copy was not set"))
            continue
        runnable.append(row)
        rows.append(skipped_result(row, output_dir, "runner intentionally has no source-slx bus-fault wiring implementation yet"))

    if args.dry_run:
        print("Dry-run only; no MATLAB/Simulink execution.")
        for row in selected:
            print(f"- {row['scenario_id']}: runnable_now={row.get('runnable_now')} target_bus={row.get('target_bus')}")

    write_summary(rows)
    return write_report(args.scenario_ids, [row["scenario_id"] for row in runnable], rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario-manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--scenario-ids", nargs="+", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--simulation-stop-time", type=float, default=0.8)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-temporary-lab-copy", action="store_true")
    return parser.parse_args()


def main() -> int:
    report = run(parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

