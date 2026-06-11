from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_ieee39_real_fault_summary_schema_and_flags() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv"
    table = pd.read_csv(path)
    required = {
        "schema_only",
        "simulation_mode",
        "trip_implementation",
        "fault_configuration_status",
        "measurement_extraction_status",
        "training_ready_candidate",
        "timeout_or_error_message",
    }
    assert required.issubset(table.columns)
    assert (table["schema_only"].astype(str).str.lower().isin(["0", "false"])).all()
    assert (table["simulation_success"].astype(str).str.lower().isin(["1", "true"])).any()
    assert (table["physical_fault_or_breaker_action_executed"].astype(str).str.lower().isin(["1", "true"])).sum() >= 2
    static = table[table["trip_implementation"].astype(str) == "static_topology_disable"]
    assert not static.empty
    assert not static["training_ready_candidate"].astype(str).str.lower().isin(["1", "true"]).any()
