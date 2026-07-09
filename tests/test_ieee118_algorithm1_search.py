from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
ALG_RESULTS = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_algorithm1_eval_earlystop"
EARLY_FULLTRUTH = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
sys.path.insert(0, str(IEEE118))

from evaluate_ieee118_rts79_protocol_search import (  # noqa: E402
    METHOD_GCN_ALGORITHM1,
    METHOD_GCN_PATH_PROB,
    METHOD_PFW,
    METHOD_SECOND_ONLY,
    algorithm1_threshold_stats,
    budget_table,
    label_method,
    make_gcn_algorithm1_order,
    make_orders,
    make_pfw_order,
)


def _toy_score() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"path": "L001->L002", "first_line": "L001", "second_line": "L002", "p_shed_first": 0.6, "p_shed_second": 0.2, "path_product_score": 0.12, "critical": False, "relay_cascade": False, "total_load_shed_mw": 0.0, "full_cascade_path": "L001->L002"},
            {"path": "L001->L003", "first_line": "L001", "second_line": "L003", "p_shed_first": 0.6, "p_shed_second": 0.8, "path_product_score": 0.48, "critical": True, "relay_cascade": True, "total_load_shed_mw": 5.0, "full_cascade_path": "L001->L003"},
            {"path": "L002->L001", "first_line": "L002", "second_line": "L001", "p_shed_first": 0.4, "p_shed_second": 0.1, "path_product_score": 0.04, "critical": False, "relay_cascade": False, "total_load_shed_mw": 0.0, "full_cascade_path": "L002->L001"},
            {"path": "L002->L003", "first_line": "L002", "second_line": "L003", "p_shed_first": 0.4, "p_shed_second": 0.3, "path_product_score": 0.12, "critical": True, "relay_cascade": False, "total_load_shed_mw": 2.0, "full_cascade_path": "L002->L003"},
            {"path": "L003->L001", "first_line": "L003", "second_line": "L001", "p_shed_first": 0.7, "p_shed_second": 0.4, "path_product_score": 0.28, "critical": False, "relay_cascade": False, "total_load_shed_mw": 0.0, "full_cascade_path": "L003->L001"},
            {"path": "L003->L002", "first_line": "L003", "second_line": "L002", "p_shed_first": 0.7, "p_shed_second": 0.2, "path_product_score": 0.14, "critical": False, "relay_cascade": False, "total_load_shed_mw": 0.0, "full_cascade_path": "L003->L002"},
        ]
    )


def test_algorithm1_positive_candidates_precede_yp_fallback() -> None:
    score = _toy_score()
    y_p_first = {"L001": 0.1, "L002": 100.0, "L003": 0.2}
    y_p_second = {
        "L003": {"L001": 0.9, "L002": 0.8},
        "L001": {"L002": 100.0, "L003": 0.1},
        "L002": {"L001": 0.2, "L003": 0.1},
    }
    order = make_gcn_algorithm1_order(score, y_p_first, y_p_second, threshold=0.5)
    assert order[:2] == ["L003->L001", "L003->L002"]
    assert order.index("L001->L003") < order.index("L001->L002")
    assert order.index("L001->L002") < order.index("L002->L001")


def test_algorithm1_threshold_changes_positive_set() -> None:
    score = _toy_score()
    y_p_first = {"L001": 0.1, "L002": 100.0, "L003": 0.2}
    y_p_second = {first: {} for first in ["L001", "L002", "L003"]}
    low = make_gcn_algorithm1_order(score, y_p_first, y_p_second, threshold=0.3)
    high = make_gcn_algorithm1_order(score, y_p_first, y_p_second, threshold=0.9)
    assert low[0].startswith("L003->")
    assert high[0].startswith("L002->")


def test_pfw_order_uses_absolute_flow_scores() -> None:
    score = _toy_score()
    pfw_first = {"L001": 10.0, "L002": 30.0, "L003": 20.0}
    pfw_second = {
        "L002": {"L001": 1.0, "L003": 5.0},
        "L003": {"L001": 4.0, "L002": 2.0},
        "L001": {"L002": 9.0, "L003": 8.0},
    }
    order = make_pfw_order(score, pfw_first, pfw_second)
    assert order[:2] == ["L002->L003", "L002->L001"]
    assert order[-2:] == ["L001->L002", "L001->L003"]


def test_make_orders_retains_ablation_and_adds_algorithm1_and_pfw() -> None:
    score = _toy_score()
    y_p_first = {"L001": 0.1, "L002": 100.0, "L003": 0.2}
    y_p_second = {first: {} for first in ["L001", "L002", "L003"]}
    pfw_first = {"L001": 10.0, "L002": 30.0, "L003": 20.0}
    pfw_second = {first: {} for first in ["L001", "L002", "L003"]}
    orders = make_orders(score, y_p_first, y_p_second, pfw_first, pfw_second, [1], method_suffix="_earlystop", gcn_threshold=0.5)
    assert label_method(METHOD_GCN_ALGORITHM1, "_earlystop") in orders
    assert label_method(METHOD_GCN_PATH_PROB, "_earlystop") in orders
    assert label_method(METHOD_SECOND_ONLY, "_earlystop") in orders
    assert METHOD_PFW in orders


def test_threshold_sweep_summary_fields() -> None:
    score = _toy_score()
    truth = score[["path", "critical", "relay_cascade", "total_load_shed_mw", "full_cascade_path"]].copy()
    budgets = budget_table(len(truth))
    sweep = algorithm1_threshold_stats(
        score,
        {"L001": 0.1, "L002": 100.0, "L003": 0.2},
        {first: {} for first in ["L001", "L002", "L003"]},
        truth,
        budgets,
        [0.3, 0.5],
        method_name="GCN_Algorithm1",
    )
    assert {"gcn_threshold", "k1000_recall_critical", "k5000_precision_at_k", "num_gcn_positive_first_lines", "mean_num_gcn_positive_second_lines"}.issubset(sweep.columns)
    assert sweep.loc[sweep["gcn_threshold"] == 0.3, "num_gcn_positive_first_lines"].iloc[0] == 3
    assert sweep.loc[sweep["gcn_threshold"] == 0.5, "num_gcn_positive_first_lines"].iloc[0] == 2


def test_algorithm1_committed_summary_contains_required_methods() -> None:
    summary = pd.read_csv(ALG_RESULTS / "ieee118_algorithm1_earlystop_search_summary.csv")
    methods = set(summary["method"])
    assert {
        "RTS79_GCN_Algorithm1_reused_on_IEEE118_earlystop",
        "RTS79_GCN_path_prob_reused_on_IEEE118_earlystop",
        "RTS79_GCN_second_only_reused_on_IEEE118_earlystop",
        "PFW",
        "LODF_yP",
        "line_order",
        "random",
    }.issubset(methods)


def test_algorithm1_paths_are_valid_earlystop_paths() -> None:
    truth = pd.read_csv(EARLY_FULLTRUTH / "ieee118_fulltruth_summary.csv")
    valid_paths = set(truth.loc[truth["valid_ordered_n2"].astype(str).str.lower().isin({"true", "1", "yes"}), "path"].astype(str))
    first_summary = pd.read_csv(EARLY_FULLTRUTH / "ieee118_first_step_summary.csv")
    skipped = set(first_summary.loc[first_summary["first_step_critical"].astype(str).str.lower().isin({"true", "1", "yes"}), "first_line"].astype(str))
    top = pd.read_csv(ALG_RESULTS / "ieee118_algorithm1_earlystop_topk_paths.csv")
    alg = top.loc[top["method"] == "RTS79_GCN_Algorithm1_reused_on_IEEE118_earlystop"]
    assert set(alg["path"].astype(str)).issubset(valid_paths)
    assert skipped.isdisjoint(set(alg["first_line"].astype(str)))


def test_threshold_sweep_outputs_exist() -> None:
    sweep = pd.read_csv(ALG_RESULTS / "ieee118_algorithm1_threshold_sweep.csv")
    assert sweep["gcn_threshold"].tolist() == [0.3, 0.5, 0.7, 0.9]
    assert "num_gcn_positive_first_lines" in sweep.columns
    data = json.loads((ALG_RESULTS / "ieee118_algorithm1_threshold_sweep.json").read_text(encoding="utf-8"))
    assert len(data) == 4


def test_missing_algorithm1_local_file_error_is_clear(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(IEEE118 / "evaluate_ieee118_rts79_protocol_search.py"),
            "--dataset-npz",
            str(tmp_path / "missing.npz"),
            "--path-index-csv",
            str(tmp_path / "missing.csv"),
            "--fulltruth-csv",
            str(tmp_path / "missing_fulltruth.csv"),
            "--model-path",
            str(tmp_path / "missing.pt"),
            "--first-step-probabilities-csv",
            str(tmp_path / "missing_first.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "Missing IEEE118 full-truth CSV" in proc.stderr
