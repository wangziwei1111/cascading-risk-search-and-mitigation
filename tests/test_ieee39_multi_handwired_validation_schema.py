from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_multi_handwired_validation_schema_and_mixed_status() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv"
    table = pd.read_csv(path)
    required = {
        "line_id",
        "line_block_path",
        "breaker_block_name",
        "breaker_block_found",
        "trip_command_name",
        "trip_command_found",
        "validation_passed",
        "validation_failure_reason",
        "handwired_model_committed",
    }
    assert required.issubset(table.columns)
    assert "L01" in set(table["line_id"].astype(str))
    selected = table[table["line_id"].astype(str).isin(["L01", "L02", "L03", "L04"])]
    assert len(selected) == 4
    assert selected["breaker_block_found"].astype(str).str.lower().isin({"1", "true"}).all()
    assert selected["trip_command_found"].astype(str).str.lower().isin({"1", "true"}).all()
    assert selected["validation_passed"].astype(str).str.lower().isin({"1", "true"}).all()
