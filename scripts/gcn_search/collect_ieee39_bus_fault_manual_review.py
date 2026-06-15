"""Collect a manual IEEE39 bus-fault injection review into a safe summary.

This script intentionally does not modify MATLAB inventory files, does not run
Simulink, and does not export labels. It only consolidates a human-filled JSON
review template and writes a conservative recommendation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = [
    "target_bus",
    "reviewer",
    "review_date",
    "temp_model_path",
    "source_model_opened_read_only",
    "source_model_saved",
    "temporary_model_saved",
    "temporary_model_committed",
    "candidate_blocks_reviewed",
    "selected_injection_block_path",
    "selected_injection_port_description",
    "selected_fault_block_path",
    "fault_block_connected_in_parallel",
    "original_network_connection_preserved",
    "no_unintended_bypass",
    "no_floating_ports",
    "no_unintended_islanding",
    "update_diagram_attempted",
    "update_diagram_success",
    "update_diagram_error",
    "fault_start_s",
    "fault_clear_s",
    "duration_s",
    "measurement_signals_expected_available",
    "human_verified_injection_point",
    "safe_to_run_smoke_recommendation",
    "reviewer_notes",
    "screenshots_or_manual_evidence_paths",
    "next_action",
]


SAFETY_TRUE_FIELDS = [
    "source_model_opened_read_only",
    "fault_block_connected_in_parallel",
    "original_network_connection_preserved",
    "no_unintended_bypass",
    "no_floating_ports",
    "no_unintended_islanding",
    "update_diagram_attempted",
    "update_diagram_success",
    "measurement_signals_expected_available",
    "human_verified_injection_point",
    "safe_to_run_smoke_recommendation",
]


SAFETY_FALSE_FIELDS = [
    "source_model_saved",
    "temporary_model_committed",
]


def _load_review(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("review JSON must contain an object")
    return payload


def _recommendation(review: dict[str, Any]) -> tuple[str, list[str]]:
    missing = [field for field in REQUIRED_FIELDS if field not in review]
    failed: list[str] = []
    if missing:
        failed.extend(f"missing:{field}" for field in missing)

    for field in SAFETY_TRUE_FIELDS:
        if review.get(field) is not True:
            failed.append(f"{field}=not_true")
    for field in SAFETY_FALSE_FIELDS:
        if review.get(field) is not False:
            failed.append(f"{field}=not_false")

    if not review.get("selected_injection_block_path"):
        failed.append("selected_injection_block_path=empty")
    if not review.get("selected_injection_port_description"):
        failed.append("selected_injection_port_description=empty")
    if not review.get("selected_fault_block_path"):
        failed.append("selected_fault_block_path=empty")
    if not review.get("screenshots_or_manual_evidence_paths"):
        failed.append("screenshots_or_manual_evidence_paths=empty")

    if failed:
        return "do_not_run_smoke", failed
    return "manual_review_supports_next_round_inventory_update", []


def _write_outputs(review: dict[str, Any], output_dir: Path, review_json: Path) -> dict[str, Any]:
    recommendation, failed_checks = _recommendation(review)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "preview_only": True,
        "review_json": str(review_json.as_posix()),
        "target_bus": review.get("target_bus"),
        "recommendation": recommendation,
        "failed_checks": failed_checks,
        "human_verified_injection_point": bool(review.get("human_verified_injection_point")),
        "safe_to_run_smoke_recommendation": bool(review.get("safe_to_run_smoke_recommendation")),
        "source_model_saved": bool(review.get("source_model_saved")),
        "temporary_model_committed": bool(review.get("temporary_model_committed")),
        "inventory_modified": False,
        "simulink_run": False,
        "labels_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "formal_label_gate": "35 / 33 / 33",
        "v2_candidate_count": 40,
        "next_action": (
            "manual review required before smoke"
            if recommendation == "do_not_run_smoke"
            else "update inventory in a separate round before any temporary smoke"
        ),
    }

    json_path = output_dir / "manual_review_consolidation_summary.json"
    md_path = output_dir / "manual_review_consolidation_summary.md"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    failed_text = "\n".join(f"- {item}" for item in failed_checks) if failed_checks else "- none"
    md_path.write_text(
        "\n".join(
            [
                "# Manual Bus-Fault Review Consolidation",
                "",
                f"- target_bus: `{summary['target_bus']}`",
                f"- recommendation: `{summary['recommendation']}`",
                f"- human_verified_injection_point: `{str(summary['human_verified_injection_point']).lower()}`",
                f"- safe_to_run_smoke_recommendation: `{str(summary['safe_to_run_smoke_recommendation']).lower()}`",
                f"- simulink_run: `{str(summary['simulink_run']).lower()}`",
                f"- inventory_modified: `{str(summary['inventory_modified']).lower()}`",
                f"- labels_exported: `{str(summary['labels_exported']).lower()}`",
                f"- gcn_trained: `{str(summary['gcn_trained']).lower()}`",
                f"- reranker_retrained: `{str(summary['reranker_retrained']).lower()}`",
                f"- formal_label_gate: `{summary['formal_label_gate']}`",
                f"- v2_candidate_count: `{summary['v2_candidate_count']}`",
                "",
                "## Failed Checks",
                "",
                failed_text,
                "",
                "This consolidation does not run Simulink, does not modify `.slx`, does not export labels, and does not train.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    review = _load_review(args.review_json)
    summary = _write_outputs(review, args.output_dir, args.review_json)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
