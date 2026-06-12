from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_handwired_fault_summary_merge_preserves_base_and_adds_non_duplicate_lines() -> None:
    root = Path(__file__).resolve().parents[1]
    merged = pd.read_csv(root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_multi_handwired.csv")
    assert "no_fault_sanity" in set(merged["test_case"].astype(str))
    assert "three_phase_fault_clear" in set(merged["test_case"].astype(str))
    assert "relay_trip_test" in set(merged["test_case"].astype(str))
    assert "single_line_trip" in set(merged["test_case"].astype(str))
    assert "handwired_line_trip_L01" not in set(merged["test_case"].astype(str))
    assert {"handwired_line_trip_L02", "handwired_line_trip_L03", "handwired_line_trip_L04"}.issubset(
        set(merged["test_case"].astype(str))
    )
    summary = json.loads(
        (root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_multi_handwired_merge_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["static_topology_disable_overwrote_handwired"] is False


def test_clean_lab_l02_merge_adds_training_ready_row_without_promoting_old_timeout() -> None:
    root = Path(__file__).resolve().parents[1]
    merged = pd.read_csv(root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02.csv")
    clean_l02 = merged[merged["test_case"].astype(str) == "clean_lab_handwired_line_trip_L02"].iloc[0]
    assert clean_l02["tripped_line"] == "L02"
    assert clean_l02["source_model"] == "clean_breaker_lab"
    assert clean_l02["trip_implementation"] == "handwired_timed_breaker"
    assert str(clean_l02["training_ready_candidate"]).lower() in {"1", "true"}

    old_l02 = merged[merged["test_case"].astype(str) == "handwired_line_trip_L02"].iloc[0]
    assert str(old_l02["training_ready_candidate"]).lower() in {"0", "false"}

    summary = json.loads(
        (root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_merge_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["num_training_ready_handwired_rows"] == 2
    assert summary["num_training_ready_handwired_rows_by_line"] == {"L01": 1, "L02": 1}
