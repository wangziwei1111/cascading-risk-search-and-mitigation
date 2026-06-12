from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_batch_clean_breaker_lab_validation_schema_allows_unwired_lines() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.csv"
    assert path.exists()
    table = pd.read_csv(path)
    required = {
        "line_id",
        "line_block_path",
        "clean_lab_model_path",
        "clean_lab_model_found",
        "clean_lab_model_loadable",
        "breaker_block_name",
        "breaker_block_found",
        "trip_command_name",
        "trip_command_found",
        "validation_passed",
        "validation_failure_reason",
        "clean_lab_model_committed",
    }
    assert required.issubset(table.columns)
    assert set(table["line_id"].astype(str)) == {"L04", "L05"}
    for line_id in ["L04", "L05"]:
        row = table[table["line_id"].astype(str) == line_id].iloc[0]
        assert str(row["clean_lab_model_found"]).lower() in {"1", "true"}
        assert str(row["clean_lab_model_loadable"]).lower() in {"1", "true"}
        assert str(row["breaker_block_found"]).lower() in {"0", "false"}
        assert str(row["trip_command_found"]).lower() in {"0", "false"}
        assert str(row["validation_passed"]).lower() in {"0", "false"}
        assert f"missing breaker block named {line_id}_HandwiredTimedBreaker".lower() in str(row["validation_failure_reason"]).lower()
        assert str(row["clean_lab_model_committed"]).lower() in {"0", "false"}
