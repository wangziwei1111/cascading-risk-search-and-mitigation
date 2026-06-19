from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_sim_stage_diagnostic_retry"
DOC = ROOT / "docs/ieee39_spp001_sim_stage_diagnostic_retry.md"


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


def test_spp001_sim_stage_diagnostic_retry_writes_artifacts() -> None:
    summary = OUT_DIR / "spp001_sim_stage_diagnostic_summary.json"
    if not os.path.exists(_long(summary)):
        subprocess.run(
            [
                sys.executable,
                "scripts/gcn_search/run_ieee39_spp001_sim_stage_diagnostic_retry.py",
                "--approved-sim-stage-diagnostic-only",
                "--pair-id",
                "SPP001",
                "--max-pairs",
                "1",
                "--write-report",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            timeout=720,
        )


def test_spp001_sim_stage_diagnostic_artifacts_exist() -> None:
    expected = [
        "spp001_sim_stage_diagnostic_summary.json",
        "spp001_sim_stage_diagnostic_summary.md",
        "spp001_sim_stage_diagnostic_summary.csv",
        "spp001_sim_stage_diagnostic_result.json",
        "spp001_sim_stage_diagnostic_result.md",
        "spp001_sim_stage_diagnostic_result.csv",
        "spp001_sim_stage_phase_trace.json",
        "spp001_sim_stage_phase_trace.md",
        "spp001_sim_stage_stdout_stderr_excerpt.json",
        "spp001_sim_stage_stdout_stderr_excerpt.md",
        "spp001_sim_stage_diagnostic_gate.json",
        "spp001_sim_stage_diagnostic_gate.md",
        "no_leakage_spp001_sim_stage_diagnostic_audit.json",
        "no_leakage_spp001_sim_stage_diagnostic_audit.md",
        "large_file_safety_spp001_sim_stage_diagnostic.json",
        "large_file_safety_spp001_sim_stage_diagnostic.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_spp001_sim_stage_diagnostic_summary_contract() -> None:
    summary = _read_json(OUT_DIR / "spp001_sim_stage_diagnostic_summary.json")
    result = _read_json(OUT_DIR / "spp001_sim_stage_diagnostic_result.json")
    gate = _read_json(OUT_DIR / "spp001_sim_stage_diagnostic_gate.json")

    expected = {
        "diagnosis_scope": "spp001_sim_stage_diagnostic_retry",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_timeout_diagnosis_commit": "b858bbf5085324ebee6e7d96f1a0216d8f1aca60",
        "pair_id": "SPP001",
        "same_wrapper_confirmed": True,
        "previous_likely_timeout_stage": "phase_sim_start",
        "sim_stage_diagnostic_attempted": True,
        "pilot_labels_are_formal_training_labels": False,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "local_bridge_committed": False,
        "source_slx_modified": False,
        "bus_fault_labels_used": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "should_train_gcn_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert summary["execution_status"] in {"succeeded", "failed", "timeout", "blocked"}
    assert isinstance(summary["phase_sim_start_seen"], bool)
    assert isinstance(summary["phase_sim_done_seen"], bool)
    assert summary["python_timeout_seconds"] >= 180
    assert summary["matlab_timeout_seconds_if_available"] is not None
    assert summary["pilot_label_value"] in {0, 1, None}
    if summary["execution_status"] != "succeeded":
        assert summary["pilot_label_value"] is None

    assert result["pair_id"] == "SPP001"
    assert result["pilot_labels_are_formal_training_labels"] is False
    assert gate["gate_scope"] == "spp001_sim_stage_diagnostic_gate"
    assert gate["pair_id"] == "SPP001"
    assert gate["selected_32_batch_allowed"] is False
    assert gate["full_1056_allowed"] is False
    assert gate["formal_label_export_allowed"] is False
    assert gate["gcn_training_allowed"] is False
    assert gate["can_request_selected_32_batch"] is False
    assert gate["can_request_formal_label_export"] is False
    assert gate["can_request_gcn_training"] is False


def test_spp001_sim_stage_diagnostic_no_leakage_and_safety() -> None:
    no_leakage = _read_json(OUT_DIR / "no_leakage_spp001_sim_stage_diagnostic_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_spp001_sim_stage_diagnostic.json")

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_outputs_used_only_as_future_labels_or_targets"] is True
    assert no_leakage["label_derived_flags_used_as_inputs"] is False
    assert no_leakage["bus_fault_labels_used"] is False
    assert no_leakage["line_trip_labels_first_priority"] is True
    assert no_leakage["no_leakage_policy_passed"] is True

    for key in [
        "raw_trajectories_committed",
        "full_timeseries_committed",
        "mat_files_committed",
        "slx_files_committed",
        "slxc_files_committed",
        "slprj_committed",
        "local_bridge_committed",
        "local_lab_copy_committed",
        "source_slx_modified",
        "venv_committed",
        "wheel_or_dll_committed",
        "model_files_committed",
    ]:
        assert safety[key] is False, key
    assert safety["safety_check_passed"] is True


def test_spp001_sim_stage_diagnostic_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(OUT_DIR / "spp001_sim_stage_diagnostic_summary.md"),
            _read_text(OUT_DIR / "spp001_sim_stage_diagnostic_result.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "spp001 sim-stage diagnostic retry",
        "does not train gcn",
        "does not rerun formal audit",
        "does not execute selected 32 batch",
        "does not run full 1056 generation",
        "does not export formal labels",
        "previous round reached phase_sim_start",
        "only checks the sim() stage",
        "cannot become a 0/1 label",
        "not a formal training label",
        "raw trajectory",
        "full timeseries",
        "source .slx is not modified",
        "bus-fault labels are not used",
        "l12 remains special/excluded",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "selected 32 batch executed",
        "full 1056 generation completed",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_spp001_sim_stage_diagnostic_no_forbidden_large_artifacts_tracked() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    changed = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
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
    ]
    for path in changed:
        assert not any(token in path for token in forbidden_tokens), path
