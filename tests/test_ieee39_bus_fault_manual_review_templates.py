from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans"


REQUIRED_FIELDS = {
    "target_bus",
    "reviewer",
    "review_date",
    "temp_model_path",
    "source_model_opened_read_only",
    "source_model_saved",
    "temporary_model_saved",
    "temporary_model_committed",
    "candidate_blocks_reviewed",
    "selected_injection_block_path",
    "selected_injection_port_description",
    "selected_fault_block_path",
    "fault_block_connected_in_parallel",
    "original_network_connection_preserved",
    "no_unintended_bypass",
    "no_floating_ports",
    "no_unintended_islanding",
    "update_diagram_attempted",
    "update_diagram_success",
    "update_diagram_error",
    "fault_start_s",
    "fault_clear_s",
    "duration_s",
    "measurement_signals_expected_available",
    "human_verified_injection_point",
    "safe_to_run_smoke_recommendation",
    "reviewer_notes",
    "screenshots_or_manual_evidence_paths",
    "next_action",
}


def _load_template(bus: str) -> dict:
    path = PLAN_DIR / f"manual_bus_fault_injection_review_template_{bus}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_manual_review_templates_and_script_exist() -> None:
    assert (ROOT / "scripts/gcn_search/collect_ieee39_bus_fault_manual_review.py").exists()
    for bus in ["B39", "B26"]:
        for suffix in ["json", "md"]:
            path = PLAN_DIR / f"manual_bus_fault_injection_review_template_{bus}.{suffix}"
            assert path.exists()
            assert path.stat().st_size > 0


def test_manual_review_template_defaults_are_conservative() -> None:
    for bus in ["B39", "B26"]:
        payload = _load_template(bus)
        assert set(payload) >= REQUIRED_FIELDS
        assert payload["target_bus"] == bus
        assert payload["human_verified_injection_point"] is False
        assert payload["safe_to_run_smoke_recommendation"] is False
        assert payload["source_model_saved"] is False
        assert payload["temporary_model_committed"] is False
        assert payload["next_action"] == "manual review required before smoke"
        assert payload["fault_start_s"] == 0.5
        assert payload["fault_clear_s"] == 0.58
        assert payload["duration_s"] == 0.08
        assert payload["candidate_blocks_reviewed"]


def test_manual_review_consolidation_default_is_do_not_run_smoke() -> None:
    summary_path = PLAN_DIR / "manual_review_consolidation_summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["preview_only"] is True
    assert payload["target_bus"] == "B39"
    assert payload["recommendation"] == "do_not_run_smoke"
    assert payload["human_verified_injection_point"] is False
    assert payload["safe_to_run_smoke_recommendation"] is False
    assert payload["inventory_modified"] is False
    assert payload["simulink_run"] is False
    assert payload["labels_exported"] is False
    assert payload["gcn_trained"] is False
    assert payload["reranker_retrained"] is False
    assert payload["formal_label_gate"] == "35 / 33 / 33"
    assert payload["v2_candidate_count"] == 40


def test_manual_review_markdown_templates_contain_candidate_blocks() -> None:
    b39 = (PLAN_DIR / "manual_bus_fault_injection_review_template_B39.md").read_text(encoding="utf-8")
    b26 = (PLAN_DIR / "manual_bus_fault_injection_review_template_B26.md").read_text(encoding="utf-8")
    for required in ["Grid/Bus39", "Grid/B39 to B1", "Grid/B9 to B39", "Generators/Gen1@Bus39"]:
        assert required in b39
    for required in ["Grid/Bus26_1", "Grid/Bus26_2", "Grid/B25 to B26", "Grid/B26 to B29"]:
        assert required in b26


def test_no_forbidden_bus_fault_temp_artifacts_are_tracked() -> None:
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
        "matlab_stdout",
    ]
    offenders = [path for path in tracked if any(token in path.lower() for token in forbidden_tokens)]
    assert offenders == []
