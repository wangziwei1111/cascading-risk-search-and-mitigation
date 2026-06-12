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
