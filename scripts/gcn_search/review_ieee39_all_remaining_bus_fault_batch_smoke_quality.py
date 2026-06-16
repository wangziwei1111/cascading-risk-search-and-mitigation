"""Review IEEE39 all-remaining bus-fault batch smoke output quality.

This script is intentionally read-only with respect to Simulink models. It
only reads the previous-round smoke reports and writes quality-review artifacts
that state whether each bus can enter a later candidate-only label export
round. It does not run Simulink, export labels, train GCN, retrain the
reranker, or run a GCN usefulness audit.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BATCH_ID = "bus_fault_all_remaining_manual_wiring"
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
SMOKE_OUT = BASE / "batch_smoke_outputs"
DEFAULT_OUT = BASE / "batch_smoke_quality_review"
DOC_PATH = ROOT / "docs/ieee39_all_remaining_bus_fault_batch_smoke_quality_review.md"
OLD_FORMAL_GATE = "35 / 33 / 33"
CURRENT_CANDIDATE_COUNT = 42

NORMAL_BUSES = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
ALL_BUSES = NORMAL_BUSES + ["B16"]
METRIC_KEYS = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
]


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _safe_float(value: Any) -> float | None:
    if _is_finite(value):
        return float(value)
    return None


def _interpret_voltage(min_voltage: float | None, max_voltage: float | None) -> str:
    if min_voltage is None or max_voltage is None:
        return "voltage metrics are missing or non-finite"
    if min_voltage < 0.2:
        return "deep voltage depression is visible in compact phasor_RMS smoke output"
    if min_voltage < 0.8:
        return "voltage depression is visible in compact phasor_RMS smoke output"
    return "voltage response is measurable and finite in compact phasor_RMS smoke output"


def _interpret_frequency(min_frequency: float | None, max_frequency: float | None, has_proxy: bool) -> str:
    if not has_proxy:
        return "frequency proxy is missing"
    if min_frequency is None or max_frequency is None:
        return "frequency proxy metrics are missing or non-finite"
    return "frequency is represented by generator_speed_proxy, not direct frequency"


def _interpret_angle(angle: float | None) -> str:
    if angle is None:
        return "rotor-angle separation metric is missing or non-finite"
    return "rotor-angle separation is available as compact dynamic evidence"


def _review_bus(bus: str, smoke_summary: dict[str, Any]) -> dict[str, Any]:
    report_path = SMOKE_OUT / f"batch_smoke_{bus}_report.json"
    summary_path = SMOKE_OUT / f"batch_smoke_{bus}_summary.csv"
    failed_checks: list[str] = []
    warning_checks: list[str] = []

    if not report_path.exists():
        failed_checks.append("missing_source_smoke_report")
        report: dict[str, Any] = {}
    else:
        report = _read_json(report_path)

    if not summary_path.exists():
        failed_checks.append("missing_source_smoke_summary")

    signal_source = str(report.get("signal_source_summary", ""))
    has_frequency_proxy = "frequency=generator_speed_proxy" in signal_source
    metrics_all_finite = all(_is_finite(report.get(key)) for key in METRIC_KEYS)
    compact_available = report.get("measurement_extraction_status") == "voltage_speed_angle"
    special_handling = bool(report.get("special_handling", bus == "B16"))

    required_true = {
        "simulation_success": report.get("simulation_success") is True,
        "physical_fault_or_breaker_action_executed": report.get("physical_fault_or_breaker_action_executed") is True,
        "training_ready_candidate_smoke": report.get("training_ready_candidate_smoke") is True,
        "metrics_all_finite": metrics_all_finite,
        "signal_source_has_frequency_proxy": has_frequency_proxy,
        "compact_dynamic_measurement_available": compact_available,
    }
    required_false = {
        "source_slx_modified": report.get("source_slx_modified") is False,
        "temporary_slx_committed": report.get("temporary_slx_committed") is False,
        "labels_exported": report.get("labels_exported") is False,
        "candidate_label_exported": report.get("candidate_label_exported") is False,
        "gcn_trained": report.get("gcn_trained") is False,
        "reranker_retrained": report.get("reranker_retrained") is False,
        "gcn_usefulness_audit_run": report.get("gcn_usefulness_audit_run") is False,
    }
    for check, passed in {**required_true, **required_false}.items():
        if not passed:
            failed_checks.append(check)

    if report.get("measurement_extraction_status") != "voltage_speed_angle":
        failed_checks.append("measurement_extraction_status_not_voltage_speed_angle")
    if report.get("selected_fault_block_path") != f"Grid/Fault_{bus}_TEMP":
        failed_checks.append("selected_fault_block_path_mismatch")
    if bus == "B16" and special_handling is not True:
        failed_checks.append("b16_special_handling_not_preserved")

    if report.get("unstable_flag") is False:
        warning_checks.append("unstable_flag_false_low_risk_marker_only")

    quality_passed = not failed_checks
    min_voltage = _safe_float(report.get("min_voltage_pu"))
    max_voltage = _safe_float(report.get("max_voltage_pu"))
    min_frequency = _safe_float(report.get("min_frequency_hz"))
    max_frequency = _safe_float(report.get("max_frequency_hz"))
    angle = _safe_float(report.get("max_rotor_angle_separation_deg"))

    return {
        "batch_id": BATCH_ID,
        "target_bus": bus,
        "scenario_id": f"BF_{bus}_TEMP_SMOKE",
        "special_handling": special_handling,
        "quality_review_scope": "smoke_output_quality_only",
        "actual_simulink_run_this_round": False,
        "smoke_was_run_in_previous_round": True,
        "simulation_success": report.get("simulation_success") is True,
        "physical_fault_or_breaker_action_executed": report.get("physical_fault_or_breaker_action_executed") is True,
        "measurement_extraction_status": report.get("measurement_extraction_status", "missing_report"),
        "training_ready_candidate_smoke": report.get("training_ready_candidate_smoke") is True,
        "timeout_or_error_message": report.get("timeout_or_error_message", "missing_source_smoke_report" if not report else ""),
        "source_smoke_report_path": str(report_path.relative_to(ROOT)).replace("\\", "/"),
        "source_smoke_summary_path": str(summary_path.relative_to(ROOT)).replace("\\", "/"),
        "selected_fault_block_path": f"Grid/Fault_{bus}_TEMP",
        "fault_start_s": report.get("fault_start_s", 0.5),
        "fault_clear_s": report.get("fault_clear_s", 0.58),
        "duration_s": report.get("duration_s", 0.08),
        "min_voltage_pu": min_voltage,
        "max_voltage_pu": max_voltage,
        "min_frequency_hz": min_frequency,
        "max_frequency_hz": max_frequency,
        "max_speed_deviation": _safe_float(report.get("max_speed_deviation")),
        "max_rotor_angle_separation_deg": angle,
        "unstable_flag": report.get("unstable_flag"),
        "signal_source_summary": signal_source,
        "signal_source_has_frequency_proxy": has_frequency_proxy,
        "metrics_all_finite": metrics_all_finite,
        "compact_dynamic_measurement_available": compact_available,
        "voltage_response_interpretation": _interpret_voltage(min_voltage, max_voltage),
        "frequency_proxy_interpretation": _interpret_frequency(min_frequency, max_frequency, has_frequency_proxy),
        "rotor_angle_interpretation": _interpret_angle(angle),
        "unstable_flag_interpretation": "unstable_flag is a compact smoke threshold marker, not a final stability conclusion",
        "quality_review_passed_for_candidate_export": quality_passed,
        "candidate_export_eligible_next_round": quality_passed,
        "labels_exported": False,
        "candidate_label_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "source_slx_modified": False,
        "temporary_slx_committed": False,
        "old_formal_gate": smoke_summary.get("old_formal_gate", OLD_FORMAL_GATE),
        "current_candidate_count": smoke_summary.get("current_candidate_count", CURRENT_CANDIDATE_COUNT),
        "b39_b26_status": "existing_candidate_labels_not_formal",
        "b16_old_fault_not_moved": True if bus == "B16" else None,
        "failed_checks": sorted(set(failed_checks)),
        "warning_checks": warning_checks,
        "recommended_next_step": (
            "export candidate label in a separate round, without training"
            if quality_passed
            else "diagnose smoke quality issue before any label export"
        ),
    }


def _write_bus_md(path: Path, review: dict[str, Any]) -> None:
    failed = ", ".join(review["failed_checks"]) if review["failed_checks"] else "none"
    warnings = ", ".join(review["warning_checks"]) if review["warning_checks"] else "none"
    text = f"""# Smoke Quality Review: {review['target_bus']}

This is a smoke output quality review only. It did not run Simulink, did not
run actual smoke, did not export labels, did not train GCN, did not retrain the
reranker, and did not run a GCN usefulness audit.

- scenario: `{review['scenario_id']}`
- selected fault block: `{review['selected_fault_block_path']}`
- quality review passed for candidate export: `{review['quality_review_passed_for_candidate_export']}`
- candidate export eligible next round: `{review['candidate_export_eligible_next_round']}`
- measurement extraction status: `{review['measurement_extraction_status']}`
- metrics all finite: `{review['metrics_all_finite']}`
- signal source has frequency proxy: `{review['signal_source_has_frequency_proxy']}`
- unstable_flag: `{review['unstable_flag']}`
- failed checks: `{failed}`
- warning checks: `{warnings}`

The `unstable_flag` value is a compact smoke threshold marker, not a final
stability conclusion. `generator_speed_proxy` is not direct frequency, and the
model remains phasor_RMS, not EMT.
"""
    _write_text(path, text)


def _write_summary_csv(path: Path, reviews: list[dict[str, Any]]) -> None:
    fields = [
        "target_bus",
        "scenario_id",
        "quality_review_passed_for_candidate_export",
        "candidate_export_eligible_next_round",
        "simulation_success",
        "measurement_extraction_status",
        "metrics_all_finite",
        "signal_source_has_frequency_proxy",
        "unstable_flag",
        "min_voltage_pu",
        "max_frequency_hz",
        "max_rotor_angle_separation_deg",
        "failed_checks",
        "warning_checks",
        "recommended_next_step",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for review in reviews:
            row = {field: review.get(field) for field in fields}
            row["failed_checks"] = ";".join(review.get("failed_checks", []))
            row["warning_checks"] = ";".join(review.get("warning_checks", []))
            writer.writerow(row)


def _top_items(values: dict[str, float | None], reverse: bool, limit: int = 10) -> list[dict[str, Any]]:
    items = [(bus, value) for bus, value in values.items() if value is not None]
    items.sort(key=lambda item: item[1], reverse=reverse)
    return [{"bus": bus, "value": value} for bus, value in items[:limit]]


def _write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    eligible = ", ".join(summary["candidate_export_eligible_buses"]) or "none"
    blocked = ", ".join(summary["candidate_export_blocked_buses"]) or "none"
    unstable_false = ", ".join(summary["unstable_flag_false_buses"]) or "none"
    text = f"""# IEEE39 All-Remaining Bus-Fault Batch Smoke Quality Review

This round is batch smoke quality review. It did not run Simulink, did not run
actual smoke, did not export labels, did not train GCN, did not retrain the
reranker, and did not run a GCN usefulness audit.

## Result

- total smoke reports reviewed: `{summary['total_smoke_reports_reviewed']}`
- quality review passed: `{summary['num_quality_review_passed']}`
- quality review failed: `{summary['num_quality_review_failed']}`
- candidate export eligible next round: `{eligible}`
- blocked buses: `{blocked}`
- unstable_flag true count: `{summary['unstable_flag_true_count']}`
- unstable_flag false buses: `{unstable_false}`
- current candidate count remains: `{summary['current_candidate_count']}`
- old formal gate remains: `{summary['old_formal_gate']}`

Quality pass only means the bus can enter a later candidate-only export round.
The 37 new targets are still not candidate labels in this round. B39/B26 remain
existing candidate labels, not formal labels.

The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.
Post-fault compact dynamic measurements should not be used as main GCN inputs,
otherwise target-feature leakage can occur.

Recommended next step: `{summary['recommended_next_step']}`.
"""
    _write_text(path, text)


def _write_main_doc(summary: dict[str, Any]) -> None:
    eligible = ", ".join(summary["candidate_export_eligible_buses"]) or "none"
    blocked = ", ".join(summary["candidate_export_blocked_buses"]) or "none"
    unstable_false = ", ".join(summary["unstable_flag_false_buses"]) or "none"
    text = f"""# IEEE39 All-Remaining Bus-Fault Batch Smoke Quality Review

This round is a batch smoke quality review for the 37 IEEE39 bus-fault
temporary smoke outputs from the previous actual-smoke round.

## Boundary

- This round did not run Simulink.
- This round did not run actual smoke.
- This round did not export labels.
- This round did not train GCN.
- This round did not retrain the reranker.
- This round did not run a GCN usefulness audit.
- The 37 new targets are still not candidate labels.
- Quality pass only means a bus can enter candidate-only export in a separate
  later round.
- B16 special handling is preserved, and the old B16 fault was not moved.
- B39/B26 remain existing candidate labels, not formal labels.
- Current candidate count remains 42.
- Old formal gate remains 35 / 33 / 33.

## Quality Review Result

- total smoke reports reviewed: `{summary['total_smoke_reports_reviewed']}`
- quality review passed: `{summary['num_quality_review_passed']}`
- quality review failed: `{summary['num_quality_review_failed']}`
- candidate export eligible next round: `{eligible}`
- blocked buses: `{blocked}`
- unstable_flag true count: `{summary['unstable_flag_true_count']}`
- unstable_flag false buses: `{unstable_false}`
- B16 quality review passed: `{summary['special_b16_quality_review_passed']}`

`unstable_flag` is a compact smoke threshold marker, not a final stability
conclusion. `unstable_flag=false` does not mean the smoke quality failed; it
only means the compact threshold marker was lower for that bus.

The model is phasor_RMS, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.
Post-fault compact dynamic measurements cannot be used as main GCN inputs,
otherwise there is target-feature leakage risk.

## Next Step

If the project continues, the next round should do candidate-only export for
quality-passed buses, without training GCN and without retraining the reranker.
"""
    _write_text(DOC_PATH, text)


def run_review(output_dir: Path = DEFAULT_OUT) -> dict[str, Any]:
    smoke_summary = _read_json(SMOKE_OUT / "batch_actual_smoke_summary.json")
    _read_json(SMOKE_OUT / "buses_ready_for_smoke_quality_review.json")
    output_dir.mkdir(parents=True, exist_ok=True)

    reviews = [_review_bus(bus, smoke_summary) for bus in ALL_BUSES]
    for review in reviews:
        bus = review["target_bus"]
        _write_json(output_dir / f"smoke_quality_review_{bus}.json", review)
        _write_bus_md(output_dir / f"smoke_quality_review_{bus}.md", review)

    passed = [review["target_bus"] for review in reviews if review["quality_review_passed_for_candidate_export"]]
    failed = [review["target_bus"] for review in reviews if not review["quality_review_passed_for_candidate_export"]]
    failed_reasons = {review["target_bus"]: review["failed_checks"] for review in reviews if review["failed_checks"]}
    unstable_false = [review["target_bus"] for review in reviews if review.get("unstable_flag") is False]
    min_voltage = {review["target_bus"]: review.get("min_voltage_pu") for review in reviews}
    max_frequency = {review["target_bus"]: review.get("max_frequency_hz") for review in reviews}
    max_angle = {review["target_bus"]: review.get("max_rotor_angle_separation_deg") for review in reviews}
    status_counts = Counter(str(review.get("measurement_extraction_status")) for review in reviews)

    summary = {
        "batch_id": BATCH_ID,
        "quality_review_scope": "smoke_output_quality_only",
        "total_smoke_reports_reviewed": len(reviews),
        "num_quality_review_passed": len(passed),
        "num_quality_review_failed": len(failed),
        "quality_review_passed_buses": passed,
        "quality_review_failed_buses": failed,
        "failed_reasons_by_bus": failed_reasons,
        "candidate_export_eligible_buses": passed,
        "candidate_export_blocked_buses": failed,
        "unstable_flag_true_count": sum(1 for review in reviews if review.get("unstable_flag") is True),
        "unstable_flag_false_count": len(unstable_false),
        "unstable_flag_false_buses": unstable_false,
        "measurement_extraction_status_counts": dict(status_counts),
        "min_voltage_by_bus": min_voltage,
        "max_frequency_by_bus": max_frequency,
        "max_rotor_angle_separation_by_bus": max_angle,
        "lowest_voltage_buses_top10": _top_items(min_voltage, reverse=False),
        "highest_angle_separation_buses_top10": _top_items(max_angle, reverse=True),
        "special_b16_quality_review_passed": "B16" in passed,
        "b16_old_fault_not_moved": True,
        "actual_simulink_run_this_round": False,
        "smoke_was_run_in_previous_round": True,
        "labels_exported": False,
        "candidate_labels_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "current_candidate_count": CURRENT_CANDIDATE_COUNT,
        "old_formal_gate": OLD_FORMAL_GATE,
        "b39_b26_status": "existing_candidate_labels_not_formal",
        "should_export_labels_now": False,
        "should_train_now": False,
        "recommended_next_step": (
            "export candidate labels for quality-passed buses in a separate round, without training"
            if passed
            else "diagnose smoke quality issues before any label export"
        ),
    }

    _write_json(output_dir / "batch_smoke_quality_review_summary.json", summary)
    _write_summary_md(output_dir / "batch_smoke_quality_review_summary.md", summary)
    _write_summary_csv(output_dir / "batch_smoke_quality_review_summary.csv", reviews)
    _write_json(
        output_dir / "buses_eligible_for_candidate_export.json",
        {
            "batch_id": BATCH_ID,
            "eligible_buses": passed,
            "blocked_buses": failed,
            "eligible_count": len(passed),
            "blocked_count": len(failed),
            "criteria": {
                "quality_review_passed_for_candidate_export": True,
                "simulation_success": True,
                "measurement_extraction_status": "voltage_speed_angle",
                "metrics_all_finite": True,
                "signal_source_has_frequency_proxy": True,
            },
            "should_export_labels_now": False,
            "should_train_now": False,
            "next_round_export_scope": "candidate_only",
        },
    )
    _write_main_doc(summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", default="all", choices=["all"], help="Only all targets are supported for this batch.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if any quality review fails.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_review(args.output_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.strict and summary["num_quality_review_failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
