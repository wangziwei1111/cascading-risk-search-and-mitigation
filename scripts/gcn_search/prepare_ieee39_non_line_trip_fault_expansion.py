"""Prepare IEEE39 non-line-trip dynamic fault expansion artifacts.

This script is intentionally a dry-run planner. It audits existing MATLAB and
Python entrypoints, writes a taxonomy, writes a first-batch scenario manifest,
and emits dry-run commands. It does not run Simulink and does not modify .slx
models.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion"

THREE_PHASE_CONFIG = ROOT / "matlab/simulink_ieee39/configure_ieee39_three_phase_fault_case.m"
FAULT_SUITE = ROOT / "matlab/simulink_ieee39/run_ieee39_fault_test_suite.m"
WRAPPER_MODEL = (
    "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/"
    "IEEE39BusSystem_dynamic_experiment_wrapper.slx"
)
FAULT_TEST_DIR = "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests"


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def audit_capabilities() -> dict[str, object]:
    config_text = _read(THREE_PHASE_CONFIG)
    suite_text = _read(FAULT_SUITE)
    has_three_phase_config = THREE_PHASE_CONFIG.exists()
    has_fault_suite = FAULT_SUITE.exists()
    has_fault_timing = all(token in config_text for token in ["faultStartS", "faultClearS", "fault_duration"])
    has_suite_three_phase_case = "three_phase_fault_clear" in suite_text
    has_relay_proxy_case = "relay_trip_test" in suite_text and "basic_relay_proxy" in suite_text
    has_generic_bus_selection = any(
        token in (config_text + suite_text)
        for token in ["faultBus", "fault_bus", "targetBus", "target_bus", "busFault"]
    )
    has_load_step = any(token in (config_text + suite_text).lower() for token in ["load_step", "load step"])
    has_generator_trip = any(
        token in (config_text + suite_text).lower()
        for token in ["generator_trip", "mechanical_power", "mechanical power", "pm_step"]
    )
    return {
        "simulink_was_run": False,
        "slx_modified": False,
        "three_phase_fault_block_script_supported": bool(has_three_phase_config),
        "fault_start_clear_parameterization_supported": bool(has_fault_timing),
        "fault_suite_three_phase_case_supported": bool(has_fault_suite and has_suite_three_phase_case),
        "different_bus_three_phase_fault_supported_without_slx_change": bool(has_generic_bus_selection),
        "relay_proxy_fault_supported_without_slx_change": bool(has_relay_proxy_case),
        "load_step_supported_without_slx_change": bool(has_load_step),
        "generator_trip_supported_without_slx_change": bool(has_generator_trip),
        "bus_voltage_reference_event_supported_without_slx_change": False,
        "notes": [
            "Existing scripts can configure an existing Fault (Three-Phase) block start/clear timing.",
            "The current fault suite has a fixed three_phase_fault_clear row and a basic relay proxy row.",
            "No generic target-bus selector for the three-phase fault was found in the current scripts.",
            "Load-step, generator-trip, and bus-voltage-reference events require manual Simulink/MATLAB extension before execution.",
        ],
    }


def taxonomy(capabilities: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "fault_type": "three_phase_bus_fault_clear",
            "description": "Use the existing Simscape Fault (Three-Phase) block and clear it after a short duration.",
            "requires_slx_modification": False,
            "runnable_with_existing_scripts": bool(capabilities["fault_suite_three_phase_case_supported"]),
            "expected_measurements": ["min_voltage_pu", "generator_speed_proxy", "max_speed_deviation", "max_rotor_angle_separation_deg"],
            "expected_training_ready_gate": "simulation_success=true, physical_fault_or_breaker_action_executed=true, measurement_extraction_status=voltage_speed_angle",
            "risks": ["current suite uses the existing fault block location", "different target buses are not yet parameterized"],
            "recommended_first_batch": True,
        },
        {
            "fault_type": "fault_duration_sweep",
            "description": "Vary fault_clear_s while keeping fault_start_s fixed to test sensitivity to clearing time.",
            "requires_slx_modification": False,
            "runnable_with_existing_scripts": bool(capabilities["fault_start_clear_parameterization_supported"]),
            "expected_measurements": ["voltage sag depth", "generator_speed_proxy excursion", "rotor-angle separation"],
            "expected_training_ready_gate": "same as three_phase_bus_fault_clear, with duration recorded and no line-trip label mixing",
            "risks": ["run_ieee39_fault_test_suite has a fixed three_phase_fault_clear row, so duration sweeps should use a dedicated smoke wrapper before label export"],
            "recommended_first_batch": True,
        },
        {
            "fault_type": "relay_proxy_fault",
            "description": "Use the existing basic relay proxy case as a non-engineering-grade relay-like disturbance.",
            "requires_slx_modification": False,
            "runnable_with_existing_scripts": bool(capabilities["relay_proxy_fault_supported_without_slx_change"]),
            "expected_measurements": ["relay_operated", "trip_time_s", "voltage_speed_angle compact signals"],
            "expected_training_ready_gate": "relay proxy row is separated from handwired line-trip labels and marked basic proxy",
            "risks": ["proxy is not engineering-grade protection coordination"],
            "recommended_first_batch": True,
        },
        {
            "fault_type": "load_step_disturbance",
            "description": "Apply a small load increase/decrease at a selected bus.",
            "requires_slx_modification": True,
            "runnable_with_existing_scripts": bool(capabilities["load_step_supported_without_slx_change"]),
            "expected_measurements": ["voltage recovery", "generator_speed_proxy deviation", "rotor-angle response"],
            "expected_training_ready_gate": "manual_required until load-step parameter and measurement export are added",
            "risks": ["manual Simulink change needed", "load step magnitude can create label leakage if encoded as target-like feature"],
            "recommended_first_batch": False,
        },
        {
            "fault_type": "generator_trip_or_mechanical_power_step",
            "description": "Trip a generator or perturb its mechanical power input.",
            "requires_slx_modification": True,
            "runnable_with_existing_scripts": bool(capabilities["generator_trip_supported_without_slx_change"]),
            "expected_measurements": ["generator_speed_proxy response", "rotor-angle separation", "voltage recovery"],
            "expected_training_ready_gate": "manual_required until generator control input is verified",
            "risks": ["model-specific generator internals", "not all generator blocks expose safe trip or Pm inputs"],
            "recommended_first_batch": False,
        },
        {
            "fault_type": "bus_voltage_disturbance_or_reference_event",
            "description": "Perturb a voltage reference or bus voltage disturbance input if a safe model input exists.",
            "requires_slx_modification": True,
            "runnable_with_existing_scripts": bool(capabilities["bus_voltage_reference_event_supported_without_slx_change"]),
            "expected_measurements": ["voltage nadir", "speed proxy", "rotor-angle separation"],
            "expected_training_ready_gate": "manual_required until a safe disturbance injection point is mapped",
            "risks": ["may not exist in the compact model", "can be confused with measurement target leakage"],
            "recommended_first_batch": False,
        },
    ]


def manifest(capabilities: dict[str, object]) -> list[dict[str, object]]:
    base = "results/gcn_search/ieee39_dynamic_fault_type_expansion/smoke_outputs"
    duration_supported = bool(capabilities["fault_start_clear_parameterization_supported"])
    suite_supported = bool(capabilities["fault_suite_three_phase_case_supported"])
    relay_supported = bool(capabilities["relay_proxy_fault_supported_without_slx_change"])
    rows = [
        {
            "scenario_id": "NF01",
            "fault_type": "three_phase_bus_fault_clear",
            "target_bus_or_component": "existing_fault_block_location",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.60,
            "duration_s": 0.10,
            "requires_slx_modification": False,
            "runnable_with_existing_scripts": suite_supported,
            "script_or_function_entrypoint": "run_ieee39_fault_test_suite selectedCases=[three_phase_fault_clear]",
            "expected_output_summary_path": f"{base}/NF01/ieee39_fault_test_summary.csv",
            "expected_event_log_path": f"{base}/NF01/ieee39_event_log.csv",
            "expected_measurement_status": "voltage_speed_angle",
            "training_ready_candidate_rule": "keep as non_line_trip; do not merge into handwired line-trip labels",
            "notes": "Existing baseline three-phase fault-clear case.",
        },
        {
            "scenario_id": "NF02",
            "fault_type": "fault_duration_sweep",
            "target_bus_or_component": "existing_fault_block_location",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.55,
            "duration_s": 0.05,
            "requires_slx_modification": False,
            "runnable_with_existing_scripts": duration_supported,
            "script_or_function_entrypoint": "configure_ieee39_three_phase_fault_case faultStartS=0.50 faultClearS=0.55",
            "expected_output_summary_path": f"{base}/NF02/ieee39_three_phase_fault_case_config.json",
            "expected_event_log_path": "not_applicable_until_smoke_runner_added",
            "expected_measurement_status": "voltage_speed_angle_after_smoke_run",
            "training_ready_candidate_rule": "candidate only after a dedicated duration-aware smoke run succeeds",
            "notes": "Duration parameter is configurable; suite-grade summary requires a duration-aware smoke wrapper.",
        },
        {
            "scenario_id": "NF03",
            "fault_type": "fault_duration_sweep",
            "target_bus_or_component": "existing_fault_block_location",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.58,
            "duration_s": 0.08,
            "requires_slx_modification": False,
            "runnable_with_existing_scripts": duration_supported,
            "script_or_function_entrypoint": "configure_ieee39_three_phase_fault_case faultStartS=0.50 faultClearS=0.58",
            "expected_output_summary_path": f"{base}/NF03/ieee39_three_phase_fault_case_config.json",
            "expected_event_log_path": "not_applicable_until_smoke_runner_added",
            "expected_measurement_status": "voltage_speed_angle_after_smoke_run",
            "training_ready_candidate_rule": "candidate only after a dedicated duration-aware smoke run succeeds",
            "notes": "Intermediate clearing-time sweep point.",
        },
        {
            "scenario_id": "NF04",
            "fault_type": "fault_duration_sweep",
            "target_bus_or_component": "existing_fault_block_location",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.60,
            "duration_s": 0.10,
            "requires_slx_modification": False,
            "runnable_with_existing_scripts": duration_supported,
            "script_or_function_entrypoint": "configure_ieee39_three_phase_fault_case faultStartS=0.50 faultClearS=0.60",
            "expected_output_summary_path": f"{base}/NF04/ieee39_three_phase_fault_case_config.json",
            "expected_event_log_path": "not_applicable_until_smoke_runner_added",
            "expected_measurement_status": "voltage_speed_angle_after_smoke_run",
            "training_ready_candidate_rule": "candidate only after a dedicated duration-aware smoke run succeeds",
            "notes": "Matches the current baseline duration.",
        },
        {
            "scenario_id": "NF05",
            "fault_type": "fault_duration_sweep",
            "target_bus_or_component": "existing_fault_block_location",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.65,
            "duration_s": 0.15,
            "requires_slx_modification": False,
            "runnable_with_existing_scripts": duration_supported,
            "script_or_function_entrypoint": "configure_ieee39_three_phase_fault_case faultStartS=0.50 faultClearS=0.65",
            "expected_output_summary_path": f"{base}/NF05/ieee39_three_phase_fault_case_config.json",
            "expected_event_log_path": "not_applicable_until_smoke_runner_added",
            "expected_measurement_status": "voltage_speed_angle_after_smoke_run",
            "training_ready_candidate_rule": "candidate only after a dedicated duration-aware smoke run succeeds",
            "notes": "Longer clearing-time sweep point; use tiny timeout-capable smoke first.",
        },
        {
            "scenario_id": "NF06",
            "fault_type": "relay_proxy_fault",
            "target_bus_or_component": "basic_relay_proxy_on_mapped_L01",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.60,
            "duration_s": 0.10,
            "requires_slx_modification": False,
            "runnable_with_existing_scripts": relay_supported,
            "script_or_function_entrypoint": "run_ieee39_fault_test_suite selectedCases=[relay_trip_test]",
            "expected_output_summary_path": f"{base}/NF06/ieee39_fault_test_summary.csv",
            "expected_event_log_path": f"{base}/NF06/ieee39_event_log.csv",
            "expected_measurement_status": "voltage_speed_angle",
            "training_ready_candidate_rule": "keep as relay_proxy_fault; do not count as handwired line-trip label",
            "notes": "Proxy relay case only; not engineering-grade protection.",
        },
        {
            "scenario_id": "NF07",
            "fault_type": "three_phase_bus_fault_clear",
            "target_bus_or_component": "B16_future_bus_fault_point",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.60,
            "duration_s": 0.10,
            "requires_slx_modification": True,
            "runnable_with_existing_scripts": False,
            "script_or_function_entrypoint": "manual_required: map/select a B16 three-phase fault injection point",
            "expected_output_summary_path": f"{base}/NF07/ieee39_fault_test_summary.csv",
            "expected_event_log_path": f"{base}/NF07/ieee39_event_log.csv",
            "expected_measurement_status": "manual_required",
            "training_ready_candidate_rule": "not candidate until bus-specific fault injection is verified",
            "notes": "Bus sweep is useful, but current scripts do not expose a target-bus selector.",
        },
        {
            "scenario_id": "NF08",
            "fault_type": "three_phase_bus_fault_clear",
            "target_bus_or_component": "B39_future_bus_fault_point",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.60,
            "duration_s": 0.10,
            "requires_slx_modification": True,
            "runnable_with_existing_scripts": False,
            "script_or_function_entrypoint": "manual_required: map/select a B39 three-phase fault injection point",
            "expected_output_summary_path": f"{base}/NF08/ieee39_fault_test_summary.csv",
            "expected_event_log_path": f"{base}/NF08/ieee39_event_log.csv",
            "expected_measurement_status": "manual_required",
            "training_ready_candidate_rule": "not candidate until bus-specific fault injection is verified",
            "notes": "Future bus-sweep point; kept out of current labels.",
        },
        {
            "scenario_id": "NF09",
            "fault_type": "load_step_disturbance",
            "target_bus_or_component": "B16_load_future",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.00,
            "duration_s": 0.00,
            "requires_slx_modification": True,
            "runnable_with_existing_scripts": False,
            "script_or_function_entrypoint": "manual_required: add safe load-step disturbance input",
            "expected_output_summary_path": f"{base}/NF09/ieee39_fault_test_summary.csv",
            "expected_event_log_path": f"{base}/NF09/ieee39_event_log.csv",
            "expected_measurement_status": "manual_required",
            "training_ready_candidate_rule": "not candidate until load-step input and quality gate are implemented",
            "notes": "Useful generalization case; future manual extension.",
        },
        {
            "scenario_id": "NF10",
            "fault_type": "generator_trip_or_mechanical_power_step",
            "target_bus_or_component": "Gen39_future",
            "fault_start_s": 0.50,
            "fault_clear_s": 0.00,
            "duration_s": 0.00,
            "requires_slx_modification": True,
            "runnable_with_existing_scripts": False,
            "script_or_function_entrypoint": "manual_required: verify generator trip or Pm-step input",
            "expected_output_summary_path": f"{base}/NF10/ieee39_fault_test_summary.csv",
            "expected_event_log_path": f"{base}/NF10/ieee39_event_log.csv",
            "expected_measurement_status": "manual_required",
            "training_ready_candidate_rule": "not candidate until generator event is verified",
            "notes": "Future generator disturbance; do not mix with line-trip labels.",
        },
    ]
    return rows


def validate_manifest(rows: list[dict[str, object]]) -> None:
    ids = [str(row["scenario_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("scenario_id values must be unique")
    text = json.dumps(rows, ensure_ascii=False).lower()
    if "l12" in text:
        raise ValueError("L12 must not appear in the non-line-trip first-batch manifest")
    if "handwired_timed_breaker" in text:
        raise ValueError("Handwired line-trip scenarios must not appear in this manifest")


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_taxonomy_md(path: Path, rows: list[dict[str, object]], capabilities: dict[str, object]) -> None:
    lines = [
        "# IEEE39 Non-Line-Trip Fault Taxonomy",
        "",
        "This file prepares additional IEEE39 dynamic-label fault types without running Simulink or modifying `.slx` files.",
        "",
        "Current audit:",
        f"- existing three-phase fault script: `{capabilities['three_phase_fault_block_script_supported']}`",
        f"- fault_start_s / fault_clear_s parameterization: `{capabilities['fault_start_clear_parameterization_supported']}`",
        f"- different bus fault selector without `.slx` change: `{capabilities['different_bus_three_phase_fault_supported_without_slx_change']}`",
        f"- load-step support without `.slx` change: `{capabilities['load_step_supported_without_slx_change']}`",
        f"- generator-trip / mechanical-power-step support without `.slx` change: `{capabilities['generator_trip_supported_without_slx_change']}`",
        "",
        "| fault_type | requires_slx_modification | runnable_with_existing_scripts | recommended_first_batch | description |",
        "|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['fault_type']}` | {row['requires_slx_modification']} | "
            f"{row['runnable_with_existing_scripts']} | {row['recommended_first_batch']} | {row['description']} |"
        )
    lines.extend(
        [
            "",
            "Boundaries:",
            "- This preparation does not create new training-ready labels.",
            "- This preparation does not run Simulink.",
            "- This preparation does not modify `.slx` files or Simscape physical wiring.",
            "- L12 remains excluded and is not fixed here.",
            "- The model remains `phasor_RMS`, not EMT.",
            "- `generator_speed_proxy` is not direct frequency.",
            "- The handwired breaker workflow is pilot breaker-like validation, not engineering-grade protection.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_feasibility(path_json: Path, path_md: Path, capabilities: dict[str, object], rows: list[dict[str, object]]) -> None:
    supported_now = [
        "three_phase_bus_fault_clear baseline through run_ieee39_fault_test_suite",
        "fault_duration_sweep timing configuration through configure_ieee39_three_phase_fault_case",
        "relay_proxy_fault baseline through run_ieee39_fault_test_suite relay_trip_test",
    ]
    manual_future = [
        "different-bus three-phase fault selector",
        "load_step_disturbance",
        "generator_trip_or_mechanical_power_step",
        "bus_voltage_disturbance_or_reference_event",
    ]
    recommended = [row["scenario_id"] for row in rows if row["scenario_id"] in {"NF01", "NF02", "NF03", "NF04", "NF06"}]
    payload = {
        "simulink_was_run": False,
        "slx_modified": False,
        "training_ready_label_count_changed": False,
        "reranker_retrained": False,
        "supported_without_slx_modification_now": supported_now,
        "manual_or_future_fault_types": manual_future,
        "first_smoke_test_candidates": recommended,
        "largest_risks": [
            "target-feature leakage if compact dynamic measurements are reused as both features and proxy labels",
            "mixing non-line-trip labels with handwired line-trip labels",
            "bus-specific fault injection requires manual mapping",
            "duration sweep must not be reported as suite-grade until a duration-aware smoke runner is used",
        ],
        "mixes_with_handwired_line_trip_labels": False,
        "target_feature_leakage_possible": True,
        "capability_audit": capabilities,
    }
    write_json(path_json, payload)
    lines = [
        "# IEEE39 Non-Line-Trip Fault Expansion Feasibility Report",
        "",
        "## What Can Run Without `.slx` Changes Now",
        "",
    ]
    lines.extend(f"- {item}" for item in supported_now)
    lines.extend(
        [
            "",
            "## Manual Or Future Work",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in manual_future)
    lines.extend(
        [
            "",
            "## First Smoke-Test Candidates",
            "",
            ", ".join(recommended),
            "",
            "## Risks",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["largest_risks"])
    lines.extend(
        [
            "",
            "## Label Boundary",
            "",
            "These scenarios do not mix with the handwired line-trip labels. They are an expansion plan only, not new training-ready labels. No Simulink run was executed, no `.slx` was modified, no L12 fix was attempted, and no dynamic-aware reranker was retrained.",
        ]
    )
    path_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_dry_run_commands(path: Path, rows: list[dict[str, object]]) -> None:
    lines = [
        "# Dry-run command plan only. Do not execute automatically.",
        "# cd C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39",
        "",
    ]
    for row in rows:
        scenario_id = row["scenario_id"]
        if row["runnable_with_existing_scripts"] is True and row["fault_type"] == "three_phase_bus_fault_clear":
            lines.append(
                f"% {scenario_id}: run_ieee39_fault_test_suite(\"{WRAPPER_MODEL}\", "
                f"\"../../results/gcn_search/ieee39_dynamic_fault_type_expansion/smoke_outputs/{scenario_id}\", "
                "true, [\"three_phase_fault_clear\"], 0.8, false)"
            )
        elif row["runnable_with_existing_scripts"] is True and row["fault_type"] == "fault_duration_sweep":
            lines.append(
                f"% {scenario_id}: configure_ieee39_three_phase_fault_case(\"{WRAPPER_MODEL}\", "
                f"{row['fault_start_s']}, {row['fault_clear_s']}, "
                f"\"../../results/gcn_search/ieee39_dynamic_fault_type_expansion/smoke_outputs/{scenario_id}\")"
            )
        elif row["runnable_with_existing_scripts"] is True and row["fault_type"] == "relay_proxy_fault":
            lines.append(
                f"% {scenario_id}: run_ieee39_fault_test_suite(\"{WRAPPER_MODEL}\", "
                f"\"../../results/gcn_search/ieee39_dynamic_fault_type_expansion/smoke_outputs/{scenario_id}\", "
                "true, [\"relay_trip_test\"], 0.8, false)"
            )
        else:
            lines.append(f"% {scenario_id}: manual_required before execution - {row['script_or_function_entrypoint']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    capabilities = audit_capabilities()
    tax = taxonomy(capabilities)
    rows = manifest(capabilities)
    validate_manifest(rows)

    write_json(OUT_DIR / "ieee39_non_line_trip_fault_taxonomy.json", tax)
    write_taxonomy_md(OUT_DIR / "ieee39_non_line_trip_fault_taxonomy.md", tax, capabilities)
    write_csv(OUT_DIR / "ieee39_non_line_trip_scenario_manifest.csv", rows)
    write_json(OUT_DIR / "ieee39_non_line_trip_scenario_manifest.json", rows)
    write_feasibility(
        OUT_DIR / "ieee39_non_line_trip_feasibility_report.json",
        OUT_DIR / "ieee39_non_line_trip_feasibility_report.md",
        capabilities,
        rows,
    )
    write_dry_run_commands(OUT_DIR / "ieee39_non_line_trip_dry_run_commands.txt", rows)
    print(f"Wrote IEEE39 non-line-trip expansion artifacts to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
