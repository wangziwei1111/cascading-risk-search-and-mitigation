from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
SCALEUP = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup"
TARGETS = SCALEUP / "strict_fragility_targets"
EVAL = SCALEUP / "strict_fragility_eval"
sys.path.insert(0, str(IEEE118))

from build_ieee118_strict_fragility_targets import add_ratios_and_composite, build_labels, require_file, target_name, topq_labels
from evaluate_ieee118_strict_fragility_path_prob import build_comparison, evaluate_ranked, ranked_by_score
from train_ieee118_strict_fragility_gcn import resolve_weight


def toy_line_stats() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"seed": 1, "line_label": "L001", "line_index": 0, "first_step_critical": False, "first_step_direct_shed_label": 0, "loss_mask": True, "critical_count": 5, "relay_cascade_count": 1, "max_load_shed_mw": 20.0, "sum_load_shed_mw": 25.0, "mean_load_shed_mw": 5.0, "num_valid_second_paths": 10, "source": "toy"},
            {"seed": 1, "line_label": "L002", "line_index": 1, "first_step_critical": False, "first_step_direct_shed_label": 0, "loss_mask": True, "critical_count": 3, "relay_cascade_count": 4, "max_load_shed_mw": 10.0, "sum_load_shed_mw": 30.0, "mean_load_shed_mw": 3.0, "num_valid_second_paths": 10, "source": "toy"},
            {"seed": 1, "line_label": "L003", "line_index": 2, "first_step_critical": False, "first_step_direct_shed_label": 0, "loss_mask": True, "critical_count": 1, "relay_cascade_count": 0, "max_load_shed_mw": 40.0, "sum_load_shed_mw": 40.0, "mean_load_shed_mw": 1.0, "num_valid_second_paths": 10, "source": "toy"},
            {"seed": 1, "line_label": "L004", "line_index": 3, "first_step_critical": True, "first_step_direct_shed_label": 1, "loss_mask": False, "critical_count": 99, "relay_cascade_count": 99, "max_load_shed_mw": 99.0, "sum_load_shed_mw": 99.0, "mean_load_shed_mw": 99.0, "num_valid_second_paths": 10, "source": "toy"},
        ]
    )


def test_target_name_and_topq_labels_are_stable() -> None:
    values = pd.Series([10.0, 5.0, 1.0, 99.0])
    mask = pd.Series([True, True, True, False])
    labels = topq_labels(values, 0.34, mask)
    assert target_name("critical_count_topq", 0.10) == "critical_count_top10"
    assert labels.tolist() == [1, 1, 0, 0]


def test_strict_label_definitions_and_first_step_exclusion() -> None:
    stats = add_ratios_and_composite(toy_line_stats())
    labeled, summaries = build_labels(
        stats,
        ["critical_count_topq", "relay_count_topq", "max_shed_topq", "composite_topq"],
        [1 / 3],
    )
    row_by_line = labeled.set_index("line_label")
    assert row_by_line.loc["L001", "critical_count_top33"] == 1
    assert row_by_line.loc["L002", "relay_count_top33"] == 1
    assert row_by_line.loc["L003", "max_shed_top33"] == 1
    assert row_by_line.loc["L004", "critical_count_top33"] == 0
    assert not bool(row_by_line.loc["L004", "loss_mask"])
    assert all(not item["degenerate"] and item["trainable"] for item in summaries)


def test_degenerate_detection_marks_all_positive_or_all_negative() -> None:
    stats = add_ratios_and_composite(toy_line_stats().assign(critical_count=[0, 0, 0, 99]))
    _, summaries = build_labels(stats, ["critical_count_topq"], [0.0, 1.0])
    by_q = {round(item["top_quantile"], 2): item for item in summaries}
    assert by_q[0.0]["num_positive"] == 1
    assert by_q[0.0]["degenerate"] is False
    assert by_q[1.0]["num_negative"] == 0
    assert by_q[1.0]["degenerate"] is True
    assert by_q[1.0]["trainable"] is False


def test_auto_positive_weight_formula() -> None:
    assert resolve_weight("auto", positive=156, negative=1305) == pytest.approx(1305 / 156)
    assert resolve_weight("20", positive=1, negative=9) == pytest.approx(20.0)


def test_trainer_uses_original_rts79_paper_style_gcn_only() -> None:
    script = (IEEE118 / "train_ieee118_strict_fragility_gcn.py").read_text(encoding="utf-8")
    assert "PaperStyleRts79Gcn" in script
    assert "load_original_rts79_gcn_symbols" in script
    assert "LogisticRegression" not in script
    assert "GCN_smoke" not in script


def test_strict_path_probability_and_alpha_score_formula() -> None:
    score = pd.DataFrame(
        [
            {"path": "A", "first_line": "L001", "second_line": "L002", "p_shed_first": 0.01, "p_shed_second": 0.9, "q_strict_fragile": 0.8, "critical": True, "relay_cascade": True, "total_load_shed_mw": 5.0},
            {"path": "B", "first_line": "L003", "second_line": "L004", "p_shed_first": 0.9, "p_shed_second": 0.5, "q_strict_fragile": 0.2, "critical": False, "relay_cascade": False, "total_load_shed_mw": 0.0},
        ]
    )
    ranked = ranked_by_score(score.assign(score_alpha=score["q_strict_fragile"] * score["p_shed_second"]), "score_alpha")
    assert ranked.iloc[0]["path"] == "A"
    assert ranked.iloc[0]["score_alpha"] == pytest.approx(0.72)
    alpha_ranked = ranked_by_score(score.assign(score_alpha=np.power(1e-3 + score["q_strict_fragile"], 0.5) * score["p_shed_second"]), "score_alpha")
    assert alpha_ranked.iloc[0]["path"] == "A"


def test_evaluation_summary_fields_and_baselines_when_artifact_exists() -> None:
    summary_path = EVAL / "ieee118_strict_fragility_path_prob_summary.csv"
    if not summary_path.exists():
        return
    summary = pd.read_csv(summary_path)
    required = {
        "method",
        "K",
        "critical_hit_count",
        "relay_cascade_hit_count",
        "recall_critical",
        "recall_relay_cascade",
        "precision_at_k",
        "captured_total_load_shed_mw",
        "num_high_q_high_p_second_hits",
        "num_high_q_relay_hits",
    }
    assert required.issubset(summary.columns)
    methods = set(summary["method"].astype(str))
    assert {"random", "line_order", "LODF_yP", "PFW", "strict_path_prob", "second_only", "best_alpha_path_prob"}.issubset(methods)
    assert any(method.startswith("strict_fragility_path_prob_") for method in methods)


def test_build_comparison_keeps_baseline_columns() -> None:
    base_rows = []
    for method, hits in [
        ("random", 1),
        ("line_order", 2),
        ("LODF_yP", 3),
        ("PFW", 4),
        ("strict_path_prob", 5),
        ("second_only", 6),
        ("best_alpha_path_prob", 7),
        ("any_critical_fragility_path_prob", 8),
        ("strict_fragility_path_prob_critical_count_top10", 9),
    ]:
        base_rows.append({"method": method, "K": 100, "critical_hit_count": hits, "relay_cascade_hit_count": hits, "precision_at_k": hits / 100, "recall_critical": 0.1, "recall_relay_cascade": 0.1, "target_mode": "", "top_quantile": np.nan})
    comparison = build_comparison(pd.DataFrame(base_rows))
    row = comparison.loc[comparison["method"].eq("best_strict_fragility_path_prob")].iloc[0]
    assert row["relative_to_line_order_hits"] == pytest.approx(7)
    assert row["relative_to_best_alpha_hits"] == pytest.approx(2)


def test_compact_target_and_diagnostic_artifacts_when_present() -> None:
    target_summary = TARGETS / "ieee118_strict_fragility_target_summary.csv"
    diagnostics = EVAL / "strict_first_line_fragility_diagnostics.csv"
    if not target_summary.exists() or not diagnostics.exists():
        return
    targets = pd.read_csv(target_summary)
    assert len(targets) == 12
    assert targets["trainable"].astype(bool).all()
    assert not targets["degenerate"].astype(bool).any()
    diag = pd.read_csv(diagnostics)
    required = {
        "first_line",
        "target_mode",
        "top_quantile",
        "q_strict_fragile",
        "critical_count",
        "relay_cascade_count",
        "mean_rank_strict_fragility_path_prob",
        "rank_improvement_vs_strict_path_prob",
    }
    assert required.issubset(diag.columns)


def test_missing_file_error_is_clear(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="will not rerun OPA or regenerate full score tables|will not rerun OPA or regenerate large datasets"):
        require_file(tmp_path / "missing.csv", "strict target input")


def test_large_strict_fragility_artifacts_are_not_tracked() -> None:
    tracked = set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())
    forbidden_suffixes = (
        "ieee118_strict_fragility_targets_dataset.npz",
        "ieee118_strict_fragility_critical_count_top10_model.pt",
        "s0_bottleneck_full_score_table_local_only.csv",
        "ieee118_step2_state_samples.csv",
        "ieee118_fulltruth_summary.csv",
    )
    tracked_strict = [path for path in tracked if "ieee118_paper_aligned_training_scaleup/strict_fragility" in path]
    assert not [path for path in tracked_strict if path.endswith(forbidden_suffixes)]


def test_evaluate_ranked_reports_high_q_relay_hits() -> None:
    ranked = pd.DataFrame(
        [
            {"path": "A", "critical": True, "relay_cascade": True, "total_load_shed_mw": 5.0, "p_shed_first": 0.01, "p_shed_second": 0.9, "q_strict_fragile": 0.8},
            {"path": "B", "critical": False, "relay_cascade": False, "total_load_shed_mw": 0.0, "p_shed_first": 0.5, "p_shed_second": 0.2, "q_strict_fragile": 0.1},
        ]
    )
    budgets = pd.DataFrame([{"K": 1, "budget_type": "fixed", "budget_label": "K=1", "search_budget_ratio": 0.5}])
    summary = evaluate_ranked("strict_fragility_path_prob_toy", ranked, budgets)
    assert int(summary.iloc[0]["num_high_q_high_p_second_hits"]) == 1
    assert int(summary.iloc[0]["num_high_q_relay_hits"]) == 1

