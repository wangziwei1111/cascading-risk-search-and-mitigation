from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_manual_dynamic_validation"
DOC = ROOT / "docs/ieee39_spp001_manual_dynamic_validation.md"


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path):
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    with open(_long(path), encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def test_spp001_manual_dynamic_validation_artifacts_exist() -> None:
    expected = [
        "spp001_manual_bridge_build_summary.json",
        "spp001_manual_bridge_static_connectivity.json",
        "spp001_manual_bridge_control_wiring.json",
        "spp001_manual_bridge_bypass_check.json",
        "spp001_manual_bridge_unconnected_ports_report.json",
        "spp001_manual_bridge_static_gate.json",
        "spp001_dynamic_stage_manifest.json",
        "spp001_dynamic_stage_results.json",
        "spp001_dynamic_stage_results.csv",
        "spp001_dynamic_phase_trace.json",
        "spp001_dynamic_stdout_stderr_excerpt.json",
        "spp001_dynamic_solver_warning_report.json",
        "spp001_dynamic_validation_summary.json",
        "spp001_dynamic_validation_summary.csv",
        "no_leakage_spp001_manual_dynamic_validation_audit.json",
        "large_file_safety_spp001_manual_dynamic_validation.json",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_spp001_manual_bridge_static_gate_passed_before_dynamic_attempt() -> None:
    gate = _read_json(OUT_DIR / "spp001_manual_bridge_static_gate.json")
    for key in [
        "l15_trip_command_to_breaker_control_connected",
        "l15_breaker_physical_ports_connected",
        "l15_breaker_in_series_with_actual_l15_branch",
        "l15_original_direct_bypass_removed",
        "l04_trip_command_to_breaker_control_connected",
        "l04_breaker_physical_ports_connected",
        "l04_breaker_in_series_with_actual_l04_branch",
        "l04_original_direct_bypass_removed",
        "no_unconnected_physical_ports",
        "no_unconnected_control_ports",
        "update_diagram_passed",
        "physical_bridge_valid",
        "static_gate_passed",
    ]:
        assert gate[key] is True, key


def test_spp001_manual_dynamic_validation_stops_on_stage_a_timeout() -> None:
    summary = _read_json(OUT_DIR / "spp001_dynamic_validation_summary.json")
    stages = _read_json(OUT_DIR / "spp001_dynamic_stage_results.json")

    assert summary["static_gate_passed"] is True
    assert summary["physical_bridge_valid"] is True
    assert summary["dynamic_stages_requested"] == 5
    assert summary["dynamic_stages_completed"] == 0
    assert summary["dynamic_stages_stopped_early"] is True
    assert summary["earliest_failed_stage_if_any"] == "A"
    assert summary["full_spp001_dynamic_validation_completed"] is False
    assert summary["pilot_label_value"] is None
    assert summary["no_formal_label_generated"] is True

    assert len(stages) == 1
    assert stages[0]["stage_id"] == "A"
    assert stages[0]["execution_status"] in {"timeout", "failed"}
    assert stages[0]["line_trip_applied"] is False
    assert stages[0]["pilot_label_value"] is None
    assert stages[0]["pilot_labels_are_formal_training_labels"] is False


def test_spp001_manual_dynamic_validation_boundaries_are_conservative() -> None:
    summary = _read_json(OUT_DIR / "spp001_dynamic_validation_summary.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_spp001_manual_dynamic_validation_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_spp001_manual_dynamic_validation.json")

    for key in [
        "gcn_training_run",
        "formal_gcn_audit_rerun",
        "selected_32_batch_executed",
        "full_1056_generation_run",
        "labels_exported",
        "formal_labels_exported",
        "reranker_retrained",
        "production_model_saved",
        "bus_fault_labels_used",
    ]:
        assert summary[key] is False, key

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["label_derived_flags_used_as_inputs"] is False
    assert no_leakage["bus_fault_labels_used"] is False
    assert no_leakage["no_leakage_policy_passed"] is True

    for key in [
        "raw_trajectories_committed",
        "full_timeseries_committed",
        "mat_files_committed",
        "slx_files_committed",
        "slxc_files_committed",
        "slprj_committed",
        "local_bridge_committed",
        "source_slx_modified",
        "venv_committed",
        "wheel_or_dll_committed",
        "model_files_committed",
    ]:
        assert safety[key] is False, key
    assert safety["safety_check_passed"] is True


def test_spp001_manual_dynamic_validation_docs_do_not_overstate() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(OUT_DIR / "spp001_dynamic_validation_summary.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "static_gate_passed",
        "stage a",
        "timed out",
        "not a completed spp001 dynamic validation",
        "no pilot/formal label",
        "does not train gcn",
        "does not export labels",
        "does not execute selected 32",
        "does not run full 1056",
        "does not retrain the reranker",
        "does not run rl mitigation",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
        "l12 remains special/excluded",
    ]:
        assert required in normalized
    for forbidden in [
        "full_spp001_dynamic_validation_completed: true",
        "spp001 dynamic validation completed",
        "formal labels exported",
        "selected 32 batch executed",
        "full 1056 generation completed",
        "gcn training completed",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_spp001_manual_dynamic_validation_no_forbidden_large_artifacts_tracked() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    changed = [line.strip().lower().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]
    forbidden_tokens = [
        ".venv-gcn-audit/",
        ".venv/",
        "site-packages",
        ".whl",
        ".dll",
        ".pt",
        ".pth",
        ".ckpt",
        ".slx",
        ".slxc",
        "slprj",
        ".mat",
        "raw_trajector",
        "full_timeseries",
        "local_lab_copies",
        "local_bridge_copy",
    ]
    for path in changed:
        assert not any(token in path for token in forbidden_tokens), path
