from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_ieee39_timed_switch_insertion_summary_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_timed_switch_insertion_summary.csv"
    json_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_timed_switch_insertion_summary.json"
    assert csv_path.exists()
    assert json_path.exists()
    table = pd.read_csv(csv_path)
    required = {
        "line_id",
        "line_block_path",
        "trip_time_s",
        "insertion_attempted",
        "insertion_success",
        "connection_verified",
        "wrapper_saved",
        "trip_implementation",
        "physical_fault_or_breaker_action_executed",
        "training_ready_candidate",
        "note",
    }
    assert required.issubset(table.columns)
    row = table.iloc[0]
    if not bool(row["insertion_success"]):
        assert row["trip_implementation"] == "static_topology_disable"
        assert not bool(row["training_ready_candidate"])
        assert "manual_required" in str(row["note"])

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["trip_implementation"] in {"static_topology_disable", "timed_controlled_switch", "existing_breaker_control"}
