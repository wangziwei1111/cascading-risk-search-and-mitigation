import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
EVIDENCE_DIR = BASE / "manual_connection_evidence"
SUMMARY_JSON = EVIDENCE_DIR / "batch_manual_connection_evidence_summary.json"
SUMMARY_MD = EVIDENCE_DIR / "batch_manual_connection_evidence_summary.md"
SUMMARY_CSV = EVIDENCE_DIR / "batch_manual_connection_evidence_summary.csv"
READY_JSON = EVIDENCE_DIR / "buses_ready_for_readiness_dry_run.json"
DOC = ROOT / "docs/ieee39_all_remaining_bus_fault_manual_connection_evidence.md"

NORMAL_BUSES = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
ALL_BUSES = NORMAL_BUSES + ["B16"]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    with open(_long(path), encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def test_per_bus_evidence_artifacts_exist() -> None:
    for bus in ALL_BUSES:
        assert os.path.exists(_long(EVIDENCE_DIR / f"manual_connection_evidence_{bus}.json")), bus
        assert os.path.exists(_long(EVIDENCE_DIR / f"manual_connection_evidence_{bus}.md")), bus
    assert SUMMARY_JSON.exists()
    assert SUMMARY_MD.exists()
    assert SUMMARY_CSV.exists()
    assert READY_JSON.exists()
    assert DOC.exists()


def test_summary_boundaries_and_counts() -> None:
    summary = _read_json(SUMMARY_JSON)
    assert summary["batch_id"] == "bus_fault_all_remaining_manual_wiring"
    assert summary["user_declared_all_wiring_complete"] is True
    assert summary["total_targets"] == 37
    assert summary["normal_targets"] == 36
    assert summary["special_targets"] == 1
    assert set(summary["existing_completed_bus_faults"]) == {"B39", "B26"}
    assert summary["current_candidate_count"] == 42
    assert summary["old_formal_gate"] == "35 / 33 / 33"
    assert summary["num_temp_models_found"] == 37
    assert summary["num_fault_blocks_found"] == 37
    assert summary["num_update_diagram_success"] == 37
    assert summary["num_automated_evidence_check_passed"] == 37
    assert summary["num_human_verified_injection_point"] == 37
    assert summary["num_safe_to_run_smoke_recommendation"] == 37
    assert len(summary["buses_ready_for_next_round_readiness"]) == 37
    assert summary["buses_blocked"] == []
    assert summary["b16_special_check_passed"] is True
    assert summary["b16_old_fault_not_moved"] is True
    assert summary["simulink_run"] is False
    assert summary["actual_smoke_run"] is False
    assert summary["labels_exported"] is False
    assert summary["candidate_labels_exported"] is False
    assert summary["gcn_trained"] is False
    assert summary["reranker_retrained"] is False
    assert summary["gcn_usefulness_audit_run"] is False
    assert summary["should_run_smoke_now"] is False
    assert summary["should_export_labels_now"] is False
    assert summary["should_train_now"] is False


def test_each_evidence_boundary_flags() -> None:
    for bus in ALL_BUSES:
        evidence = _read_json(EVIDENCE_DIR / f"manual_connection_evidence_{bus}.json")
        assert evidence["target_bus"] == bus
        assert evidence["user_declared_manual_wiring_complete"] is True
        assert evidence["temp_model_exists"] is True
        assert evidence["fault_block_found"] is True
        assert evidence["fault_block_name_correct"] is True
        assert evidence["update_diagram_attempted"] is True
        assert evidence["update_diagram_success"] is True
        assert evidence["automated_evidence_check_passed"] is True
        assert evidence["human_verified_injection_point"] is True
        assert evidence["safe_to_run_smoke_recommendation"] is True
        assert evidence["simulink_smoke_run"] is False
        assert evidence["smoke_success"] is False
        assert evidence["labels_exported"] is False
        assert evidence["candidate_label_exported"] is False
        assert evidence["gcn_trained"] is False
        assert evidence["reranker_retrained"] is False
        if bus == "B16":
            assert evidence["special_handling"] is True
            assert evidence["selected_fault_block_path"] == "Grid/Fault_B16_TEMP"
        else:
            assert evidence["special_handling"] is False


def test_ready_list_matches_summary() -> None:
    ready = _read_json(READY_JSON)
    assert ready["batch_id"] == "bus_fault_all_remaining_manual_wiring"
    assert set(ready["ready_buses"]) == set(ALL_BUSES)
    assert ready["blocked_buses"] == []
    assert ready["ready_count"] == 37
    assert ready["blocked_count"] == 0
    assert ready["should_run_readiness_now"] is False
    assert ready["should_run_smoke_now"] is False
    assert ready["should_export_labels_now"] is False
    assert ready["should_train_now"] is False


def test_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(SUMMARY_MD),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "does not run simulink simulation",
        "does not run actual smoke",
        "does not export labels",
        "does not train gcn",
        "does not run a gcn usefulness audit",
        "not formal labels",
        "not candidate labels",
        "not smoke success",
        "phasor_rms, not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "37 new targets are candidate labels",
        "37 new targets are smoke success",
        "gcn usefulness audit was run",
        "labels_exported=true",
        "candidate_label_exported=true",
        "smoke_success=true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in normalized


def test_no_forbidden_large_artifacts_are_tracked_for_evidence() -> None:
    result = subprocess.run(
        ["git", "ls-files", str(EVIDENCE_DIR.relative_to(ROOT)).replace("\\", "/")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    forbidden = [".slx", ".slxc", ".mat", "slprj", "raw_trajector", "full_timeseries", "local_lab_copies"]
    bad = [path for path in result.stdout.splitlines() if any(token in path.lower() for token in forbidden)]
    assert bad == []
