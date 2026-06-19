from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_model_provenance_bridge_repair"
DOC = ROOT / "docs/ieee39_spp001_model_provenance_bridge_repair.md"


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


def test_spp001_provenance_bridge_runner_writes_artifacts() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/repair_ieee39_spp001_model_provenance_bridge.py",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_spp001_provenance_bridge_artifacts_exist() -> None:
    expected = [
        "spp001_provenance_bridge_repair_summary.json",
        "spp001_provenance_bridge_repair_summary.md",
        "spp001_provenance_bridge_repair_summary.csv",
        "spp001_trip_command_provenance_inventory.json",
        "spp001_trip_command_provenance_inventory.md",
        "spp001_repaired_provenance_manifest.json",
        "spp001_repaired_provenance_manifest.md",
        "spp001_rerun_provenance_gate.json",
        "spp001_rerun_provenance_gate.md",
        "no_leakage_spp001_provenance_bridge_audit.json",
        "no_leakage_spp001_provenance_bridge_audit.md",
        "large_file_safety_spp001_provenance_bridge.json",
        "large_file_safety_spp001_provenance_bridge.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_spp001_provenance_bridge_summary_and_gate_fields() -> None:
    summary = _read_json(OUT_DIR / "spp001_provenance_bridge_repair_summary.json")
    manifest = _read_json(OUT_DIR / "spp001_repaired_provenance_manifest.json")
    gate = _read_json(OUT_DIR / "spp001_rerun_provenance_gate.json")
    inventory = _read_json(OUT_DIR / "spp001_trip_command_provenance_inventory.json")

    expected = {
        "repair_scope": "spp001_model_provenance_bridge_repair",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "spp001_smoke_executed": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_spp001_rerun_commit": "f33eb97790a2bcc232a17ecd79be6c5153407f3b",
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "previous_execution_status": "failed",
        "l15_trip_command_model_source": "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15",
        "l04_trip_command_model_source": "IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker",
        "same_wrapper_trip_commands_available": False,
        "repaired_provenance_manifest_written": True,
        "can_rerun_spp001_after_manual_approval": False,
        "no_label_value_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "source_slx_modified": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert summary["blocker_if_any"]
    assert summary["recommended_next_step"] == "build or validate an SPP001-only same-wrapper bridge locally before any rerun"

    assert manifest["manifest_scope"] == "spp001_same_wrapper_provenance_manifest"
    assert manifest["same_wrapper_confirmed"] is False
    assert manifest["approved_for_execution_now"] is False
    assert manifest["requires_next_round_approval"] is True
    assert manifest["prior_trip_command_path"] is None
    assert manifest["next_trip_command_path"] is None

    assert gate["gate_scope"] == "spp001_rerun_provenance_gate"
    assert gate["l15_ready"] is True
    assert gate["l04_ready"] is True
    assert gate["same_wrapper_confirmed"] is False
    assert gate["provenance_bridge_ready"] is False
    assert gate["can_request_spp001_rerun_approval"] is False
    assert gate["selected_32_batch_allowed"] is False
    assert gate["full_1056_allowed"] is False
    assert gate["formal_label_export_allowed"] is False
    assert gate["gcn_training_allowed"] is False

    assert inventory["searched_artifacts"]
    assert inventory["l15_trip_command_candidates"]
    assert inventory["l04_trip_command_candidates"]
    assert inventory["loaded_wrapper_candidates"]
    assert inventory["same_wrapper_candidates"] == []
    assert inventory["selected_candidate_if_any"] is None
    assert inventory["reason_not_selected_if_any"]


def test_spp001_provenance_bridge_no_leakage_and_safety() -> None:
    no_leakage = _read_json(OUT_DIR / "no_leakage_spp001_provenance_bridge_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_spp001_provenance_bridge.json")

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_outputs_used_only_as_future_labels_or_targets"] is True
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
        "source_slx_modified",
        "venv_committed",
        "wheel_or_dll_committed",
        "model_files_committed",
    ]:
        assert safety[key] is False, key
    assert safety["safety_check_passed"] is True


def test_spp001_provenance_bridge_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_spp001_single_pair_smoke_rerun.md"),
            _read_text(ROOT / "docs/ieee39_l15_handwired_validation_readiness_repair.md"),
            _read_text(ROOT / "docs/ieee39_matlab_selected_pair_entrypoint_repair.md"),
            _read_text(OUT_DIR / "spp001_provenance_bridge_repair_summary.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "spp001 model provenance bridge repair",
        "does not train gcn",
        "does not rerun formal audit",
        "does not execute spp001 smoke",
        "does not execute selected 32 batch",
        "does not run full 1056 generation",
        "does not export formal labels",
        "does not retrain the reranker",
        "clean-lab l15",
        "same wrapper",
        "no spp001 0/1 label",
        "raw trajectory",
        "full timeseries",
        "source .slx is not modified",
        "bus-fault labels are not used",
        "l12 remains special/excluded",
        "pilot labels are not formal training labels",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "rerun formal audit completed",
        "spp001 smoke completed",
        "selected 32 batch execution completed",
        "full 1056 generation completed",
        "formal labels exported",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_spp001_provenance_bridge_no_forbidden_large_artifacts_tracked() -> None:
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
