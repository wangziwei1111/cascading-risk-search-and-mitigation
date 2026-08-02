from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

from summarize_ieee118_global_rank_fusion import summarize_query_table  # noqa: E402
from tail_rank_fusion import weighted_global_path_rrf_ranking  # noqa: E402
from tail_rank_fusion import weighted_multi_global_path_rrf_ranking  # noqa: E402


def test_global_rrf_keeps_partial_union_unique_and_deterministic() -> None:
    first = pd.DataFrame(
        [
            {"path": "A->B", "first_line": "A", "second_line": "B"},
            {"path": "A->C", "first_line": "A", "second_line": "C"},
        ]
    )
    second = pd.DataFrame(
        [
            {"path": "A->C", "first_line": "A", "second_line": "C"},
            {"path": "B->C", "first_line": "B", "second_line": "C"},
        ]
    )

    fused = weighted_global_path_rrf_ranking(
        first, second, primary_weight=0.5, rrf_k=60.0
    )

    assert fused["path"].is_unique
    assert set(fused["path"]) == {"A->B", "A->C", "B->C"}
    assert fused.iloc[0]["path"] == "A->C"


def test_global_rrf_rejects_invalid_weight() -> None:
    table = pd.DataFrame(
        [{"path": "A->B", "first_line": "A", "second_line": "B"}]
    )
    with pytest.raises(ValueError, match="between zero and one"):
        weighted_global_path_rrf_ranking(table, table, primary_weight=1.1)


def test_multi_global_rrf_uses_all_rankings() -> None:
    first = pd.DataFrame(
        [{"path": "A->B", "first_line": "A", "second_line": "B"}]
    )
    second = pd.DataFrame(
        [{"path": "A->C", "first_line": "A", "second_line": "C"}]
    )
    third = pd.DataFrame(
        [{"path": "B->C", "first_line": "B", "second_line": "C"}]
    )

    fused = weighted_multi_global_path_rrf_ranking(
        [first, second, third], [0.7, 0.2, 0.1]
    )

    assert set(fused["path"]) == {"A->B", "A->C", "B->C"}
    assert fused.iloc[0]["path"] == "A->B"


def test_compact_summary_counts_only_fallback_stage() -> None:
    table = pd.DataFrame(
        [
            {
                "search_stage": "probe",
                "critical": True,
                "relay_cascade": False,
                "total_load_shed_mw": 10.0,
                "error": "",
            },
            {
                "search_stage": "gcn_pair_interaction_global_rrf_fallback",
                "critical": True,
                "relay_cascade": True,
                "total_load_shed_mw": 20.0,
                "error": "",
            },
        ]
    )

    summary = summarize_query_table(table)

    assert summary["critical"] == 2
    assert summary["fallback_queries"] == 1
    assert summary["fallback_critical"] == 1
    assert summary["fallback_relay"] == 1
    assert summary["fallback_load_shed_mw"] == pytest.approx(20.0)


def test_compact_summary_parses_csv_string_booleans() -> None:
    table = pd.DataFrame(
        [
            {
                "search_stage": "fallback",
                "critical": "False",
                "relay_cascade": "True",
                "total_load_shed_mw": 0.0,
                "error": "",
            }
        ]
    )

    summary = summarize_query_table(table)

    assert summary["fallback_critical"] == 0
    assert summary["fallback_relay"] == 1
