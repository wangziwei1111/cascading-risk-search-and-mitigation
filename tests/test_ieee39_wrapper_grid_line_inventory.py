from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_ieee39_wrapper_grid_line_inventory_schema_and_real_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv"
    assert path.exists()
    table = pd.read_csv(path)
    required = {
        "inventory_index",
        "block_name",
        "block_path",
        "parent_path",
        "block_type",
        "mask_type",
        "bus_from_candidate",
        "bus_to_candidate",
        "is_line_like_candidate",
        "note",
    }
    assert required.issubset(table.columns)
    assert len(table) >= 10
    assert table["block_path"].notna().all()
    assert table["block_path"].astype(str).str.startswith("IEEE39BusSystem_dynamic_experiment_wrapper/Grid/").all()
    assert table["is_line_like_candidate"].astype(str).str.lower().isin({"1", "true"}).all()
    for block_path in [
        "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B14 to B15",
        "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B15 to B16",
        "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B16 to B17",
    ]:
        assert block_path in set(table["block_path"].astype(str))
