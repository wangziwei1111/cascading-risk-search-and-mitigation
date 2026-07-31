from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

from prospective_physical_oracle import (
    OnDemandCascadeOracle,
    run_frozen_adaptive_ordered_n2,
)
from run_ieee118_prospective_oracle import (
    build_prospective_stage_summary,
    parse_args,
)
from audit_ieee118_prospective_oracle import audit_prospective_queries


def _first_description(state: dict, first_line: str) -> dict:
    return {
        "converged": True,
        "critical": first_line == "L003",
        "total_load_shed_mw": 10.0 if first_line == "L003" else 0.0,
        "valid_second_lines": tuple(
            line for line in state["line_labels"] if line != first_line
        ),
    }


def _second_description(state: dict, first_line: str, second_line: str) -> dict:
    critical = state["path"] in {"L001->L002", "L004->L001"}
    return {
        "converged": True,
        "critical": critical,
        "relay_cascade": critical,
        "total_load_shed_mw": 25.0 if critical else 0.0,
        "error": "",
    }


def test_on_demand_oracle_reuses_s1_and_never_repeats_n2() -> None:
    first_calls: list[str] = []
    second_calls: list[str] = []
    labels = ("L001", "L002", "L003", "L004")

    def build_first(first_line: str) -> dict:
        first_calls.append(first_line)
        return {"first_line": first_line, "line_labels": labels}

    def build_second(first_state: dict, second_line: str) -> dict:
        path = f"{first_state['first_line']}->{second_line}"
        second_calls.append(path)
        return {"path": path}

    oracle = OnDemandCascadeOracle(
        line_labels=labels,
        first_state_builder=build_first,
        first_state_describer=_first_description,
        second_state_builder=build_second,
        second_state_describer=_second_description,
    )

    first = oracle.query("L001", "L002", stage="probe")
    repeated = oracle.query("L001", "L002", stage="fallback")
    second = oracle.query("L001", "L004", stage="fallback")

    assert first is repeated
    assert second is not None
    assert first_calls == ["L001"]
    assert second_calls == ["L001->L002", "L001->L004"]
    assert oracle.num_n1_state_constructions == 1
    assert oracle.num_new_n2_simulations == 2


def test_on_demand_oracle_early_stops_first_step_critical_prefix() -> None:
    second_calls = 0
    labels = ("L001", "L002", "L003")

    def build_second(first_state: dict, second_line: str) -> dict:
        nonlocal second_calls
        second_calls += 1
        return {"path": f"{first_state['first_line']}->{second_line}"}

    oracle = OnDemandCascadeOracle(
        line_labels=labels,
        first_state_builder=lambda first: {
            "first_line": first,
            "line_labels": labels,
        },
        first_state_describer=_first_description,
        second_state_builder=build_second,
        second_state_describer=_second_description,
    )

    assert oracle.query("L003", "L001", stage="probe") is None
    assert oracle.num_n1_state_constructions == 1
    assert oracle.num_new_n2_simulations == 0
    assert second_calls == 0
    assert oracle.first_step_rows[0]["first_step_critical"] is True


def test_resume_rows_are_replayed_without_new_n2_simulation() -> None:
    labels = ("L001", "L002", "L003")
    resumed = {
        "query_rank": 1,
        "path": "L001->L002",
        "first_line": "L001",
        "second_line": "L002",
        "search_stage": "probe",
        "converged": True,
        "critical": True,
        "relay_cascade": True,
        "total_load_shed_mw": 25.0,
        "error": "",
    }
    oracle = OnDemandCascadeOracle(
        line_labels=labels,
        first_state_builder=lambda first: {
            "first_line": first,
            "line_labels": labels,
        },
        first_state_describer=_first_description,
        second_state_builder=lambda *_: (_ for _ in ()).throw(
            AssertionError("resume must not repeat the N-2 simulation")
        ),
        second_state_describer=_second_description,
        resume_rows=[resumed],
        resume_first_step_rows=[
            {
                "first_line": "L001",
                "first_step_converged": True,
                "first_step_critical": False,
                "first_step_total_load_shed_mw": 0.0,
                "num_valid_second_lines": 2,
            }
        ],
    )

    assert oracle.query("L001", "L002", stage="fallback")["critical"] is True
    assert oracle.num_new_n2_simulations == 0
    assert oracle.num_unique_n2_queries == 1
    assert len(oracle.first_step_rows) == 1
    assert oracle.first_step_rows[0]["first_line"] == "L001"


def test_frozen_adaptive_search_uses_only_queried_oracle_outcomes() -> None:
    labels = ("L001", "L002", "L003", "L004")
    oracle = OnDemandCascadeOracle(
        line_labels=labels,
        first_state_builder=lambda first: {
            "first_line": first,
            "line_labels": labels,
        },
        first_state_describer=_first_description,
        second_state_builder=lambda state, second: {
            "path": f"{state['first_line']}->{second}"
        },
        second_state_describer=_second_description,
    )
    conditional = {
        first: {
            second: float(1.0 / (1 + abs(i - j)))
            for j, second in enumerate(labels)
            if second != first
        }
        for i, first in enumerate(labels)
    }

    result = run_frozen_adaptive_ordered_n2(
        first_line_scores={
            "L001": 1.0,
            "L002": 0.8,
            "L003": 0.6,
            "L004": 0.4,
        },
        line_labels=labels,
        gate_second_lines=("L002",),
        second_score_provider=lambda first: conditional[first],
        oracle=oracle,
        probes_per_second_line=2,
        promotion_min_positives=1,
        max_n2_queries=5,
    )

    assert result.promoted_second_lines == ("L002",)
    assert len(result.query_rows) == 5
    assert result.query_rows[0]["path"] == "L001->L002"
    assert result.query_rows[0]["critical"] is True
    assert oracle.num_new_n2_simulations == 5
    assert all("critical" in row for row in result.query_rows)


def test_completed_resume_replays_policy_and_preserves_promotions() -> None:
    labels = ("L001", "L002", "L003", "L004")

    def make_oracle(**kwargs) -> OnDemandCascadeOracle:
        return OnDemandCascadeOracle(
            line_labels=labels,
            first_state_builder=lambda first: {
                "first_line": first,
                "line_labels": labels,
            },
            first_state_describer=_first_description,
            second_state_builder=lambda state, second: {
                "path": f"{state['first_line']}->{second}"
            },
            second_state_describer=_second_description,
            **kwargs,
        )

    conditional = {
        first: {second: 0.5 for second in labels if second != first}
        for first in labels
    }
    search_args = {
        "first_line_scores": dict(zip(labels, (1.0, 0.8, 0.6, 0.4))),
        "line_labels": labels,
        "gate_second_lines": ("L002",),
        "second_score_provider": lambda first: conditional[first],
        "probes_per_second_line": 2,
        "promotion_min_positives": 1,
        "max_n2_queries": 5,
    }
    initial_oracle = make_oracle()
    initial = run_frozen_adaptive_ordered_n2(
        oracle=initial_oracle,
        **search_args,
    )
    resumed_oracle = make_oracle(
        resume_rows=initial.query_rows,
        resume_first_step_rows=initial.first_step_rows,
    )
    resumed = run_frozen_adaptive_ordered_n2(
        oracle=resumed_oracle,
        **search_args,
    )

    assert resumed.promoted_second_lines == initial.promoted_second_lines
    assert resumed.probe_paths == initial.probe_paths
    assert resumed.num_new_n2_simulations == 0
    assert resumed_oracle.num_policy_queries == 5


def test_prospective_cli_has_no_fulltruth_input() -> None:
    args = parse_args(["--seed", "20260709", "--max-n2-queries", "5"])
    assert args.seed == 20260709
    assert args.max_n2_queries == 5
    assert not any("fulltruth" in name for name in vars(args))
    assert args.gate_size == 26
    assert args.probes_per_second_line == 5
    assert args.promotion_min_positives == 1


def test_prospective_stage_summary_separates_relay_activity_from_label() -> None:
    table = pd.DataFrame(
        [
            {
                "search_stage": "probe",
                "critical": False,
                "relay_cascade": False,
                "has_overload_cascade": True,
                "total_load_shed_mw": 0.0,
                "error": "",
            },
            {
                "search_stage": "probe",
                "critical": True,
                "relay_cascade": True,
                "has_overload_cascade": True,
                "total_load_shed_mw": 20.0,
                "error": "",
            },
        ]
    )

    summary = build_prospective_stage_summary(table)

    assert summary.loc[0, "num_queries"] == 2
    assert summary.loc[0, "num_critical"] == 1
    assert summary.loc[0, "num_relay_cascade"] == 1
    assert summary.loc[0, "num_overload_relay_activity"] == 2
    assert summary.loc[0, "critical_precision"] == 0.5


def test_posthoc_audit_computes_recall_without_changing_query_order() -> None:
    truth = pd.DataFrame(
        [
            {"path": "L001->L002", "critical": True, "critical_mechanism": "relay_cascade", "total_load_shed_mw": 10.0},
            {"path": "L001->L003", "critical": False, "critical_mechanism": "non_critical", "total_load_shed_mw": 0.0},
            {"path": "L002->L001", "critical": True, "critical_mechanism": "island_only", "total_load_shed_mw": 20.0},
            {"path": "L002->L003", "critical": False, "critical_mechanism": "non_critical", "total_load_shed_mw": 0.0},
        ]
    )
    queries = pd.DataFrame(
        [
            {"query_rank": 1, "path": "L001->L002", "critical": True},
            {"query_rank": 2, "path": "L001->L003", "critical": False},
        ]
    )

    summary, curve, missed = audit_prospective_queries(queries, truth)

    assert summary["audit_mode"] == "posthoc_read_only"
    assert summary["num_truth_critical"] == 2
    assert summary["num_queried_critical"] == 1
    assert summary["critical_recall"] == 0.5
    assert summary["query_precision"] == 0.5
    assert summary["relay_cascade_recall"] == 1.0
    assert summary["captured_load_shed_ratio"] == pytest.approx(1.0 / 3.0)
    assert curve["candidate_evaluations"].tolist() == [1, 2]
    assert missed["path"].tolist() == ["L002->L001"]


def test_posthoc_audit_rejects_duplicate_query_paths() -> None:
    truth = pd.DataFrame(
        [{"path": "L001->L002", "critical": True, "critical_mechanism": "relay_cascade", "total_load_shed_mw": 1.0}]
    )
    queries = pd.DataFrame(
        [
            {"query_rank": 1, "path": "L001->L002", "critical": True},
            {"query_rank": 2, "path": "L001->L002", "critical": True},
        ]
    )

    with pytest.raises(ValueError, match="duplicate"):
        audit_prospective_queries(queries, truth)
