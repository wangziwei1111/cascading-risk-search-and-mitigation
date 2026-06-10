from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_ieee39_fault_test_summary_distinguishes_physical_rows() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv"
    assert path.exists()
    table = pd.read_csv(path)
    required = {
        "test_case",
        "simulation_success",
        "physical_fault_or_breaker_action_executed",
        "fault_type",
        "min_voltage_pu",
        "max_voltage_pu",
        "min_frequency_hz",
        "max_frequency_hz",
        "max_speed_deviation",
        "max_rotor_angle_separation_deg",
        "trip_time_s",
        "note",
    }
    assert required.issubset(table.columns)
    assert "no_fault_sanity" in set(table["test_case"])
    assert table["physical_fault_or_breaker_action_executed"].astype(bool).any()
