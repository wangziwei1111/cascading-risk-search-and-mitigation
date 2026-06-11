from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_ieee39_breaker_candidate_inventory_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_compatible_breaker_candidates.csv"
    assert path.exists()
    table = pd.read_csv(path)
    required = {
        "library_path",
        "block_name",
        "mask_type",
        "port_structure",
        "physical_port_count",
        "likely_compatible_with_l01",
        "requires_control_input",
        "note",
    }
    assert required.issubset(table.columns)
    assert len(table) > 0
    assert table["library_path"].astype(str).str.contains("Breaker|Switch", case=False, regex=True).any()
