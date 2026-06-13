from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_all_remaining_merge_adds_only_successful_lines() -> None:
    root = Path(__file__).resolve().parents[1]
    merged_path = root / (
        "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/"
        "ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08_l09_l10_l11_to_l34.csv"
    )
    summary_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l11_to_l34_merge_summary.json"
    merged = pd.read_csv(merged_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected_success = [f"L{i:02d}" for i in range(11, 35) if i != 12]

    assert summary["merged_line_ids"] == expected_success
    assert summary["timeout_line_ids"] == ["L12"]
    assert summary["failed_line_ids"] == []
    assert summary["skipped_line_ids"] == []
    assert summary["num_training_ready_handwired_rows"] == 33
    assert "clean_lab_handwired_line_trip_L12" not in set(merged["test_case"].astype(str))
    for line_id in expected_success:
        row = merged[merged["test_case"].astype(str) == f"clean_lab_handwired_line_trip_{line_id}"].iloc[0]
        assert row["tripped_line"] == line_id
        assert row["source_model"] == f"clean_breaker_lab_{line_id}"
        assert row["measurement_extraction_status"] == "voltage_speed_angle"
        assert str(row["training_ready_candidate"]).lower() in {"1", "true"}
