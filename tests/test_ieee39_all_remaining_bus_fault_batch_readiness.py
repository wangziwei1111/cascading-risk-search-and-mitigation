import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
READINESS_DIR = BASE / "readiness_dry_run"
SUMMARY_JSON = READINESS_DIR / "batch_readiness_dry_run_summary.json"
SUMMARY_MD = READINESS_DIR / "batch_readiness_dry_run_summary.md"
SUMMARY_CSV = READINESS_DIR / "batch_readiness_dry_run_summary.csv"
MANIFEST_JSON = READINESS_DIR / "batch_actual_smoke_plan_manifest.json"
MANIFEST_MD = READINESS_DIR / "batch_actual_smoke_plan_manifest.md"
DOC = ROOT / "docs/ieee39_all_remaining_bus_fault_batch_readiness_dry_run.md"

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


def test_per_bus_readiness_artifacts_exist() -> None:
    for bus in ALL_BUSES:
        assert os.path.exists(_long(READINESS_DIR / f"readiness_dry_run_{bus}.json")), bus
        assert os.path.exists(_long(READINESS_DIR / f"readiness_dry_run_{bus}.md")), bus
    assert SUMMARY_JSON.exists()
    assert SUMMARY_MD.exists()
    assert SUMMARY_CSV.exists()
    assert MANIFEST_JSON.exists()
    assert MANIFEST_MD.exists()
    assert DOC.exists()


def test_batch_readiness_summary_boundaries() -> None:
    summary = _read_json(SUMMARY_JSON)
    assert summary["batch_id"] == "bus_fault_all_remaining_manual_wiring"
    assert summary["readiness_scope"] == "dry_run_only"
    assert summary["total_targets"] == 37
    assert summary["normal_targets"] == 36
    assert summary["special_targets"] == 1
    assert set(summary["existing_completed_bus_faults"]) == {"B39", "B26"}
    assert summary["current_candidate_count"] == 42
    assert summary["old_formal_gate"] == "35 / 33 / 33"
    assert summary["num_manual_evidence_passed"] == 37
    assert summary["num_readiness_dry_run_checked"] == 37
    assert summary["num_ready_for_next_round_actual_smoke"] == 37
    assert summary["num_blocked_before_smoke"] == 0
    assert set(summary["ready_buses"]) == set(ALL_BUSES)
    assert summary["blocked_buses"] == []
    assert summary["blocked_reasons_by_bus"] == {}
    assert summary["b16_special_handling_preserved"] is True
    assert summary["b16_old_fault_not_moved"] is True
    assert summary["simulation_run"] is False
    assert summary["actual_smoke_run"] is False
    assert summary["labels_exported"] is False
    assert summary["candidate_labels_exported"] is False
    assert summary["gcn_trained"] is False
    assert summary["reranker_retrained"] is False
    assert summary["gcn_usefulness_audit_run"] is False
    assert summary["should_run_actual_smoke_now"] is False
    assert summary["should_export_labels_now"] is False
    assert summary["should_train_now"] is False


def test_each_readiness_record_is_dry_run_only() -> None:
    for bus in ALL_BUSES:
        record = _read_json(READINESS_DIR / f"readiness_dry_run_{bus}.json")
        assert record["target_bus"] == bus
        assert record["readiness_scope"] == "dry_run_only"
        assert record["actual_smoke_run"] is False
        assert record["simulation_run"] is False
        assert record["labels_exported"] is False
        assert record["candidate_label_exported"] is False
        assert record["gcn_trained"] is False
        assert record["reranker_retrained"] is False
        assert record["gcn_usefulness_audit_run"] is False
        assert record["source_slx_modified"] is False
        assert record["temporary_slx_committed"] is False
        assert record["selected_fault_block_path"] == f"Grid/Fault_{bus}_TEMP"
        assert record["temp_model_exists"] is True
        assert record["fault_block_found"] is True
        assert record["fault_block_name_correct"] is True
        assert record["update_diagram_success"] is True
        assert record["human_verified_injection_point"] is True
        assert record["safe_to_run_smoke_recommendation_from_manual_evidence"] is True
        assert record["readiness_status"] == "ready_for_next_round_actual_smoke"
        assert record["ready_for_next_round_actual_smoke"] is True
        assert "smoke_success" not in record
        if bus == "B16":
            assert record["special_handling"] is True
        else:
            assert record["special_handling"] is False


def test_actual_smoke_plan_is_plan_only() -> None:
    manifest = _read_json(MANIFEST_JSON)
    assert manifest["plan_scope"] == "next_round_actual_smoke_plan_only"
    assert manifest["actual_smoke_run_this_round"] is False
    assert set(manifest["ready_buses"]) == set(ALL_BUSES)
    assert manifest["blocked_buses"] == []
    assert manifest["should_run_smoke_now"] is False
    assert manifest["should_export_labels_now"] is False
    assert manifest["should_train_now"] is False
    for bus in ALL_BUSES:
        assert manifest["scenario_id_by_bus"][bus] == f"BF_{bus}_TEMP_SMOKE"
        assert manifest["selected_fault_block_path_by_bus"][bus] == f"Grid/Fault_{bus}_TEMP"


def test_readiness_docs_are_conservative() -> None:
    readiness_text = "\n".join(
        [
            _read_text(DOC),
            _read_text(SUMMARY_MD),
            _read_text(MANIFEST_MD),
        ]
    ).lower()
    text_with_log = "\n".join(
        [
            readiness_text,
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text_with_log.replace("`", "").split())
    for required in [
        "readiness dry-run",
        "not actual smoke",
        "no simulation was run",
        "does not export labels",
        "does not train gcn",
        "does not run a gcn usefulness audit",
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
        "actual smoke succeeded",
        "simulation succeeded",
        "gcn usefulness audit was run",
        "labels_exported=true",
        "candidate_label_exported=true",
        "smoke_success=true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
            assert forbidden not in " ".join(readiness_text.replace("`", "").split())


def test_no_forbidden_large_artifacts_are_tracked_for_readiness() -> None:
    result = subprocess.run(
        ["git", "ls-files", str(READINESS_DIR.relative_to(ROOT)).replace("\\", "/")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    forbidden = [".slx", ".slxc", ".mat", "slprj", "raw_trajector", "full_timeseries", "local_lab_copies"]
    bad = [path for path in result.stdout.splitlines() if any(token in path.lower() for token in forbidden)]
    assert bad == []
