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
    }
    assert required.issubset(summary.columns)
    assert summary["measurement_extraction_status"].isin(["partial", "unavailable"]).all()
    assert summary["missing_signal_list"].astype(str).str.contains("frequency").any()
    assert summary["min_voltage_pu"].isna().all()
    debug = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_signal_extraction_debug.json"
    assert debug.exists()
