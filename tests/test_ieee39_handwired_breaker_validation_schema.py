from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_ieee39_handwired_validation_summary_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    summary_json = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_validation_summary.json"
    inventory_csv = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_block_inventory.csv"
    assert summary_json.exists()
    assert inventory_csv.exists()

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    required = {
        "handwired_model_found",
        "handwired_model_loadable",
        "breaker_block_found",
        "trip_command_found",
        "no_fault_simulation_success",
        "single_line_trip_simulation_success",
        "trip_time_s",
        "measurement_extraction_status",
        "validation_passed",
        "validation_failure_reason",
        "handwired_model_committed",
    }
    assert required.issubset(payload)
    assert payload["handwired_model_committed"] is False

    inventory = pd.read_csv(inventory_csv)
    assert {"block_path", "candidate_role"}.issubset(inventory.columns)
