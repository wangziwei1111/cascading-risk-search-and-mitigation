from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_ieee39_simlog_inventory_schema_and_candidates() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_simlog_tree_inventory.csv"
    json_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_simlog_tree_inventory.json"
    assert csv_path.exists()
    assert json_path.exists()

    table = pd.read_csv(csv_path)
    required = {
        "node_path",
        "node_name",
        "node_class",
        "depth",
        "has_series",
        "num_points",
        "series_unit",
        "candidate_signal_type",
    }
    assert required.issubset(table.columns)
    assert {"voltage", "speed", "rotor_angle"}.issubset(set(table["candidate_signal_type"].astype(str)))
    assert table["has_series"].astype(str).str.lower().isin({"1", "true"}).any()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["num_nodes"] >= len(table)
    assert payload["num_voltage_candidates"] > 0
    assert payload["num_speed_candidates"] > 0
    assert payload["num_rotor_angle_candidates"] > 0
