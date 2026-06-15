import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans"
)
EVIDENCE_JSON = PLAN_DIR / "b26_manual_connection_evidence.json"
EVIDENCE_MD = PLAN_DIR / "b26_manual_connection_evidence.md"
SUMMARY_JSON = PLAN_DIR / "manual_review_consolidation_summary_B26.json"
SUMMARY_MD = PLAN_DIR / "manual_review_consolidation_summary_B26.md"
TEMPLATE = PLAN_DIR / "manual_bus_fault_injection_review_template_B26.json"
REVIEW_DOC = ROOT / "docs/ieee39_b26_manual_bus_fault_review_result.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_b26_manual_evidence_artifacts_exist():
    for path in [EVIDENCE_JSON, EVIDENCE_MD, SUMMARY_JSON, SUMMARY_MD, REVIEW_DOC]:
        assert path.exists(), path
        assert path.stat().st_size > 0, path


def test_b26_evidence_verified_branch_is_consistent():
    evidence = _load(EVIDENCE_JSON)
    summary = _load(SUMMARY_JSON)
    template = _load(TEMPLATE)

    assert evidence["target_bus"] == "B26"
    assert evidence["fault_b26_temp_found"] is True
    assert evidence["fault_b26_temp_connected_in_parallel"] is True
    assert evidence["selected_fault_block_path"] == "Grid/Fault_B26_TEMP"
    assert evidence["observed_parallel_fault_connected_to_b26"] is True
    assert evidence["update_diagram_attempted"] is True
    assert evidence["update_diagram_success"] is True
    assert evidence["human_verified_injection_point"] is True
    assert evidence["safe_to_run_smoke_recommendation"] is True
    assert evidence["simulink_smoke_run"] is False
    assert evidence["smoke_success"] is False
    assert evidence["labels_exported"] is False
    assert evidence["gcn_trained"] is False
    assert evidence["reranker_retrained"] is False
    assert evidence["old_formal_gate"] == "35 / 33 / 33"
    assert evidence["v2_plus_b39_count"] == 41
    assert evidence["failed_checks"] == []

    assert summary["recommendation"] == "manual_review_supports_next_round_inventory_update"
    assert summary["failed_checks"] == []
    assert summary["human_verified_injection_point"] is True
    assert summary["safe_to_run_smoke_recommendation"] is True
    assert summary["simulink_run"] is False
    assert summary["smoke_success"] is False
    assert summary["labels_exported"] is False
    assert summary["gcn_trained"] is False
    assert summary["reranker_retrained"] is False

    assert template["human_verified_injection_point"] is True
    assert template["safe_to_run_smoke_recommendation"] is True
    assert template["human_verified"] is True
    assert template["update_diagram_success"] is True
    assert template["selected_fault_block_path"] == "Grid/Fault_B26_TEMP"


def test_b26_verified_branch_requirements_are_guarded_if_status_changes():
    evidence = _load(EVIDENCE_JSON)
    summary = _load(SUMMARY_JSON)
    template = _load(TEMPLATE)

    if template["human_verified_injection_point"]:
        assert template["safe_to_run_smoke_recommendation"] is True
        assert template["selected_fault_block_path"] == "Grid/Fault_B26_TEMP"
        assert template["selected_injection_block_path"]
        assert template["update_diagram_success"] is True
        assert template["fault_start_s"] == 0.5
        assert template["duration_s"] == 0.08
        assert template["fault_clear_s"] == 0.58
        assert template["original_network_connection_preserved"] is True
        assert template["no_floating_ports"] is True
        assert template["old_fault_still_near_b16"] is True
        assert summary["recommendation"] == "manual_review_supports_next_round_inventory_update"
    else:
        assert evidence["safe_to_run_smoke_recommendation"] is False
        assert summary["recommendation"] == "do_not_run_smoke"
        assert summary["failed_checks"]


def test_b26_docs_do_not_overstate_manual_review():
    combined = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in [EVIDENCE_MD, SUMMARY_MD, REVIEW_DOC]
    )
    forbidden = [
        "b26 smoke success = true",
        "b26 candidate label exported = true",
        "labels_exported = true",
        "gcn trained = true",
        "reranker retrained = true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]
    for phrase in forbidden:
        assert phrase not in combined
    assert "not emt" in combined
    assert "not direct frequency" in combined


def test_no_forbidden_artifacts_tracked_for_b26_manual_review():
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    forbidden = [
        ".slx",
        ".slxc",
        "slprj",
        ".mat",
        "raw_trajectories",
        "full_timeseries",
        "local_lab_copies",
    ]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden)]
