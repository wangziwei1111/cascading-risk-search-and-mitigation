from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_ieee39_full_line_map_preserves_verified_lines_and_extends_remaining() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv"
    summary_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full_summary.json"
    inventory_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv"
    assert csv_path.exists()
    assert summary_path.exists()
    table = pd.read_csv(csv_path)
    inventory = pd.read_csv(inventory_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    expected_lines = {f"L{i:02d}" for i in range(1, 35)}
    assert set(table["line_id"].astype(str)) == expected_lines
    assert summary["preserved_line_ids"] == [f"L{i:02d}" for i in range(1, 11)]
    assert summary["newly_mapped_line_ids"] == [f"L{i:02d}" for i in range(11, 35)]
    assert summary["num_preserved_lines"] == 10
    assert summary["num_newly_mapped_lines"] == 24
    assert summary["warnings"] == []

    inventory_paths = set(inventory["block_path"].astype(str))
    assert set(table["line_block_path"].astype(str)).issubset(inventory_paths)
    assert table["line_block_path"].astype(str).is_unique

    expected_tail = {
        "L11": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B18 to B17",
        "L34": "IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B9 to B8",
    }
    for line_id, line_path in expected_tail.items():
        row = table[table["line_id"].astype(str) == line_id].iloc[0]
        assert row["line_block_path"] == line_path
