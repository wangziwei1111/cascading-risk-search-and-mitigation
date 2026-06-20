from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_bridge_physical_connectivity_audit"
DOC = ROOT / "docs/ieee39_spp001_bridge_physical_connectivity_audit.md"


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


def test_spp001_bridge_physical_connectivity_audit_writes_artifacts() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/audit_ieee39_spp001_bridge_physical_connectivity.py",
            "--approved-static-connectivity-audit-only",
            "--pair-id",
            "SPP001",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        timeout=260,
    )


def test_spp001_bridge_physical_connectivity_audit_artifacts_exist() -> None:
    expected = [
        "spp001_bridge_physical_connectivity_summary.json",
        "spp001_bridge_physical_connectivity_summary.md",
        "spp001_bridge_physical_connectivity_summary.csv",
        "l15_bridge_connectivity_inventory.json",
        "l04_bridge_connectivity_inventory.json",
        "spp001_bridge_unconnected_ports_report.json",
        "spp001_bridge_control_signal_report.json",
        "spp001_bridge_topology_comparison.json",
        "spp001_bridge_execution_go_no_go_gate.json",
        "no_leakage_spp001_bridge_connectivity_audit.json",
        "large_file_safety_spp001_bridge_connectivity_audit.json",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_spp001_bridge_physical_connectivity_audit_summary_contract() -> None:
    summary = _read_json(OUT_DIR / "spp001_bridge_physical_connectivity_summary.json")
    gate = _read_json(OUT_DIR / "spp001_bridge_execution_go_no_go_gate.json")

    expected = {
        "audit_scope": "spp001_bridge_physical_connectivity_audit",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "spp001_smoke_executed": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "pair_id": "SPP001",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "local_bridge_loaded_for_static_audit": True,
        "source_slx_modified": False,
        "l15_trip_command_block_exists": True,
        "l15_breaker_block_exists": True,
        "l15_trip_command_to_breaker_control_connected": False,
        "l15_breaker_physical_ports_connected": False,
        "l15_breaker_in_series_with_actual_l15_branch": False,
        "l04_trip_command_block_exists": True,
        "l04_breaker_block_exists": True,
        "l04_trip_command_to_breaker_control_connected": True,
        "l04_breaker_physical_ports_connected": True,
        "physical_bridge_valid": False,
        "same_wrapper_block_presence_only": True,
        "can_run_initialization_profile_after_manual_approval": False,
        "can_run_full_spp001_smoke_after_manual_approval": False,
        "no_label_value_generated": True,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "local_bridge_committed": False,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "sim_called": False,
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key

    assert summary["blocker_if_any"]
    assert summary["recommended_next_step"].startswith("freeze SPP001 dynamic pair extension")
    assert gate["physical_bridge_valid"] is False
    assert gate["can_run_initialization_profile_after_manual_approval"] is False
    assert gate["selected_32_batch_allowed"] is False
    assert gate["full_1056_allowed"] is False
    assert gate["formal_label_export_allowed"] is False
    assert gate["gcn_training_allowed"] is False


def test_spp001_bridge_physical_connectivity_audit_inventory_is_not_name_only() -> None:
    l15 = _read_json(OUT_DIR / "l15_bridge_connectivity_inventory.json")
    l04 = _read_json(OUT_DIR / "l04_bridge_connectivity_inventory.json")
    unconnected = _read_json(OUT_DIR / "spp001_bridge_unconnected_ports_report.json")
    control = _read_json(OUT_DIR / "spp001_bridge_control_signal_report.json")

    assert l15["bridge"]["breaker_block_exists"] is True
    assert l15["bridge"]["trip_command_block_exists"] is True
    assert l15["bridge"]["breaker_physical_ports_connected"] is False
    assert l15["bridge"]["trip_command_to_breaker_control_connected"] is False
    assert len(l15["bridge"]["unconnected_ports"]) >= 1

    assert l04["bridge"]["breaker_block_exists"] is True
    assert l04["bridge"]["trip_command_block_exists"] is True
    assert l04["bridge"]["breaker_physical_ports_connected"] is True
    assert control["l04_trip_command_to_breaker_control_connected"] is True
    assert unconnected["unconnected_physical_ports_detected"] is True


def test_spp001_bridge_physical_connectivity_audit_no_leakage_and_safety() -> None:
    no_leakage = _read_json(OUT_DIR / "no_leakage_spp001_bridge_connectivity_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_spp001_bridge_connectivity_audit.json")
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
        "local_lab_copy_committed",
        "source_slx_modified",
        "venv_committed",
        "wheel_or_dll_committed",
        "model_files_committed",
    ]:
        assert safety[key] is False, key
    assert safety["safety_check_passed"] is True


def test_spp001_bridge_physical_connectivity_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(OUT_DIR / "spp001_bridge_physical_connectivity_summary.md"),
            _read_text(OUT_DIR / "spp001_bridge_execution_go_no_go_gate.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "spp001 bridge physical connectivity audit",
        "does not call sim()",
        "does not train gcn",
        "does not rerun formal audit",
        "does not execute spp001 smoke",
        "does not execute selected 32 batch",
        "does not run full 1056 generation",
        "does not export formal labels",
        "block name by itself is not enough",
        "physical_bridge_valid",
        "false",
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
        "selected 32 batch executed",
        "full 1056 generation completed",
        "formal labels exported",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_spp001_bridge_physical_connectivity_no_forbidden_large_artifacts_tracked() -> None:
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
