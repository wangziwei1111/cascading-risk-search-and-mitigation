from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_all_remaining_clean_breaker_lab_validation_records_l11_l34() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.csv"
    table = pd.read_csv(path)
    expected_lines = {f"L{i:02d}" for i in range(11, 35)}
    assert set(table["line_id"].astype(str)) == expected_lines
    for column in [
        "clean_lab_model_found",
        "clean_lab_model_loadable",
        "breaker_block_found",
        "trip_command_found",
        "breaker_near_line",
        "validation_passed",
    ]:
        assert table[column].astype(str).str.lower().isin({"1", "true"}).all()
    assert table["clean_lab_model_committed"].astype(str).str.lower().isin({"0", "false"}).all()
    assert "not_in_current_line_map" not in set(table["line_block_path"].astype(str))


def test_all_remaining_compact_simulation_marks_l12_timeout_only() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_line_trip_summary.csv"
    table = pd.read_csv(path)
    expected_lines = {f"L{i:02d}" for i in range(11, 35)}
    assert set(table["tripped_line"].astype(str)) == expected_lines
    success = set(table.loc[table["training_ready_candidate"].astype(str).str.lower().isin({"1", "true"}), "tripped_line"].astype(str))
    assert success == expected_lines - {"L12"}
    l12 = table[table["tripped_line"].astype(str) == "L12"].iloc[0]
    assert l12["measurement_extraction_status"] == "simulation_timeout"
    assert str(l12["training_ready_candidate"]).lower() in {"0", "false"}
    assert "timed out" in str(l12["note"]).lower()
