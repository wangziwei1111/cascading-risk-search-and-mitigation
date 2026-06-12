from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_clean_breaker_lab_validation_summary_schema_and_valid_l02() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_validation_summary.csv"
    assert path.exists()
    table = pd.read_csv(path)
    required = {
        "line_id",
        "line_block_path",
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
    l02 = table[table["line_id"].astype(str) == "L02"].iloc[0]
    assert str(l02["clean_lab_model_found"]).lower() in {"1", "true"}
    assert str(l02["clean_lab_model_loadable"]).lower() in {"1", "true"}
    assert str(l02["breaker_block_found"]).lower() in {"1", "true"}
    assert str(l02["trip_command_found"]).lower() in {"1", "true"}
    assert str(l02["validation_passed"]).lower() in {"1", "true"}
    assert str(l02["validation_failure_reason"]).lower() in {"", "nan"}
    assert str(l02["clean_lab_model_committed"]).lower() in {"0", "false"}
