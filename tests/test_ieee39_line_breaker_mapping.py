from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_ieee39_line_breaker_map_schema_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv"
    assert path.exists()
    table = pd.read_csv(path)
    required = {
        "line_id",
        "from_bus",
        "to_bus",
        "line_block_path",
        "breaker_block_path",
        "current_measurement_block_path",
        "voltage_measurement_block_path",
        "fault_injection_bus_or_line",
        "mapping_status",
        "note",
    }
    assert required.issubset(table.columns)
    assert len(table) >= 3
    assert table["mapping_status"].str.contains("pilot", case=False).any()
