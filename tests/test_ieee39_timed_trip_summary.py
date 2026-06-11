from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_ieee39_pilot_trip_summary_distinguishes_timed_and_static() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_pilot_trip_implementation_summary.csv"
    json_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_pilot_trip_implementation_summary.json"
    assert csv_path.exists()
    assert json_path.exists()

    table = pd.read_csv(csv_path)
    required = {
        "line_id",
        "line_block_path",
        "inserted_switch_block_path",
        "control_signal_block_path",
        "trip_time_s",
        "trip_implementation",
        "physical_fault_or_breaker_action_executed",
        "training_ready_candidate",
        "implementation_status",
        "note",
    }
    assert required.issubset(table.columns)
    assert table["trip_implementation"].isin(["existing_breaker_control", "timed_controlled_switch", "static_topology_disable"]).all()

    static = table[table["trip_implementation"] == "static_topology_disable"]
    if not static.empty:
        assert not static["training_ready_candidate"].astype(str).str.lower().isin({"1", "true"}).any()
        assert static["implementation_status"].astype(str).str.contains("manual_required").any()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["trip_implementation"] in {"existing_breaker_control", "timed_controlled_switch", "static_topology_disable"}
