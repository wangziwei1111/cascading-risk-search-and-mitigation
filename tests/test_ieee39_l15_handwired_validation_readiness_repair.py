from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_l15_handwired_validation_readiness_repair"
DOC = ROOT / "docs/ieee39_l15_handwired_validation_readiness_repair.md"


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


def test_l15_readiness_repair_runner_writes_artifacts() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/repair_ieee39_l15_handwired_validation_readiness.py",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_l15_readiness_repair_artifacts_exist() -> None:
    expected = [
        "l15_readiness_repair_summary.json",
        "l15_readiness_repair_summary.md",
        "l15_readiness_repair_summary.csv",
        "l15_evidence_inventory.json",
        "l15_evidence_inventory.md",
        "repaired_combined_validation_preview.json",
        "repaired_combined_validation_preview.md",
        "repaired_combined_validation_preview.csv",
        "spp001_rerun_readiness_gate.json",
        "spp001_rerun_readiness_gate.md",
        "no_leakage_l15_readiness_repair_audit.json",
        "no_leakage_l15_readiness_repair_audit.md",
        "large_file_safety_l15_readiness_repair.json",
        "large_file_safety_l15_readiness_repair.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_l15_readiness_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "l15_readiness_repair_summary.json")
    expected = {
        "repair_scope": "l15_handwired_validation_readiness_repair",
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
        "source_spp001_smoke_commit": "4c9e18b9aab9dce3d968ed3b47271372d60f78b2",
        "target_line_id": "L15",
        "paired_next_line_id": "L04",
        "previous_blocker": "single-pair smoke not ready: validation missing for L15; L04 validation passed",
        "l15_existing_evidence_found": True,
        "l15_trip_command_path_found": True,
        "l15_validation_passed": True,
        "l15_readiness_status": "ready",
        "l04_validation_still_passed": True,
        "repaired_combined_validation_written": True,
        "can_rerun_spp001_smoke_after_manual_approval": True,
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
        "blocker_if_any": None,
        "recommended_next_step": "approve rerun of SPP001 single-pair smoke in a separate round",
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key


def test_l15_inventory_preview_gate_no_leakage_and_safety() -> None:
    inventory = _read_json(OUT_DIR / "l15_evidence_inventory.json")
    preview = _read_json(OUT_DIR / "repaired_combined_validation_preview.json")
    gate = _read_json(OUT_DIR / "spp001_rerun_readiness_gate.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_l15_readiness_repair_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_l15_readiness_repair.json")

    assert inventory["searched_artifacts"]
    assert inventory["l15_rows_found"]
    assert inventory["l15_trip_command_candidates"]
    assert inventory["l15_validation_candidates"]
    assert inventory["selected_source_if_any"]
    assert inventory["reason_not_selected_if_any"] is None

    by_line = {row["line_id"]: row for row in preview}
    assert set(by_line) == {"L04", "L15"}
    assert by_line["L04"]["readiness_status"] == "ready"
    assert by_line["L15"]["readiness_status"] == "ready"
    assert by_line["L15"]["validation_passed"] is True
    assert "L15_TripCommand" in by_line["L15"]["trip_command_path"]

    assert gate["gate_scope"] == "spp001_rerun_readiness_gate"
    assert gate["pair_id"] == "SPP001"
    assert gate["prior_outaged_branch"] == "L15"
    assert gate["candidate_next_branch"] == "L04"
    assert gate["l15_ready"] is True
    assert gate["l04_ready"] is True
    assert gate["both_lines_ready"] is True
    assert gate["selected_32_batch_allowed"] is False
    assert gate["full_1056_allowed"] is False
    assert gate["formal_label_export_allowed"] is False
    assert gate["gcn_training_allowed"] is False
    assert gate["can_request_spp001_rerun_approval"] is True

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


def test_l15_readiness_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_spp001_single_pair_smoke_execution.md"),
            _read_text(ROOT / "docs/ieee39_matlab_selected_pair_entrypoint_repair.md"),
            _read_text(OUT_DIR / "l15_readiness_repair_summary.md"),
            _read_text(OUT_DIR / "spp001_rerun_readiness_gate.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "l15 handwired validation readiness repair",
        "does not train gcn",
        "does not rerun formal audit",
        "does not run spp001 smoke",
        "does not execute selected 32 batch",
        "does not run full 1056 generation",
        "does not export formal labels",
        "does not retrain the reranker",
        "l15",
        "l04",
        "does not create an spp001 0/1 label",
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


def test_l15_readiness_no_forbidden_large_artifacts_tracked() -> None:
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
