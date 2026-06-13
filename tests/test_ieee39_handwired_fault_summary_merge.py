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


def test_clean_lab_l03_merge_adds_training_ready_row_without_overwriting_l02() -> None:
    root = Path(__file__).resolve().parents[1]
    merged = pd.read_csv(root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03.csv")
    clean_l03 = merged[merged["test_case"].astype(str) == "clean_lab_handwired_line_trip_L03"].iloc[0]
    assert clean_l03["tripped_line"] == "L03"
    assert clean_l03["source_model"] == "clean_breaker_lab_L03"
    assert clean_l03["trip_implementation"] == "handwired_timed_breaker"
    assert str(clean_l03["training_ready_candidate"]).lower() in {"1", "true"}

    assert "clean_lab_handwired_line_trip_L02" in set(merged["test_case"].astype(str))
    summary = json.loads(
        (root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l03_merge_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["num_training_ready_handwired_rows"] == 3
    assert summary["num_training_ready_handwired_rows_by_line"] == {"L01": 1, "L02": 1, "L03": 1}


def test_clean_lab_l04_l05_merge_adds_batch_training_ready_rows() -> None:
    root = Path(__file__).resolve().parents[1]
    merged = pd.read_csv(root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05.csv")
    test_cases = set(merged["test_case"].astype(str))
    assert {"clean_lab_handwired_line_trip_L04", "clean_lab_handwired_line_trip_L05"}.issubset(test_cases)
    for line_id in ["L04", "L05"]:
        row = merged[merged["test_case"].astype(str) == f"clean_lab_handwired_line_trip_{line_id}"].iloc[0]
        assert row["tripped_line"] == line_id
        assert row["source_model"] == f"clean_breaker_lab_{line_id}"
        assert row["trip_implementation"] == "handwired_timed_breaker"
        assert row["measurement_extraction_status"] == "voltage_speed_angle"
        assert str(row["training_ready_candidate"]).lower() in {"1", "true"}

    summary = json.loads(
        (root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l04_l05_merge_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["num_training_ready_handwired_rows"] == 5
    assert summary["num_training_ready_handwired_rows_by_line"] == {"L01": 1, "L02": 1, "L03": 1, "L04": 1, "L05": 1}


def test_clean_lab_l06_l07_l08_merge_adds_batch_training_ready_rows() -> None:
    root = Path(__file__).resolve().parents[1]
    merged = pd.read_csv(root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary_with_clean_lab_l02_l03_l04_l05_l06_l07_l08.csv")
    test_cases = set(merged["test_case"].astype(str))
    assert {
        "clean_lab_handwired_line_trip_L06",
        "clean_lab_handwired_line_trip_L07",
        "clean_lab_handwired_line_trip_L08",
    }.issubset(test_cases)
    for line_id in ["L06", "L07", "L08"]:
        row = merged[merged["test_case"].astype(str) == f"clean_lab_handwired_line_trip_{line_id}"].iloc[0]
        assert row["tripped_line"] == line_id
        assert row["source_model"] == f"clean_breaker_lab_{line_id}"
        assert row["trip_implementation"] == "handwired_timed_breaker"
        assert row["measurement_extraction_status"] == "voltage_speed_angle"
        assert str(row["training_ready_candidate"]).lower() in {"1", "true"}

    summary = json.loads(
        (root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_l06_l07_l08_merge_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["num_training_ready_handwired_rows"] == 8
    assert summary["num_training_ready_handwired_rows_by_line"] == {
        "L01": 1,
        "L02": 1,
        "L03": 1,
        "L04": 1,
        "L05": 1,
        "L06": 1,
        "L07": 1,
        "L08": 1,
    }
