import sys
from pathlib import Path

import pandas as pd
import pytest

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from case_adapter import (
    build_case_adapter,
    run_initial_dcopf_for_case,
    search_ordered_n2_paths_for_case,
    simulate_cascade_path_for_case,
)


def test_ieee118_case_loads_with_three_digit_line_labels():
    adapter = build_case_adapter("ieee118")

    assert adapter.case_name == "ieee118"
    assert adapter.num_branches == 186
    assert adapter.line_labels[:3] == ("L001", "L002", "L003")
    assert adapter.line_label_to_index_1based("L001") == 1
    assert adapter.line_label_to_index_1based("L186") == 186


def test_ieee118_initial_dcopf_converges():
    state = run_initial_dcopf_for_case("ieee118")

    assert state.case["success"]
    assert state.branch_table["line_label"].iloc[0] == "L001"
    assert state.branch_table["loading_ratio"].max() >= 0.0


def test_ieee118_single_active_outage_runs():
    result = simulate_cascade_path_for_case("ieee118", ["L001"], beta=1.2, security_limit=1.0)

    assert result.converged
    assert result.initial_outage_sequence == ("L001",)
    assert "L001" in result.final_outage_labels
    assert result.total_load_shed_mw >= 0.0
    assert result.final_max_loading_ratio >= 0.0


def test_ieee118_small_ordered_n2_search_outputs_structured_rows():
    table = search_ordered_n2_paths_for_case("ieee118", num_paths=3, seed=20260708)

    assert isinstance(table, pd.DataFrame)
    assert len(table) == 3
    assert set(
        [
            "path",
            "first_line",
            "second_line",
            "converged",
            "critical",
            "total_load_shed_mw",
            "final_max_loading_ratio",
            "final_outage_labels",
            "error",
        ]
    ).issubset(table.columns)
    assert table["first_line"].str.match(r"^L\d{3}$").all()
    assert table["second_line"].str.match(r"^L\d{3}$").all()


def test_rts79_adapter_preserves_legacy_two_digit_aliases():
    adapter = build_case_adapter("rts79")

    assert adapter.line_label_to_index_1based("L001") == 1
    assert adapter.line_label_to_index_1based("L01") == 1
    assert adapter.legacy_line_labels[:3] == ("L01", "L02", "L03")
