from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_ieee39_breaker_probe_summary_records_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/breaker_probe/breaker_probe_summary.csv"
    assert path.exists()
    table = pd.read_csv(path)
    required = {
        "probe_model_created",
        "candidate_block",
        "connection_success",
        "simulation_success",
        "timed_open_signal_applied",
        "compatible_for_wrapper_insertion",
        "error_message",
        "note",
    }
    assert required.issubset(table.columns)
    assert table["probe_model_created"].astype(str).str.lower().isin({"1", "true"}).any()
    assert table["compatible_for_wrapper_insertion"].astype(str).str.lower().isin({"0", "false", "1", "true"}).all()
