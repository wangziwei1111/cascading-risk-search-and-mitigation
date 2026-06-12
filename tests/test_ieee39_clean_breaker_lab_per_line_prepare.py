from __future__ import annotations

import json
from pathlib import Path


def test_per_line_clean_breaker_lab_prepare_summary_schema_and_l03_target() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_per_line_prepare_summary.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "line_id",
        "source_wrapper_path",
        "target_clean_lab_path",
        "source_found",
        "target_created",
        "target_loadable",
        "contains_existing_L01_HandwiredTimedBreaker",
        "contains_existing_L02_HandwiredTimedBreaker",
        "contains_existing_L03_HandwiredTimedBreaker",
        "contains_existing_L04_HandwiredTimedBreaker",
        "clean_lab_committed",
        "note",
    }
    assert required.issubset(payload)
    assert payload["line_id"] == "L03"
    assert payload["target_clean_lab_path"].endswith("IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L03.slx")
    assert payload["source_found"] is True
    assert payload["target_created"] is True
    assert payload["target_loadable"] is True
    assert payload["clean_lab_committed"] is False
    assert payload["contains_existing_L03_HandwiredTimedBreaker"] is False
