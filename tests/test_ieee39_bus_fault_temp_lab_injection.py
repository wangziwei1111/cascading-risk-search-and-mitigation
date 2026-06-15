from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"
PLANS = BASE / "temp_lab_plans"
SMOKE = BASE / "temp_lab_smoke_outputs"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_temp_lab_scripts_and_artifacts_exist() -> None:
    for rel in [
        "scripts/gcn_search/prepare_ieee39_bus_fault_temp_lab.py",
        "scripts/gcn_search/run_ieee39_bus_fault_temp_lab_smoke.py",
        "matlab/simulink_ieee39/prepare_ieee39_bus_fault_temp_lab_copy.m",
        "docs/ieee39_bus_fault_temp_lab_injection.md",
    ]:
        path = ROOT / rel
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0, f"empty {path}"

    for target_bus in ["B39", "B26"]:
        for suffix in [
            f"ieee39_bus_fault_temp_lab_{target_bus}_plan.json",
            f"ieee39_bus_fault_temp_lab_{target_bus}_plan.md",
            f"matlab_bus_fault_injection_inventory_{target_bus}.json",
            f"matlab_bus_fault_injection_inventory_{target_bus}.md",
        ]:
            path = PLANS / suffix
            assert path.exists(), f"missing {path}"
            assert path.stat().st_size > 0, f"empty {path}"

    for suffix in [
        "ieee39_bus_fault_temp_lab_feasibility_summary.json",
        "ieee39_bus_fault_temp_lab_feasibility_summary.md",
    ]:
        path = PLANS / suffix
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0, f"empty {path}"


def test_temp_lab_plans_preserve_boundaries() -> None:
    for target_bus in ["B39", "B26"]:
        payload = _load_json(PLANS / f"ieee39_bus_fault_temp_lab_{target_bus}_plan.json")
        assert payload["target_bus"] == target_bus
        assert payload["preview_only"] is True
        assert payload["temporary_model_is_ignored"] is True
        assert payload["source_slx_modified"] is False
        assert payload["source_slx_committed"] is False
        assert payload["temporary_slx_committed"] is False
        assert payload["manual_review_required"] is True
        assert payload["do_not_commit_temporary_slx"] is True
        assert payload["formal_label_gate"] == "35 / 33 / 33"
        assert payload["v2_candidate_count"] == 40
        assert payload["reranker_retrained"] is False
        assert payload["gcn_trained"] is False
        assert payload["labels_exported"] is False
        assert payload["l12_touched"] is False


def test_matlab_inventories_are_conservative() -> None:
    for target_bus in ["B39", "B26"]:
        payload = _load_json(PLANS / f"matlab_bus_fault_injection_inventory_{target_bus}.json")
        assert payload["target_bus"] == target_bus
        assert payload["source_model_modified"] is False
        assert payload["injection_point_found"] is False
        assert payload["fault_block_added_to_temp_copy"] is False
        assert payload["fault_timing_configured"] is False
        assert payload["compile_or_update_diagram_success"] is True
        assert payload["manual_review_required"] is True
        assert payload["safe_to_run_smoke"] is False
        assert payload["candidate_block_paths"], f"expected candidate inventory for {target_bus}"


def test_temp_lab_feasibility_summary_records_no_training_or_gate_change() -> None:
    payload = _load_json(PLANS / "ieee39_bus_fault_temp_lab_feasibility_summary.json")
    assert payload["preview_only"] is True
    assert payload["target_buses_attempted"] == ["B26", "B39"]
    assert payload["target_buses_with_injection_point_found"] == []
    assert payload["target_buses_safe_to_run_smoke"] == []
    assert payload["target_buses_smoke_successful"] == []
    assert payload["source_slx_modified"] is False
    assert payload["source_slx_committed"] is False
    assert payload["temporary_slx_committed"] is False
    assert payload["formal_label_gate_changed"] is False
    assert payload["old_formal_gate"] == "35 / 33 / 33"
    assert payload["v2_candidate_count_changed"] is False
    assert payload["v2_candidate_count"] == 40
    assert payload["reranker_retrained"] is False
    assert payload["gcn_trained"] is False
    assert payload["labels_exported"] is False
    assert payload["l12_touched"] is False


def test_temp_lab_smoke_refuses_when_not_safe() -> None:
    payload = _load_json(SMOKE / "ieee39_bus_fault_temp_lab_smoke_report.json")
    assert payload["preview_only"] is True
    assert payload["target_bus"] == "B39"
    assert payload["safe_to_run_smoke"] is False
    assert payload["smoke_executed"] is False
    if payload.get("human_readiness_used"):
        assert payload["human_readiness_ready"] is True
        assert payload["smoke_not_run_reason"] == "ready_for_next_round_temp_smoke"
    else:
        assert "safe_to_run_smoke=false" in payload["smoke_not_run_reason"]
    assert payload["source_slx_modified"] is False
    assert payload["temporary_slx_committed"] is False
    assert payload["formal_label_gate_changed"] is False
    assert payload["v2_candidate_count_changed"] is False
    assert payload["reranker_retrained"] is False
    assert payload["gcn_trained"] is False
    assert payload["labels_exported"] is False
    assert payload["l12_touched"] is False


def test_no_temp_or_source_model_artifacts_are_tracked() -> None:
    tracked = subprocess.check_output(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    forbidden_tokens = [
        "local_lab_copies",
        "temp_slx",
        "slprj",
        ".slx",
        ".slxc",
        ".mat",
        "raw_trajectories",
        "full_timeseries",
    ]
    offenders = [path for path in tracked if any(token in path.lower() for token in forbidden_tokens)]
    assert offenders == []
