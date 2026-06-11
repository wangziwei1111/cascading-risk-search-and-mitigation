from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_ieee39_signal_summary_does_not_treat_placeholders_as_measured() -> None:
    root = Path(__file__).resolve().parents[1]
    summary = pd.read_csv(root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_signal_summary.csv")
    required = {
        "measurement_extraction_status",
        "missing_signal_list",
        "min_voltage_pu",
        "min_frequency_hz",
        "max_speed_deviation",
        "frequency_source",
        "num_voltage_signals_found",
        "num_speed_signals_found",
        "num_rotor_angle_signals_found",
    }
    assert required.issubset(summary.columns)
    assert summary["measurement_extraction_status"].isin(["none", "partial", "voltage_only", "voltage_and_speed", "voltage_speed_angle", "full"]).all()
    measured = summary[summary["measurement_extraction_status"].isin(["voltage_only", "voltage_and_speed", "voltage_speed_angle", "full"])]
    assert not measured.empty
    assert measured["min_voltage_pu"].notna().any()
    assert not ((summary["min_voltage_pu"] == 1.0) & (summary["measurement_extraction_status"] == "none")).any()
    assert not ((summary["min_frequency_hz"] == 50.0) & (summary["frequency_source"].fillna("") == "")).any()
    debug = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_signal_extraction_debug.json"
    assert debug.exists()
