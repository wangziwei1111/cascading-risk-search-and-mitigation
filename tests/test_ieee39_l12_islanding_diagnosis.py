from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSIS_PATH = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/"
    "ieee39_l12_islanding_diagnosis.json"
)


def _payload() -> dict:
    return json.loads(DIAGNOSIS_PATH.read_text(encoding="utf-8"))


def test_l12_islanding_diagnosis_schema_and_status() -> None:
    payload = _payload()
    required = {
        "line_id",
        "line_block_path",
        "validation_passed",
        "simulation_success",
        "measurement_extraction_status",
        "training_ready_candidate",
        "timeout_or_error_message",
        "breaker_block_found",
        "trip_command_found",
        "breaker_near_line",
        "islanding_candidate",
        "removed_edge",
        "b19_component_after_l12_open",
        "component_size",
        "component_contains_reference_or_main_grid",
        "suspected_reason",
        "recommended_manual_checks",
        "recommended_next_action",
        "should_merge_as_training_ready",
        "should_retrain_reranker",
        "caveats",
    }
    assert required.issubset(payload)
    assert payload["line_id"] == "L12"
    assert payload["line_block_path"] == "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B19 to B16"
    assert payload["validation_passed"] is True
    assert payload["simulation_success"] is False
    assert payload["measurement_extraction_status"] == "simulation_timeout"
    assert payload["training_ready_candidate"] is False
    assert payload["breaker_block_found"] is True
    assert payload["trip_command_found"] is True
    assert payload["breaker_near_line"] is True
    assert payload["should_merge_as_training_ready"] is False
    assert payload["should_retrain_reranker"] is False


def test_l12_islanding_diagnosis_topology_and_manual_checks() -> None:
    payload = _payload()
    assert payload["islanding_candidate"] is True
    assert payload["removed_edge"] == ["B19", "B16"]
    assert "B19" in payload["b19_component_after_l12_open"]
    assert payload["component_size"] == len(payload["b19_component_after_l12_open"])
    assert payload["component_contains_reference_or_main_grid"] is False
    assert payload["recommended_manual_checks"]
    assert "special-case timeout label" in payload["recommended_next_action"]
    caveats = "\n".join(payload["caveats"]).lower()
    for required in [
        "phasor_rms, not emt",
        "generator_speed_proxy, not direct frequency",
        "pilot breaker-like validation, not engineering-grade protection",
        "not a verified stable or unstable conclusion",
    ]:
        assert required in caveats
