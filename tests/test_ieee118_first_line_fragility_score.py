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
sys.path.insert(0, str(IEEE118))

from build_ieee118_first_line_fragility_dataset import (
    build_sampled_fragility_for_seed,
    infer_unique_first_line,
    load_fulltruth_fragility,
    require_file as require_fragility_builder_file,
)
from evaluate_ieee118_fragility_path_prob import attach_q_fragile, evaluate_fragility_ranked
from evaluate_ieee118_alpha_path_prob_sweep import make_budget_table, ranked_by_score


def test_infer_unique_first_line_rejects_relay_ambiguous_outages() -> None:
    labels = ["L001", "L002", "L003"]
    assert infer_unique_first_line("L001", labels) == "L001"
    assert infer_unique_first_line("L001,L002", labels) is None
    assert infer_unique_first_line("", labels) is None


def toy_npz_like() -> dict[str, np.ndarray]:
    return {
        "y_gcn": np.asarray(
            [
                [0, 1, 0],
                [0, 0, 1],
                [0, 0, 0],
            ],
            dtype=np.int64,
        ),
        "loss_mask": np.asarray(
            [
                [1, 1, 1],
                [0, 1, 1],
                [1, 0, 1],
            ],
            dtype=bool,
        ),
        "sample_type": np.asarray(["S0", "S1", "S1"]),
        "seed": np.asarray([1, 1, 1], dtype=np.int64),
        "current_outage_labels": np.asarray(["", "L001", "L003"]),
    }


def test_sampled_fragility_label_definition_and_first_step_mask() -> None:
    data = toy_npz_like()
    rows = build_sampled_fragility_for_seed(seed=1, data=data, s0_index=0, line_labels=["L001", "L002", "L003"])
    assert rows["L001"]["loss_mask"] is True
    assert rows["L001"]["fragility_label"] == 1
    assert rows["L002"]["first_step_direct_shed_label"] == 1
    assert rows["L002"]["loss_mask"] is False
    assert rows["L003"]["loss_mask"] is True
    assert rows["L003"]["fragility_label"] == 0


def test_fulltruth_fragility_excludes_first_step_critical_lines(tmp_path: Path) -> None:
    fulltruth = pd.DataFrame(
        [
            {"path": "L001->L002", "first_line": "L001", "second_line": "L002", "critical": True, "relay_cascade": True, "total_load_shed_mw": 5.0, "valid_ordered_n2": True, "first_step_critical": False},
            {"path": "L002->L001", "first_line": "L002", "second_line": "L001", "critical": False, "relay_cascade": False, "total_load_shed_mw": 0.0, "valid_ordered_n2": True, "first_step_critical": True},
            {"path": "L003->L001", "first_line": "L003", "second_line": "L001", "critical": False, "relay_cascade": False, "total_load_shed_mw": 0.0, "valid_ordered_n2": True, "first_step_critical": False},
        ]
    )
    path_index = fulltruth[["path", "first_line", "second_line"]].copy()
    path_index["seed"] = 99
    fulltruth_path = tmp_path / "truth.csv"
    path_index_path = tmp_path / "path_index.csv"
    fulltruth.to_csv(fulltruth_path, index=False)
    path_index.to_csv(path_index_path, index=False)
    labels = load_fulltruth_fragility(fulltruth_path, path_index_path, line_labels=["L001", "L002", "L003"], heldout_test_seed=99)
    assert labels[99]["L001"]["fragility_label"] == 1
    assert labels[99]["L002"]["first_step_direct_shed_label"] == 1
    assert labels[99]["L002"]["loss_mask"] is False
    assert labels[99]["L003"]["fragility_label"] == 0


def test_fragility_path_prob_score_formula_and_summary_fields() -> None:
    score = pd.DataFrame(
        [
            {"path": "L001->L002", "first_line": "L001", "second_line": "L002", "p_shed_first": 0.01, "p_shed_second": 0.9, "critical": True, "relay_cascade": True, "total_load_shed_mw": 5.0},
            {"path": "L002->L003", "first_line": "L002", "second_line": "L003", "p_shed_first": 0.8, "p_shed_second": 0.8, "critical": False, "relay_cascade": False, "total_load_shed_mw": 0.0},
        ]
    )
    q = pd.DataFrame(
        [
            {"seed": 1, "line_label": "L001", "q_fragile": 0.7, "fragility_label": 1, "loss_mask": True, "first_step_direct_shed_label": 0, "first_step_critical": False},
            {"seed": 1, "line_label": "L002", "q_fragile": 0.2, "fragility_label": 0, "loss_mask": True, "first_step_direct_shed_label": 0, "first_step_critical": False},
        ]
    )
    merged = attach_q_fragile(score, q)
    merged["score_alpha"] = merged["q_fragile"] * merged["p_shed_second"]
    ranked = ranked_by_score(merged, "score_alpha")
    assert ranked.iloc[0]["path"] == "L001->L002"
    assert ranked.iloc[0]["score_alpha"] == pytest.approx(0.63)
    summary = evaluate_fragility_ranked("fragility_path_prob", ranked, make_budget_table(2, [1], []))
    required = {"mean_q_fragile_topk", "num_high_q_high_p_second_hits", "num_low_p_first_high_p_second_hits"}
    assert required.issubset(summary.columns)
    assert int(summary.iloc[0]["num_high_q_high_p_second_hits"]) == 1


def test_training_script_uses_original_paper_style_gcn_only() -> None:
    script = (IEEE118 / "train_ieee118_first_line_fragility_gcn.py").read_text(encoding="utf-8")
    assert "PaperStyleRts79Gcn" in script
    assert "load_original_rts79_gcn_symbols" in script
    assert "LogisticRegression" not in script
    assert "GCN_smoke" not in script


def test_missing_local_file_error_is_clear(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="will not rerun OPA or regenerate large datasets"):
        require_fragility_builder_file(tmp_path / "missing.npz", "paper GCN dataset NPZ")


def test_large_fragility_artifacts_are_not_tracked() -> None:
    tracked = set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())
    forbidden = {
        "results/gcn_search/ieee118_paper_aligned_training_scaleup/first_line_fragility/ieee118_first_line_fragility_dataset.npz",
        "results/gcn_search/ieee118_paper_aligned_training_scaleup/first_line_fragility/ieee118_first_line_fragility_model.pt",
    }
    assert forbidden.isdisjoint(tracked)
