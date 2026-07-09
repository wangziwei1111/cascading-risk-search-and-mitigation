from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

from evaluate_ieee118_alpha_path_prob_sweep import (
    SECOND_ONLY_METHOD,
    STRICT_PATH_PROB_METHOD,
    add_alpha_score,
    alpha_method_name,
    alpha_score,
    build_heatmap_data,
    build_score_table,
    build_vs_baselines,
    evaluate_alpha_sweep,
    make_budget_table,
    ranked_by_score,
    run_alpha_sweep,
    select_best_configs,
)


def toy_score_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "path": "L001->L002",
                "first_line": "L001",
                "second_line": "L002",
                "p_shed_first": 0.01,
                "p_shed_second": 0.99,
                "critical": True,
                "relay_cascade": True,
                "critical_mechanism": "relay_cascade",
                "total_load_shed_mw": 10.0,
            },
            {
                "path": "L003->L004",
                "first_line": "L003",
                "second_line": "L004",
                "p_shed_first": 0.9,
                "p_shed_second": 0.5,
                "critical": True,
                "relay_cascade": False,
                "critical_mechanism": "island_only",
                "total_load_shed_mw": 3.0,
            },
            {
                "path": "L005->L006",
                "first_line": "L005",
                "second_line": "L006",
                "p_shed_first": 0.8,
                "p_shed_second": 0.4,
                "critical": False,
                "relay_cascade": False,
                "critical_mechanism": "non_critical",
                "total_load_shed_mw": 0.0,
            },
            {
                "path": "L007->L008",
                "first_line": "L007",
                "second_line": "L008",
                "p_shed_first": 0.2,
                "p_shed_second": 0.95,
                "critical": True,
                "relay_cascade": True,
                "critical_mechanism": "relay_cascade",
                "total_load_shed_mw": 7.0,
            },
            {
                "path": "L009->L010",
                "first_line": "L009",
                "second_line": "L010",
                "p_shed_first": 0.7,
                "p_shed_second": 0.1,
                "critical": False,
                "relay_cascade": False,
                "critical_mechanism": "non_critical",
                "total_load_shed_mw": 0.0,
            },
        ]
    )


def test_alpha_one_epsilon_zero_equivalent_to_strict_path_prob() -> None:
    score = toy_score_table()
    strict = alpha_score(score["p_shed_first"], score["p_shed_second"], alpha=1.0, epsilon=0.0)
    assert np.allclose(strict, score["p_shed_first"] * score["p_shed_second"])


def test_alpha_zero_equivalent_to_second_only_and_epsilon_independent() -> None:
    score = toy_score_table()
    eps0 = alpha_score(score["p_shed_first"], score["p_shed_second"], alpha=0.0, epsilon=0.0)
    eps_big = alpha_score(score["p_shed_first"], score["p_shed_second"], alpha=0.0, epsilon=1e-2)
    assert np.allclose(eps0, score["p_shed_second"])
    assert np.allclose(eps0, eps_big)


def test_method_name_uses_stable_machine_readable_tokens() -> None:
    assert alpha_method_name(0.05, 1e-4) == "alpha_path_prob_a005_eps1em4"
    assert alpha_method_name(1.0, 0.0) == "alpha_path_prob_a1_eps0"
    assert alpha_method_name(0.25, 1e-2) == "alpha_path_prob_a025_eps1em2"


def test_sorting_direction_uses_score_then_second_then_first_then_path() -> None:
    score = pd.DataFrame(
        [
            {"path": "B", "first_line": "L001", "second_line": "L002", "p_shed_first": 0.2, "p_shed_second": 0.9, "score_alpha": 0.5, "critical": False, "relay_cascade": False, "total_load_shed_mw": 0},
            {"path": "A", "first_line": "L003", "second_line": "L004", "p_shed_first": 0.3, "p_shed_second": 0.9, "score_alpha": 0.5, "critical": False, "relay_cascade": False, "total_load_shed_mw": 0},
            {"path": "C", "first_line": "L005", "second_line": "L006", "p_shed_first": 0.1, "p_shed_second": 0.95, "score_alpha": 0.4, "critical": False, "relay_cascade": False, "total_load_shed_mw": 0},
        ]
    )
    ranked = ranked_by_score(score, "score_alpha")
    assert ranked["path"].tolist() == ["A", "B", "C"]


def test_low_p_first_high_p_second_hit_count() -> None:
    budgets = make_budget_table(5, [2], [])
    ranked = ranked_by_score(add_alpha_score(toy_score_table(), 0.0, 0.0), "score_alpha")
    summary, _ = evaluate_alpha_sweep(
        toy_score_table(),
        alphas=[0.0],
        epsilons=[0.0],
        budgets=budgets,
        random_seeds=[1],
    )
    row = summary.loc[(summary["method"].eq(SECOND_ONLY_METHOD)) & (summary["K"].eq(2))].iloc[0]
    assert ranked.head(2)["path"].tolist() == ["L001->L002", "L007->L008"]
    assert int(row["num_low_p_first_high_p_second_hits"]) == 1


def test_best_config_selection_and_heatmap_fields() -> None:
    budgets = make_budget_table(5, [2], [])
    summary, _ = evaluate_alpha_sweep(
        toy_score_table(),
        alphas=[0.0, 1.0],
        epsilons=[0.0],
        budgets=budgets,
        random_seeds=[1],
    )
    best = select_best_configs(summary)
    assert not best.empty
    assert "criterion" in best.columns
    heat = build_heatmap_data(summary)
    expected = {"method", "alpha", "epsilon", "K", "critical_hit_count", "recall_critical", "relay_cascade_hit_count"}
    assert expected.issubset(set(heat.columns))


def test_baselines_retained_in_summary_and_vs_table() -> None:
    budgets = make_budget_table(5, [2], [])
    summary, _ = evaluate_alpha_sweep(
        toy_score_table(),
        alphas=[0.5],
        epsilons=[0.0],
        budgets=budgets,
        random_seeds=[1, 2],
    )
    methods = set(summary["method"])
    assert {STRICT_PATH_PROB_METHOD, SECOND_ONLY_METHOD, "line_order", "random"}.issubset(methods)
    best = select_best_configs(summary)
    vs = build_vs_baselines(summary, best)
    assert {"critical_hits_vs_strict", "critical_hits_vs_second_only"}.issubset(set(vs.columns))


def test_missing_local_large_file_error_is_clear(tmp_path: Path) -> None:
    args = type(
        "Args",
        (),
        {
            "score_table_csv": tmp_path / "missing_score.csv",
            "fulltruth_csv": tmp_path / "missing_truth.csv",
            "path_index_csv": tmp_path / "missing_path_index.csv",
            "dataset_npz": tmp_path / "missing_dataset.npz",
            "model_path": tmp_path / "missing_model.pt",
            "feature_normalizer_json": tmp_path / "missing_normalizer.json",
            "first_step_probabilities_csv": tmp_path / "missing_first_prob.csv",
        },
    )()
    with pytest.raises(FileNotFoundError, match="will not retrain the GCN, rerun OPA, or regenerate full-truth"):
        build_score_table(args)


def test_run_alpha_sweep_writes_compact_outputs(tmp_path: Path) -> None:
    score_csv = tmp_path / "score.csv"
    toy_score_table().to_csv(score_csv, index=False)
    args = type(
        "Args",
        (),
        {
            "score_table_csv": score_csv,
            "fulltruth_csv": tmp_path / "unused_truth.csv",
            "path_index_csv": tmp_path / "unused_path_index.csv",
            "dataset_npz": tmp_path / "unused_dataset.npz",
            "model_path": tmp_path / "unused_model.pt",
            "feature_normalizer_json": tmp_path / "unused_normalizer.json",
            "first_step_probabilities_csv": tmp_path / "unused_first_prob.csv",
            "baseline_summary_csv": tmp_path / "missing_baseline_summary.csv",
            "baseline_topk_paths_csv": tmp_path / "missing_topk.csv",
            "output_dir": tmp_path / "out",
            "alphas": [0.0, 0.5, 1.0],
            "epsilons": [0.0, 1e-4],
            "k_values": [2, 4],
            "ratio_k_values": [],
            "random_seeds": [1, 2],
            "topk_output_rows": 3,
            "method_suffix": "",
        },
    )()
    result = run_alpha_sweep(args)
    assert result["num_paths"] == 5
    for name in [
        "alpha_path_prob_sweep_summary.csv",
        "alpha_path_prob_sweep_summary.json",
        "alpha_path_prob_sweep_best_configs.csv",
        "alpha_path_prob_heatmap_data.csv",
        "alpha_path_prob_sweep_config.json",
        "alpha_path_prob_sweep_readme.md",
    ]:
        assert (args.output_dir / name).exists()
