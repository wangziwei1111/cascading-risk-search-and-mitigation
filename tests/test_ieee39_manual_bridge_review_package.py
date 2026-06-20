from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_manual_bridge_review_package"
ZIP_PATH = OUT_DIR / "spp001_manual_bridge_review_package.zip"
LOCAL_BRIDGE = (
    ROOT
    / "results/gcn_search/ieee39_spp001_manual_dynamic_validation/local_bridge_copy/"
    / "IEEE39BusSystem_dynamic_experiment_wrapper_spp001_manual_physical_bridge.slx"
)
L15_SOURCE = (
    ROOT
    / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/"
    / "IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L15.slx"
)
L04_SOURCE = (
    ROOT
    / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/"
    / "IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx"
)

REQUIRED_FILES = {
    "model_summary.json",
    "block_inventory.csv",
    "physical_port_connectivity.csv",
    "signal_port_connectivity.csv",
    "unconnected_ports.csv",
    "breaker_control_chain.json",
    "breaker_series_and_bypass_check.json",
    "l15_topology_comparison.json",
    "l04_topology_comparison.json",
    "model_configuration.json",
    "static_update_check.json",
    "review_manifest.json",
    "grid_overview.png",
}


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path):
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def test_manual_bridge_review_package_exporter_runs_without_sim() -> None:
    before = {
        "local": os.path.getmtime(_long(LOCAL_BRIDGE)),
        "l15": os.path.getmtime(_long(L15_SOURCE)),
        "l04": os.path.getmtime(_long(L04_SOURCE)),
    }
    result = subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/export_ieee39_manual_bridge_review_package.py",
            "--zip-review-package",
            "--output-dir",
            str(OUT_DIR),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        timeout=300,
        encoding="utf-8",
        errors="replace",
    )
    assert "REVIEW_PACKAGE_READY=" in result.stdout
    after = {
        "local": os.path.getmtime(_long(LOCAL_BRIDGE)),
        "l15": os.path.getmtime(_long(L15_SOURCE)),
        "l04": os.path.getmtime(_long(L04_SOURCE)),
    }
    assert before == after


def test_manual_bridge_review_package_contains_required_files() -> None:
    assert ZIP_PATH.exists()
    for filename in REQUIRED_FILES:
        assert (OUT_DIR / filename).exists(), filename
    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = set(archive.namelist())
    assert REQUIRED_FILES <= names


def test_manual_bridge_review_package_has_no_forbidden_payloads() -> None:
    forbidden_suffixes = {".slx", ".slxc", ".mat", ".pt", ".pth", ".ckpt", ".dll", ".whl"}
    forbidden_tokens = {"raw_trajector", "full_timeseries", "slprj"}
    with zipfile.ZipFile(ZIP_PATH) as archive:
        for name in archive.namelist():
            lower = name.lower()
            assert Path(lower).suffix not in forbidden_suffixes, name
            assert not any(token in lower for token in forbidden_tokens), name


def test_manual_bridge_review_package_summary_contract() -> None:
    summary = _read_json(OUT_DIR / "model_summary.json")
    manifest = _read_json(OUT_DIR / "review_manifest.json")
    bypass = _read_json(OUT_DIR / "breaker_series_and_bypass_check.json")
    static_update = _read_json(OUT_DIR / "static_update_check.json")

    for key in [
        "sim_called",
        "gcn_training_run",
        "selected_32_batch_executed",
        "full_1056_generation_run",
        "labels_exported",
        "formal_labels_exported",
        "raw_trajectories_saved",
        "full_timeseries_saved",
        "mat_files_saved",
        "source_slx_modified",
        "local_bridge_saved",
        "local_bridge_committed",
    ]:
        assert summary[key] is False, key

    assert summary["pair_id"] == "SPP001"
    assert summary["l15_trip_command_to_breaker_control_connected"] is True
    assert summary["l15_breaker_physical_ports_connected"] is True
    assert summary["l15_breaker_in_series_with_actual_l15_branch"] is True
    assert summary["l15_original_direct_bypass_exists"] is False
    assert summary["l15_original_direct_bypass_removed"] is True
    assert summary["l04_trip_command_to_breaker_control_connected"] is True
    assert summary["l04_breaker_physical_ports_connected"] is True
    assert summary["l04_breaker_in_series_with_actual_l04_branch"] is True
    assert summary["l04_original_direct_bypass_exists"] is False
    assert summary["l04_original_direct_bypass_removed"] is True
    assert summary["no_unconnected_physical_ports"] is True
    assert summary["no_unconnected_control_ports"] is True
    assert summary["physical_bridge_valid"] is True
    assert summary["block_existence_only_is_sufficient"] is False
    assert summary["forbidden_features_detected_in_inputs"] == []
    assert summary["no_leakage_policy_passed"] is True

    assert bypass["block_existence_only_is_sufficient"] is False
    assert "PortHandles" in bypass["note"]
    assert static_update["sim_called"] is False
    assert static_update["update_diagram_called"] is False
    assert manifest["local_bridge_slx_included"] is False
    assert manifest["required_files_missing"] == []
    assert manifest["forbidden_files_in_review_package_dir"] == []


def test_manual_bridge_review_package_not_name_only() -> None:
    physical_csv = (OUT_DIR / "physical_port_connectivity.csv").read_text(encoding="utf-8", errors="ignore")
    signal_csv = (OUT_DIR / "signal_port_connectivity.csv").read_text(encoding="utf-8", errors="ignore")
    control = _read_json(OUT_DIR / "breaker_control_chain.json")
    l15 = _read_json(OUT_DIR / "l15_topology_comparison.json")
    l04 = _read_json(OUT_DIR / "l04_topology_comparison.json")

    assert "port_handle" in physical_csv
    assert "line_handle" in physical_csv
    assert "neighbor_blocks" in physical_csv
    assert "port_handle" in signal_csv
    assert len(control["l15_control_signal_path"]) >= 2
    assert len(control["l04_control_signal_path"]) >= 2
    assert "port/line graph evidence" in l15["note"]
    assert "port/line graph evidence" in l04["note"]


def test_manual_bridge_review_package_no_forbidden_large_artifacts_tracked_and_rl_clean() -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    ).stdout.lower().replace("\\", "/")
    for token in [
        ".slx",
        ".slxc",
        "slprj",
        ".mat",
        "raw_trajector",
        "full_timeseries",
        "local_bridge_copy",
        ".pt",
        ".pth",
        ".ckpt",
        ".dll",
        ".whl",
        "site-packages",
        ".venv",
    ]:
        assert token not in changed

    rl_diff = subprocess.run(
        ["git", "diff", "--", "src/rl_mitigation", "scripts/rl_mitigation"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    assert rl_diff.stdout == ""
