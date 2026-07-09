from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

from analyze_ieee118_s0_first_probability_bottleneck import (
    aggregate_first_line_suppression,
    build_probability_distribution,
    mechanism_summary,
    rank_score_table,
    s0_label_conflict_summary,
    suppressed_masks,
    topk_overlap,
)


def toy_score() -> pd.DataFrame:
    rows = [
        {"path": "L001->L002", "first_line": "L001", "second_line": "L002", "critical": True, "relay_cascade": True, "critical_mechanism": "relay_cascade", "total_load_shed_mw": 5.0, "p_shed_first": 0.01, "p_shed_second": 0.99, "path_product_score": 0.0099},
        {"path": "L003->L004", "first_line": "L003", "second_line": "L004", "critical": True, "relay_cascade": False, "critical_mechanism": "island_only", "total_load_shed_mw": 2.0, "p_shed_first": 0.9, "p_shed_second": 0.5, "path_product_score": 0.45},
        {"path": "L005->L006", "first_line": "L005", "second_line": "L006", "critical": False, "relay_cascade": False, "critical_mechanism": "", "total_load_shed_mw": 0.0, "p_shed_first": 0.8, "p_shed_second": 0.4, "path_product_score": 0.32},
        {"path": "L001->L007", "first_line": "L001", "second_line": "L007", "critical": True, "relay_cascade": True, "critical_mechanism": "relay_cascade", "total_load_shed_mw": 8.0, "p_shed_first": 0.01, "p_shed_second": 0.98, "path_product_score": 0.0098},
        {"path": "L008->L009", "first_line": "L008", "second_line": "L009", "critical": False, "relay_cascade": False, "critical_mechanism": "", "total_load_shed_mw": 0.0, "p_shed_first": 0.7, "p_shed_second": 0.1, "path_product_score": 0.07},
        {"path": "L010->L011", "first_line": "L010", "second_line": "L011", "critical": False, "relay_cascade": False, "critical_mechanism": "", "total_load_shed_mw": 0.0, "p_shed_first": 0.6, "p_shed_second": 0.05, "path_product_score": 0.03},
    ]
    return rank_score_table(pd.DataFrame(rows))


def test_rank_gap_and_suppressed_definition() -> None:
    score = toy_score()
    low_first_high_second = score.loc[score["path"].eq("L001->L002")].iloc[0]
    assert int(low_first_high_second["second_only_rank"]) == 1
    assert int(low_first_high_second["path_prob_rank"]) > int(low_first_high_second["second_only_rank"])
    assert int(low_first_high_second["rank_gap"]) == int(low_first_high_second["path_prob_rank"] - low_first_high_second["second_only_rank"])
    suppressed_a, suppressed_b = suppressed_masks(score)
    assert suppressed_a.dtype == bool
    assert suppressed_b.dtype == bool


def test_first_line_aggregation_fields() -> None:
    score = toy_score()
    suppressed = score["first_line"].eq("L001")
    summary = aggregate_first_line_suppression(score, suppressed)
    row = summary.loc[summary["first_line"].eq("L001")].iloc[0]
    assert int(row["num_suppressed_critical"]) == 2
    assert int(row["num_suppressed_relay"]) == 2
    assert "L001->L002" in row["representative_paths"]
    assert json.loads(row["mechanism_distribution"]) == {"relay_cascade": 2}


def test_distribution_and_overlap_fields() -> None:
    score = toy_score()
    suppressed_a = score["first_line"].eq("L001")
    suppressed_b = score["path"].eq("L001->L007")
    distribution = build_probability_distribution(score, suppressed_a, suppressed_b)
    assert {
        "subset",
        "count",
        "mean_p_first",
        "median_p_first",
        "mean_p_second",
        "mean_path_prob_score",
    }.issubset(distribution.columns)
    overlap = topk_overlap(score, [2, 4])
    assert {
        "K",
        "overlap_count",
        "path_prob_only_critical_hits",
        "second_only_only_critical_hits",
        "path_prob_only_mean_p_first",
        "second_only_only_mean_p_first",
    }.issubset(overlap.columns)


def test_s0_label_conflict_summary_identifies_valid_n2_negative_first_lines(tmp_path: Path) -> None:
    score = toy_score()
    first = pd.DataFrame(
        {
            "first_line": ["L001", "L003", "L005", "L008", "L010"],
            "first_step_critical": [False, True, False, False, False],
        }
    )
    first_path = tmp_path / "ieee118_first_step_summary.csv"
    first.to_csv(first_path, index=False)
    probs = pd.DataFrame(
        {
            "line_label": ["L001", "L003", "L005", "L008", "L010"],
            "p_shed_first": [0.01, 0.9, 0.8, 0.7, 0.6],
        }
    )
    prob_path = tmp_path / "first_prob.csv"
    probs.to_csv(prob_path, index=False)
    summary = s0_label_conflict_summary(score, first_path, prob_path)
    row = summary.iloc[0]
    assert int(row["num_valid_n2_paths_with_first_step_positive_label"]) == 1
    assert int(row["num_valid_n2_paths_with_first_step_negative_label"]) == len(score) - 1


def test_mechanism_summary_fields() -> None:
    score = toy_score()
    mech = mechanism_summary(score, score["first_line"].eq("L001"))
    assert {
        "mechanism",
        "num_paths",
        "num_critical",
        "mean_p_first",
        "median_p_second",
        "path_prob_top1000_hits",
        "second_only_top1000_hits",
        "suppressed_count",
        "suppressed_ratio",
        "mean_rank_gap",
    }.issubset(mech.columns)


def test_missing_local_artifact_error_is_clear(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(IEEE118 / "analyze_ieee118_s0_first_probability_bottleneck.py"),
            "--fulltruth-csv",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "Missing full-truth CSV" in proc.stderr
    assert "will not regenerate OPA full-truth" in proc.stderr


def test_committed_diagnostic_outputs_exist_when_artifact_present() -> None:
    out = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup" / "s0_bottleneck_diagnostics"
    if not out.exists():
        return
    for name in [
        "suppressed_critical_paths_top.csv",
        "first_line_s0_suppression_summary.csv",
        "s0_probability_distribution_summary.csv",
        "s0_label_conflict_summary.csv",
        "path_prob_vs_second_only_overlap.csv",
        "mechanism_s0_bottleneck_summary.csv",
        "s0_first_probability_bottleneck_diagnostics.json",
        "s0_first_probability_bottleneck_readme.md",
    ]:
        assert (out / name).exists()


def test_no_large_diagnostic_artifacts_are_tracked() -> None:
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    forbidden = [
        path
        for path in tracked
        if "s0_bottleneck_diagnostics" in path
        and (
            path.endswith(".npz")
            or path.endswith(".pt")
            or "full_score_table" in path
            or "full_predictions" in path
        )
    ]
    assert forbidden == []
