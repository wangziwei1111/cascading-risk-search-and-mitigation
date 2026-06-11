from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_ieee39_line_port_inventory_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_port_inventory.csv"
    assert path.exists()
    table = pd.read_csv(path)
    required = {
        "line_id",
        "line_block_path",
        "block_type",
        "mask_type",
        "physical_port_count",
        "lconn_count",
        "rconn_count",
        "port_domain_guess",
        "switch_insertion_feasible",
        "note",
    }
    assert required.issubset(table.columns)
    row = table.iloc[0]
    assert row["line_id"] == "L01"
    assert int(row["physical_port_count"]) >= 4
    assert str(row["port_domain_guess"]) == "simscape_physical"
