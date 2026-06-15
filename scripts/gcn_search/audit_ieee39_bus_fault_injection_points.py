"""Audit IEEE39 bus-fault injection feasibility and write smoke manifest.

This audit is intentionally conservative. It checks whether the existing
IEEE39 graphical wrapper exposes a safe target-bus selector for three-phase
bus faults. If not, it writes bus-fault smoke scenarios as not runnable yet,
instead of modifying source `.slx` models or pretending that a bus-specific
fault was executed.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"
MATLAB_DIR = ROOT / "matlab/simulink_ieee39"
THREE_PHASE_CONFIG = MATLAB_DIR / "configure_ieee39_three_phase_fault_case.m"
FAULT_SUITE = MATLAB_DIR / "run_ieee39_fault_test_suite.m"
FAULT_POINTS = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_fault_injection_points.csv"
LINE_MAP = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv"

MANIFEST_FIELDS = [
    "scenario_id",
    "fault_type",
    "target_bus",
    "fault_start_s",
    "fault_clear_s",
    "duration_s",
    "injection_strategy",
    "requires_source_slx_modification",
    "uses_temporary_lab_copy",
    "runnable_now",
    "expected_measurement_status",
    "expected_output_summary_path",
    "expected_event_log_path",
    "training_ready_candidate_rule",
    "notes",
]


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _script_capabilities() -> dict[str, bool]:
    config_text = _read(THREE_PHASE_CONFIG)
    suite_text = _read(FAULT_SUITE)
    combined = (config_text + "\n" + suite_text).lower()
    return {
        "three_phase_config_script_exists": THREE_PHASE_CONFIG.exists(),
        "fault_suite_script_exists": FAULT_SUITE.exists(),
        "existing_fault_block_timing_supported": all(
            token in config_text for token in ["faultStartS", "faultClearS", "fault_duration"]
        ),
        "existing_fault_suite_case_supported": "three_phase_fault_clear" in suite_text,
        "target_bus_selector_supported": any(
            token in combined for token in ["targetbus", "target_bus", "faultbus", "fault_bus", "busfault"]
        ),
        "fault_point_inventory_exists": FAULT_POINTS.exists(),
        "line_map_exists": LINE_MAP.exists(),
    }


def _candidate_bus_rows(capabilities: dict[str, bool]) -> list[dict[str, Any]]:
    preferred = [
        ("B16", "NF07 requested bus; connected to B15/B17/B24 and near previous L12 exclusion edge, so it needs extra care."),
        ("B39", "NF08 requested bus; high-number/reference-area bus and useful independent bus-fault candidate."),
        ("B21", "Alternative candidate connected to B16/B22; useful if B16 is unsafe."),
        ("B26", "Alternative mid/high-number bus connected to B25/B27/B28/B29."),
        ("B29", "Alternative high-number load-area bus connected to B26/B28."),
    ]
    rows: list[dict[str, Any]] = []
    selector = capabilities["target_bus_selector_supported"]
    for bus, reason in preferred:
        if selector:
            classification = "supported_without_slx_modification"
            runnable = True
            uses_copy = False
            risk = "target-bus selector appears available; still smoke-test only."
        else:
            classification = "requires_temporary_lab_copy"
            runnable = False
            uses_copy = True
            risk = "no safe script-level target-bus selector found; needs temporary lab copy or manual injection-point wiring."
        rows.append(
            {
                "target_bus": bus,
                "feasibility_classification": classification,
                "priority_reason": reason,
                "runnable_now": runnable,
                "requires_source_slx_modification": False,
                "uses_temporary_lab_copy": uses_copy,
                "risk": risk,
            }
        )
    return rows


def build_feasibility() -> dict[str, Any]:
    capabilities = _script_capabilities()
    candidates = _candidate_bus_rows(capabilities)
    runnable = [row["target_bus"] for row in candidates if row["runnable_now"]]
    return {
        "preview_only": True,
        "simulink_was_run": False,
        "source_slx_modified": False,
        "formal_label_gate_changed": False,
        "reranker_retrained": False,
        "gcn_trained": False,
        "l12_touched": False,
        "old_formal_gate": "35 / 33 / 33",
        "v2_candidate_count_unchanged": 40,
        "capabilities": capabilities,
        "candidate_buses": candidates,
        "priority_bus_fault_smoke_candidates": runnable,
        "requires_temporary_lab_copy": any(row["uses_temporary_lab_copy"] for row in candidates),
        "source_slx_modification_required": False,
        "highest_risks": [
            "The existing script can configure timing on the existing Fault (Three-Phase) block, but not select a different target bus.",
            "Bus-specific injection likely needs a temporary lab copy or manual Simulink wiring review.",
            "B16 is close to the known L12 excluded area; do not touch L12 or infer L12 labels.",
            "Do not commit source `.slx`, temporary lab `.slx`, Simulink cache, `.mat`, raw trajectories, or full timeseries.",
        ],
        "recommended_action": (
            "Do not run bus-fault smoke until a safe target-bus injection point is verified."
            if not runnable
            else "Run only the runnable bus-fault smoke candidates with timeout protection."
        ),
    }


def build_manifest(feasibility: dict[str, Any]) -> list[dict[str, Any]]:
    base = "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/smoke_outputs"
    selected = [
        ("BF01", "B16", "NF07 priority B16 three-phase bus fault smoke candidate."),
        ("BF02", "B39", "NF08 priority B39 three-phase bus fault smoke candidate."),
        ("BF03", "B21", "Alternative bus fault candidate because B16/B39 may require manual injection mapping."),
        ("BF04", "B26", "Alternative mid/high-number bus fault candidate; B29 remains next fallback."),
    ]
    by_bus = {row["target_bus"]: row for row in feasibility["candidate_buses"]}
    rows: list[dict[str, Any]] = []
    for scenario_id, bus, note in selected:
        candidate = by_bus[bus]
        rows.append(
            {
                "scenario_id": scenario_id,
                "fault_type": "three_phase_bus_fault_smoke",
                "target_bus": bus,
                "fault_start_s": 0.50,
                "fault_clear_s": 0.58,
                "duration_s": 0.08,
                "injection_strategy": candidate["feasibility_classification"],
                "requires_source_slx_modification": False,
                "uses_temporary_lab_copy": candidate["uses_temporary_lab_copy"],
                "runnable_now": candidate["runnable_now"],
                "expected_measurement_status": (
                    "voltage_speed_angle" if candidate["runnable_now"] else "not_runnable_until_bus_injection_verified"
                ),
                "expected_output_summary_path": f"{base}/{scenario_id}/ieee39_bus_fault_smoke_summary.csv",
                "expected_event_log_path": f"{base}/{scenario_id}/ieee39_bus_fault_event_log.csv",
                "training_ready_candidate_rule": (
                    "candidate smoke only after simulation_success=true, physical_fault_or_breaker_action_executed=true, "
                    "measurement_extraction_status=voltage_speed_angle, and signal_source_summary contains "
                    "frequency=generator_speed_proxy; do not merge into formal labels in this round"
                ),
                "notes": note + " " + candidate["risk"],
            }
        )
    return rows


def write_feasibility(feasibility: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "ieee39_bus_fault_injection_feasibility.json", feasibility)
    lines = [
        "# IEEE39 Bus-Fault Injection Feasibility",
        "",
        "This audit does not run Simulink, does not modify `.slx`, does not fix L12, does not train GCN, and does not retrain the reranker.",
        "",
        f"- old formal gate: `{feasibility['old_formal_gate']}`",
        f"- v2 candidate count unchanged: `{feasibility['v2_candidate_count_unchanged']}`",
        f"- target-bus selector supported: `{feasibility['capabilities']['target_bus_selector_supported']}`",
        f"- source `.slx` modification required: `{feasibility['source_slx_modification_required']}`",
        f"- temporary lab copy needed: `{feasibility['requires_temporary_lab_copy']}`",
        "",
        "## Candidate Bus Classification",
        "",
        "| target_bus | classification | runnable_now | uses_temporary_lab_copy | reason |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in feasibility["candidate_buses"]:
        lines.append(
            f"| {row['target_bus']} | {row['feasibility_classification']} | {row['runnable_now']} | "
            f"{row['uses_temporary_lab_copy']} | {row['priority_reason']} |"
        )
    lines += [
        "",
        "## Key Boundaries",
        "",
        "- B16/B39 are priority smoke candidates, but they are not executable until a safe bus injection point is verified.",
        "- L12 remains excluded because it is a timeout / suspected islanding special case.",
        "- Source `.slx` files are not committed because this round is a smoke feasibility step and source model licensing / physical wiring must stay untouched.",
        "- The model remains phasor_RMS, not EMT.",
        "- `generator_speed_proxy` is not direct frequency.",
        "- relay proxy / handwired breaker is not engineering-grade protection.",
        "- Bus-fault smoke candidates are not formal labels.",
        "",
        "## Recommended Action",
        "",
        str(feasibility["recommended_action"]),
    ]
    (OUT_DIR / "ieee39_bus_fault_injection_feasibility.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(rows: list[dict[str, Any]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "ieee39_bus_fault_smoke_scenario_manifest.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    _write_json(OUT_DIR / "ieee39_bus_fault_smoke_scenario_manifest.json", rows)


def main() -> int:
    feasibility = build_feasibility()
    rows = build_manifest(feasibility)
    write_feasibility(feasibility)
    write_manifest(rows)
    print(
        json.dumps(
            {
                "feasibility": str(OUT_DIR / "ieee39_bus_fault_injection_feasibility.json"),
                "manifest": str(OUT_DIR / "ieee39_bus_fault_smoke_scenario_manifest.csv"),
                "runnable_now": [row["scenario_id"] for row in rows if row["runnable_now"]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

