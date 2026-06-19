from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_same_wrapper_bridge_builder_repair"
DOC = ROOT / "docs/ieee39_spp001_same_wrapper_bridge_builder_repair.md"


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


def test_spp001_same_wrapper_bridge_builder_repair_writes_artifacts() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/repair_ieee39_spp001_same_wrapper_bridge_builder.py",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_spp001_same_wrapper_bridge_builder_repair_artifacts_exist() -> None:
    expected = [
        "spp001_bridge_builder_repair_summary.json",
        "spp001_bridge_builder_repair_summary.md",
        "spp001_bridge_builder_repair_summary.csv",
        "spp001_bridge_builder_repair_report.json",
        "spp001_bridge_builder_repair_report.md",
        "spp001_repaired_same_wrapper_manifest.json",
        "spp001_repaired_same_wrapper_manifest.md",
        "spp001_bridge_builder_rerun_gate.json",
        "spp001_bridge_builder_rerun_gate.md",
        "no_leakage_spp001_bridge_builder_repair_audit.json",
        "no_leakage_spp001_bridge_builder_repair_audit.md",
        "large_file_safety_spp001_bridge_builder_repair.json",
        "large_file_safety_spp001_bridge_builder_repair.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_spp001_same_wrapper_bridge_builder_repair_summary_and_gate() -> None:
    summary = _read_json(OUT_DIR / "spp001_bridge_builder_repair_summary.json")
    manifest = _read_json(OUT_DIR / "spp001_repaired_same_wrapper_manifest.json")
    gate = _read_json(OUT_DIR / "spp001_bridge_builder_rerun_gate.json")
    report = _read_json(OUT_DIR / "spp001_bridge_builder_repair_report.json")

    expected = {
        "repair_scope": "spp001_same_wrapper_bridge_builder_repair",
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
        "source_local_validation_commit": "391a67f1e380d167b39779bfd06c161519eefdfc",
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "previous_l15_trip_command_found_in_bridge": False,
        "previous_l04_trip_command_found_in_bridge": True,
        "local_bridge_build_attempted": True,
        "local_bridge_validation_attempted": True,
        "local_bridge_built": True,
        "local_bridge_committed": False,
        "source_slx_modified": False,
        "l15_trip_command_found_in_bridge": True,
        "l04_trip_command_found_in_bridge": True,
        "l15_breaker_found_in_bridge": True,
        "l04_breaker_found_in_bridge": True,
        "same_wrapper_confirmed": True,
        "repaired_provenance_manifest_written": True,
        "can_rerun_spp001_after_manual_approval": True,
        "no_label_value_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "blocker_if_any": None,
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert summary["recommended_next_step"] == (
        "approve rerun of SPP001 single-pair smoke using repaired same-wrapper bridge in a separate round; do not export labels or train"
    )

    assert report["repair_report_scope"] == "spp001_bridge_builder_repair_report"
    assert report["matlab_builder_invoked"] is True
    assert report["matlab_returncode"] == 0
    assert report["local_bridge_built"] is True
    assert report["source_slx_modified"] is False
    assert report["simulink_run"] is False

    assert manifest["manifest_scope"] == "spp001_repaired_same_wrapper_manifest"
    assert manifest["same_wrapper_confirmed"] is True
    assert manifest["l15_trip_command_found_in_bridge"] is True
    assert manifest["l04_trip_command_found_in_bridge"] is True
    assert manifest["l15_breaker_found_in_bridge"] is True
    assert manifest["l04_breaker_found_in_bridge"] is True
    assert manifest["approved_for_execution_now"] is False
    assert manifest["requires_next_round_approval"] is True

    assert gate["gate_scope"] == "spp001_bridge_builder_rerun_gate"
    assert gate["l15_ready"] is True
    assert gate["l04_ready"] is True
    assert gate["local_bridge_built"] is True
    assert gate["same_wrapper_confirmed"] is True
    assert gate["selected_32_batch_allowed"] is False
    assert gate["full_1056_allowed"] is False
    assert gate["formal_label_export_allowed"] is False
    assert gate["gcn_training_allowed"] is False
    assert gate["can_request_spp001_smoke_rerun_approval"] is True


def test_spp001_same_wrapper_bridge_builder_repair_no_leakage_and_safety() -> None:
    no_leakage = _read_json(OUT_DIR / "no_leakage_spp001_bridge_builder_repair_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_spp001_bridge_builder_repair.json")

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
        "local_bridge_committed",
        "local_lab_copy_committed",
        "source_slx_modified",
        "venv_committed",
        "wheel_or_dll_committed",
        "model_files_committed",
    ]:
        assert safety[key] is False, key
    assert safety["safety_check_passed"] is True


def test_spp001_same_wrapper_bridge_builder_repair_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(OUT_DIR / "spp001_bridge_builder_repair_summary.md"),
            _read_text(OUT_DIR / "spp001_bridge_builder_rerun_gate.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "spp001 same-wrapper bridge builder repair",
        "does not train gcn",
        "does not rerun formal audit",
        "does not execute spp001 smoke",
        "does not execute selected 32 batch",
        "does not run full 1056 generation",
        "does not export formal labels",
        "missing l15_tripcommand",
        "local bridge .slx",
        "does not generate a 0/1 label",
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
        "spp001 smoke completed",
        "selected 32 batch execution completed",
        "full 1056 generation completed",
        "formal labels exported",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_spp001_same_wrapper_bridge_builder_repair_no_forbidden_large_artifacts_tracked() -> None:
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
