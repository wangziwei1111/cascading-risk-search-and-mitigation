from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans"
DOCS = [
    "docs/ieee39_bus_fault_b39_manual_review_result.md",
    "docs/ieee39_bus_fault_gui_manual_checklist.md",
    "docs/ieee39_bus_fault_temp_lab_injection.md",
    "docs/ieee39_bus_fault_smoke_tests.md",
    "docs/gcn_pio_validation_log.md",
]


def test_b39_review_template_records_human_verified_injection_point() -> None:
    path = PLAN_DIR / "manual_bus_fault_injection_review_template_B39.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["human_verified_injection_point"] is True
    assert payload["safe_to_run_smoke_recommendation"] is True
    assert payload["selected_injection_block_path"] == "Grid/Bus39"
    assert payload["selected_fault_block_path"] == "Grid/Fault_B39_TEMP"
    assert "Bus39 physical node" in payload["selected_injection_port_description"]
    assert payload["fault_block_connected_in_parallel"] is True
    assert payload["original_network_connection_preserved"] is True
    assert payload["no_unintended_bypass"] is True
    assert payload["no_floating_ports"] is True
    assert payload["no_unintended_islanding"] is True
    assert payload["update_diagram_attempted"] is True
    assert payload["update_diagram_success"] is True
    assert payload["update_diagram_error"] == ""
    assert payload["fault_start_s"] == 0.5
    assert payload["fault_clear_s"] == 0.58
    assert payload["duration_s"] == 0.08
    assert payload["measurement_signals_expected_available"] is True
    assert payload["source_model_saved"] is False
    assert payload["temporary_model_committed"] is False


def test_b39_consolidation_allows_next_round_without_running_smoke() -> None:
    path = PLAN_DIR / "manual_review_consolidation_summary.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["recommendation"] != "do_not_run_smoke"
    assert payload["recommendation"] == "manual_review_supports_next_round_inventory_update"
    assert payload["failed_checks"] == []
    assert payload["human_verified_injection_point"] is True
    assert payload["safe_to_run_smoke_recommendation"] is True
    assert payload["simulink_run"] is False
    assert payload["labels_exported"] is False
    assert payload["gcn_trained"] is False
    assert payload["reranker_retrained"] is False
    assert payload["formal_label_gate"] == "35 / 33 / 33"
    assert payload["v2_candidate_count"] == 40


def test_b39_evidence_doc_records_manual_result_and_boundaries() -> None:
    text = (ROOT / "docs/ieee39_bus_fault_b39_manual_review_result.md").read_text(encoding="utf-8").lower()
    for required in [
        "simscapeblock",
        "busbar",
        "grid/fault_b39_temp",
        "bus39 port 1",
        "b9 to b39",
        "bus16_1",
        "b16 to b17",
        "update diagram passed",
        "fault_start_time = 0.5 s",
        "fault_duration = 0.08 s",
        "not smoke success",
        "35 / 33 / 33",
        "v2 candidate count remains `40`",
    ]:
        assert required in text


def test_b39_manual_review_docs_do_not_overclaim() -> None:
    joined = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for forbidden in [
        "b39 smoke success",
        "smoke success completed",
        "exported bus-fault labels",
        "trained gcn model",
        "reranker was retrained",
        "is a final dynamic performance conclusion",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "engineering-grade protection completed",
    ]:
        assert forbidden not in joined


def test_no_forbidden_bus_fault_review_artifacts_are_tracked() -> None:
    tracked = subprocess.check_output(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    forbidden_tokens = [
        ".slx",
        ".slxc",
        ".mat",
        "slprj",
        "raw_trajectories",
        "full_timeseries",
        "local_lab_copies",
    ]
    offenders = [path for path in tracked if any(token in path.lower() for token in forbidden_tokens)]
    assert offenders == []
