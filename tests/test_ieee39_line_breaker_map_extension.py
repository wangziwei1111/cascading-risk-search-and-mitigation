from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_ieee39_line_breaker_map_extension_preserves_existing_and_maps_new_lines() -> None:
    root = Path(__file__).resolve().parents[1]
    legacy_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv"
    extended_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extended.csv"
    summary_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extension_summary.json"
    inventory_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv"
    assert extended_path.exists()
    assert summary_path.exists()
    legacy = pd.read_csv(legacy_path)
    extended = pd.read_csv(extended_path)
    inventory = pd.read_csv(inventory_path)
    inventory_paths = set(inventory["block_path"].astype(str))

    for line_id in ["L01", "L02", "L03", "L04", "L05"]:
        old = legacy[legacy["line_id"].astype(str) == line_id].fillna("").iloc[0]
        new = extended[extended["line_id"].astype(str) == line_id].fillna("").iloc[0]
        assert old.to_dict() == new.to_dict()

    expected = {
        "L06": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B14 to B15",
        "L07": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B15 to B16",
        "L08": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B16 to B17",
    }
    for line_id, block_path in expected.items():
        row = extended[extended["line_id"].astype(str) == line_id].iloc[0]
        assert row["line_block_path"] == block_path
        assert block_path in inventory_paths
        assert row["mapping_status"] == "pilot_line_block_disable"
        assert "not_in_current_line_map" not in row["line_block_path"]

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["preserved_line_ids"] == ["L01", "L02", "L03", "L04", "L05"]
    assert {"L06", "L07", "L08"}.issubset(set(summary["newly_mapped_line_ids"]))
    assert "ascending inventory_index" in summary["mapping_rule"]
