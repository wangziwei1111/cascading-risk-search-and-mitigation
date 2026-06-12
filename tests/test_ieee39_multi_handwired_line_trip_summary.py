from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_multi_handwired_line_trip_summary_flags_passed_and_failed_lines() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_multi_handwired_line_trip_summary.csv"
    table = pd.read_csv(path)
    required = {
        "test_case",
        "simulation_success",
        "physical_fault_or_breaker_action_executed",
        "trip_implementation",
        "training_ready_candidate",
        "measurement_extraction_status",
        "tripped_line",
    }
    assert required.issubset(table.columns)
    l01 = table[table["test_case"].astype(str) == "handwired_line_trip_L01"].iloc[0]
    assert str(l01["simulation_success"]).lower() in {"1", "true"}
    assert l01["trip_implementation"] == "handwired_timed_breaker"
    assert str(l01["training_ready_candidate"]).lower() in {"1", "true"}
    failed = table[table["tripped_line"].astype(str).isin(["L02", "L03", "L04"])]
    assert not failed.empty
    assert not failed["training_ready_candidate"].astype(str).str.lower().isin({"1", "true"}).any()
