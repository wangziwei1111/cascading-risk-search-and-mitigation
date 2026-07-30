from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

from audit_ieee118_gcn_oracle_cost import audit
from evaluate_ieee118_active_dual_anchor import _oracle_costs, fuse_probabilities
from active_replay_search_metrics import (
    ActiveReplaySearchContext,
    active_replay_search_thresholds,
    make_active_replay_path_scores,
)
from run_ieee118_active_label_replay import (
    _label_budget_schedule,
    _prior_corrected_positive_weight,
)
from run_ieee118_active_label_replay import parse_args as parse_replay_args
from run_ieee118_active_label_replay import replay
from run_ieee118_label_efficiency_experiment import (
    _replay_arguments,
    parse_args as parse_experiment_args,
)
from risk_controlled_selective_verification import (
    calibrate_missed_positive_risk,
    missed_positive_fraction_by_unit,
    selected_for_physical_verification,
)
from simulation_efficient_active_learning import (
    assert_no_label_leakage,
    binary_entropy,
    candidate_pairs,
    ensemble_disagreement,
    select_active_query_batch,
    select_initial_batch,
    select_quota_active_query_batch,
    select_random_batch,
    update_query_mask,
)
from summarize_ieee118_active_label_replay import summarize


FEATURE_NAMES = np.asarray(
    ["branch_status_offline", "relay_loading_ratio", "abs_flow", "max_terminal_load"],
    dtype=str,
)


def test_uncertainty_functions_separate_entropy_and_disagreement() -> None:
    probability = np.asarray([0.01, 0.5, 0.99])
    entropy = binary_entropy(probability)
    assert entropy[1] > entropy[0]
    assert entropy[1] > entropy[2]

    members = np.asarray(
        [
            [[0.1, 0.5], [0.8, 0.2]],
            [[0.9, 0.5], [0.8, 0.2]],
        ]
    )
    disagreement = ensemble_disagreement(members)
    assert disagreement[0, 0] > 0.0
    assert disagreement[0, 1] == pytest.approx(0.0)


def test_random_query_is_unique_and_reproducible() -> None:
    valid = np.ones((5, 4), dtype=bool)
    first = select_random_batch(valid, 8, random_seed=10)
    repeated = select_random_batch(valid, 8, random_seed=10)
    different = select_random_batch(valid, 8, random_seed=11)
    assert np.array_equal(first, repeated)
    assert not np.array_equal(first, different)
    assert len({tuple(pair) for pair in first.tolist()}) == 8


def test_physics_stratified_initial_batch_covers_tail() -> None:
    x = np.zeros((3, 4, 4), dtype=np.float32)
    x[:, :, 1] = np.asarray(
        [
            [0.1, 0.2, 0.3, 0.4],
            [0.5, 0.6, 4.0, 0.8],
            [0.9, 3.0, 1.1, 1.2],
        ]
    )
    valid = np.ones((3, 4), dtype=bool)
    batch = select_initial_batch(
        x,
        valid,
        FEATURE_NAMES,
        4,
        physics_fraction=0.5,
        random_seed=7,
    )
    assert batch.size == 4
    assert len({tuple(pair) for pair in batch.pairs().tolist()}) == 4
    assert (1, 2) in {tuple(pair) for pair in batch.pairs().tolist()}
    assert (2, 1) in {tuple(pair) for pair in batch.pairs().tolist()}


def test_active_batch_excludes_queried_candidates() -> None:
    rng = np.random.default_rng(5)
    x = rng.normal(size=(4, 5, 4)).astype(np.float32)
    x[:, :, 1] = np.abs(x[:, :, 1])
    valid = np.ones((4, 5), dtype=bool)
    queried = np.zeros_like(valid)
    queried[0, 0] = True
    members = rng.uniform(0.05, 0.95, size=(3, 4, 5))
    batch = select_active_query_batch(
        members,
        x,
        valid,
        queried,
        FEATURE_NAMES,
        7,
        shortlist_multiplier=2,
    )
    pairs = {tuple(pair) for pair in batch.pairs().tolist()}
    assert batch.size == 7
    assert (0, 0) not in pairs
    assert len(pairs) == 7
    updated = update_query_mask(queried, batch)
    assert int(updated.sum()) == 8
    assert len(candidate_pairs(valid, updated)) == 12


def test_large_active_batch_caps_diversity_and_fills_without_duplicates() -> None:
    rng = np.random.default_rng(9)
    x = np.abs(rng.normal(size=(4, 5, 4))).astype(np.float32)
    valid = np.ones((4, 5), dtype=bool)
    queried = np.zeros_like(valid)
    members = rng.uniform(0.05, 0.95, size=(2, 4, 5))
    batch = select_active_query_batch(
        members,
        x,
        valid,
        queried,
        FEATURE_NAMES,
        19,
        shortlist_multiplier=2,
        max_diversity_selections=2,
    )
    assert batch.size == 19
    assert len({tuple(pair) for pair in batch.pairs().tolist()}) == 19


def test_quota_active_batch_is_unique_and_excludes_queried() -> None:
    rng = np.random.default_rng(19)
    x = np.abs(rng.normal(size=(5, 7, 4))).astype(np.float32)
    valid = np.ones((5, 7), dtype=bool)
    queried = np.zeros_like(valid)
    queried[0, 0] = True
    members = rng.uniform(0.05, 0.95, size=(3, 5, 7))
    batch = select_quota_active_query_batch(
        members,
        x,
        valid,
        queried,
        FEATURE_NAMES,
        30,
        shortlist_multiplier=2,
        max_diversity_selections=3,
    )
    pairs = {tuple(pair) for pair in batch.pairs().tolist()}
    assert batch.size == 30
    assert len(pairs) == 30
    assert (0, 0) not in pairs

    hybrid = select_quota_active_query_batch(
        members,
        x,
        valid,
        queried,
        FEATURE_NAMES,
        30,
        risk_fraction=0.15,
        uncertainty_fraction=0.25,
        random_fraction=0.50,
        shortlist_multiplier=2,
        max_diversity_selections=3,
        random_seed=23,
    )
    repeated = select_quota_active_query_batch(
        members,
        x,
        valid,
        queried,
        FEATURE_NAMES,
        30,
        risk_fraction=0.15,
        uncertainty_fraction=0.25,
        random_fraction=0.50,
        shortlist_multiplier=2,
        max_diversity_selections=3,
        random_seed=23,
    )
    assert np.array_equal(hybrid.pairs(), repeated.pairs())
    assert len({tuple(pair) for pair in hybrid.pairs().tolist()}) == 30


def test_label_leakage_guard_rejects_outcome_fields() -> None:
    assert_no_label_leakage(FEATURE_NAMES)
    with pytest.raises(ValueError, match="Outcome/label fields"):
        assert_no_label_leakage(["abs_flow", "total_load_shed_mw"])
    with pytest.raises(ValueError, match="Outcome/label fields"):
        assert_no_label_leakage(["feature_a", "label_critical"])


def test_oracle_cost_audit_counts_n1_and_n2_targets(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.npz"
    labels = np.asarray(
        [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ],
        dtype=np.int64,
    )
    target_mask = np.asarray(
        [
            [1, 1, 1],
            [0, 1, 1],
            [1, 0, 1],
        ],
        dtype=bool,
    )
    source_mask = np.asarray(
        [
            [1, 1, 1],
            [1, 1, 1],
            [1, 1, 1],
        ],
        dtype=bool,
    )
    np.savez(
        dataset,
        x_gcn=np.zeros((3, 3, 4), dtype=np.float32),
        y_gcn=labels,
        loss_mask=target_mask,
        source_loss_mask=source_mask,
        split=np.asarray(["train", "train", "validation"]),
        sample_type=np.asarray(["S0", "S1", "S1"]),
    )
    output = tmp_path / "audit"
    summary = audit(dataset, output)
    assert summary["num_graph_states"] == 3
    assert summary["num_active_target_high_fidelity_labels"] == 7
    assert summary["num_active_training_high_fidelity_labels"] == 5
    assert summary["estimated_n1_oracle_calls_for_s0_labels"] == 3
    assert summary["estimated_n2_oracle_calls_for_s1_labels"] == 6
    assert (output / "ieee118_gcn_oracle_cost_audit.json").exists()


def test_missing_oracle_dataset_error_does_not_regenerate(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="will not regenerate"):
        audit(tmp_path / "missing.npz")


def test_risk_control_calibrates_missed_positive_fraction() -> None:
    probability = np.asarray(
        [
            [0.90, 0.10],
            [0.20, 0.80],
            [0.70, 0.30],
        ]
    )
    labels = np.asarray(
        [
            [1, 0],
            [0, 1],
            [0, 0],
        ],
        dtype=bool,
    )
    valid = np.ones_like(labels)
    calibration = calibrate_missed_positive_risk(
        probability,
        labels,
        valid,
        alpha=0.40,
    )
    assert calibration.feasible
    assert calibration.threshold == pytest.approx(0.80)
    selected = selected_for_physical_verification(probability, valid, calibration)
    loss = missed_positive_fraction_by_unit(labels, selected, valid)
    assert loss.mean() == pytest.approx(0.0)
    assert calibration.crc_upper_risk <= 0.40


def test_uncertainty_can_expand_physical_fallback_set() -> None:
    probability = np.asarray([[0.9, 0.2, 0.1]])
    labels = np.asarray([[1, 0, 0]], dtype=bool)
    valid = np.ones_like(labels)
    calibration = calibrate_missed_positive_risk(probability, labels, valid, alpha=0.6)
    uncertainty = np.asarray([[0.0, 0.9, 0.1]])
    selected = selected_for_physical_verification(
        probability,
        valid,
        calibration,
        uncertainty=uncertainty,
        uncertainty_threshold=0.8,
    )
    assert selected[0, 1]


def test_active_label_replay_uses_sparse_queries_and_original_model(tmp_path: Path) -> None:
    rng = np.random.default_rng(14)
    num_states = 14
    num_lines = 5
    x = rng.normal(size=(num_states, num_lines, 4)).astype(np.float32)
    x[:, :, 1:] = np.abs(x[:, :, 1:])
    y = np.zeros((num_states, num_lines), dtype=np.int64)
    for state_idx in range(num_states):
        y[state_idx, state_idx % num_lines] = 1
    split = np.asarray(
        ["train"] * 8 + ["validation"] * 3 + ["test"] * 3,
        dtype=str,
    )
    dataset = tmp_path / "tiny_replay.npz"
    np.savez(
        dataset,
        x_gcn=x,
        y_gcn=y,
        loss_mask=np.ones_like(y, dtype=bool),
        split=split,
        sample_type=np.asarray(["S1"] * num_states, dtype=str),
        line_labels=np.asarray([f"L{i + 1:03d}" for i in range(num_lines)], dtype=str),
        branch_from_bus=np.asarray([1, 2, 3, 4, 5]),
        branch_to_bus=np.asarray([2, 3, 4, 5, 1]),
        feature_names=FEATURE_NAMES,
    )
    output = tmp_path / "replay"
    argument_list = [
        "--dataset-npz",
        str(dataset),
        "--output-dir",
        str(output),
        "--acquisition-mode",
        "pmf_bal",
        "--label-budgets",
        "6",
        "10",
        "--epochs-per-round",
        "1",
        "--ensemble-members",
        "1",
        "--batch-size",
        "4",
        "--k-gcn",
        "1",
        "--initial-pool-multiplier",
        "2",
        "--shortlist-multiplier",
        "2",
    ]
    args = parse_replay_args(argument_list)
    summary = replay(args)
    assert summary["status"] == "complete"
    assert summary["model_class"] == "PaperStyleRts79Gcn"
    assert summary["model_core_modified"] is False
    assert summary["hidden_outcome_labels_used_as_features"] is False
    assert summary["num_available_training_oracle_labels"] == 40
    assert summary["num_queried_training_oracle_labels"] == 10
    assert summary["queried_training_oracle_fraction"] == pytest.approx(0.25)
    assert summary["label_budget_schedule"] == [6, 10]
    assert summary["resumed_from_checkpoint"] is False
    assert (output / "active_label_replay_round_metrics.csv").exists()
    assert (output / "active_label_replay_retrieval_metrics.csv").exists()
    assert (output / "active_label_replay_checkpoint.pt").exists()

    resumed = replay(parse_replay_args(argument_list + ["--resume"]))
    assert resumed["resumed_from_checkpoint"] is True
    assert resumed["num_queried_training_oracle_labels"] == 10
    assert len(pd.read_csv(output / "active_label_replay_round_metrics.csv")) == 2


def test_fractional_label_budget_schedule_uses_available_training_count() -> None:
    args = parse_replay_args(
        ["--label-budget-fractions", "0.0025", "0.005", "0.01"]
    )
    assert _label_budget_schedule(args, 10_000) == [25, 50, 100]


def test_prior_correction_uses_only_queried_positive_rate() -> None:
    assert _prior_corrected_positive_weight(20.0, 0.015, 0.075) == pytest.approx(4.0)
    assert _prior_corrected_positive_weight(20.0, 0.015, 0.005) == pytest.approx(20.0)
    assert _prior_corrected_positive_weight(20.0, 0.0, 0.075) == pytest.approx(20.0)


def test_dual_anchor_probability_fusion_is_shape_safe() -> None:
    anchor = np.asarray([[0.1, 0.9]])
    active = np.asarray([[0.4, 0.4]])
    assert np.allclose(fuse_probabilities(anchor, active, "mean"), [[0.25, 0.65]])
    assert np.allclose(
        fuse_probabilities(anchor, active, "geometric_mean"),
        np.sqrt(anchor * active),
    )
    with pytest.raises(ValueError, match="same shape"):
        fuse_probabilities(anchor, active[:, :1], "mean")


def test_dual_anchor_oracle_cost_uses_subset_source_index_order() -> None:
    anchor = {
        "source_indices": np.asarray([1, 3, 2, 0]),
        "query_mask": np.asarray(
            [
                [1, 0],
                [0, 1],
                [1, 1],
                [1, 1],
            ],
            dtype=bool,
        ),
    }
    active = {
        "source_indices": np.asarray([1, 3, 2, 0]),
        "query_mask": np.asarray(
            [
                [0, 1],
                [0, 1],
                [0, 0],
                [0, 0],
            ],
            dtype=bool,
        ),
    }
    full_split = np.asarray(["test", "train", "validation", "train"])
    assert _oracle_costs(anchor, active, full_split) == (2, 2, 3)


def test_label_efficiency_runner_preserves_exact_fraction_schedule(tmp_path: Path) -> None:
    args = parse_experiment_args(
        [
            "--label-budget-fractions",
            "0.0025",
            "0.01",
            "--resume",
        ]
    )
    values = _replay_arguments(
        args,
        mode="pmf_hybrid_prior_corrected",
        seed=12,
        output_dir=tmp_path,
    )
    fraction_start = values.index("--label-budget-fractions") + 1
    assert values[fraction_start : fraction_start + 2] == ["0.0025", "0.01"]
    assert values[-1] == "--resume"
    assert values[values.index("--random-seed") + 1] == "12"


def test_active_replay_formal_search_uses_s0_and_all_s1_scores() -> None:
    truth = pd.DataFrame(
        [
            {
                "path": "L001->L002",
                "first_line": "L001",
                "second_line": "L002",
                "critical": True,
                "relay_cascade": True,
                "island_only": False,
                "total_load_shed_mw": 10.0,
                "n1_second": False,
            },
            {
                "path": "L001->L003",
                "first_line": "L001",
                "second_line": "L003",
                "critical": False,
                "relay_cascade": False,
                "island_only": False,
                "total_load_shed_mw": 0.0,
                "n1_second": False,
            },
            {
                "path": "L002->L001",
                "first_line": "L002",
                "second_line": "L001",
                "critical": False,
                "relay_cascade": False,
                "island_only": False,
                "total_load_shed_mw": 0.0,
                "n1_second": False,
            },
            {
                "path": "L002->L003",
                "first_line": "L002",
                "second_line": "L003",
                "critical": True,
                "relay_cascade": False,
                "island_only": True,
                "total_load_shed_mw": 5.0,
                "n1_second": True,
            },
        ]
    )
    context = ActiveReplaySearchContext(
        x_eval=np.zeros((2, 3, 4), dtype=np.float32),
        truth=truth,
        first_step=pd.DataFrame(),
        first_lines=np.asarray(["L001", "L002"]),
        line_labels=np.asarray(["L001", "L002", "L003"]),
        test_seed=1,
    )
    score = make_active_replay_path_scores(
        context,
        s0_probability=np.asarray([0.5, 0.9, 0.1]),
        s1_probability=np.asarray(
            [
                [0.0, 0.8, 0.2],
                [0.4, 0.0, 0.7],
            ]
        ),
    )
    first = score.set_index("path").loc["L001->L002"]
    assert first["p_shed_first"] == pytest.approx(0.5)
    assert first["p_shed_second"] == pytest.approx(0.8)
    assert first["path_product_score"] == pytest.approx(0.4)
    thresholds = active_replay_search_thresholds(
        context,
        s0_probability=np.asarray([0.5, 0.9, 0.1]),
        s1_probability=np.asarray(
            [
                [0.0, 0.8, 0.2],
                [0.4, 0.0, 0.7],
            ]
        ),
    )
    assert thresholds["search_num_valid_paths"] == 4
    assert thresholds["search_num_critical_paths"] == 2
    assert thresholds["search_path_prob_K90"] == 2
    assert thresholds["search_second_only_K100"] <= 4
    assert thresholds["search_residual_path_prob_K90"] == 1


def test_active_replay_summary_compares_complete_runs(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    for method, final_ap in (("random", 0.1), ("pmf_bal", 0.3)):
        run = root / f"{method}_smoke"
        run.mkdir(parents=True)
        (run / "active_label_replay_summary.json").write_text(
            (
                "{"
                f"\"acquisition_mode\": \"{method}\""
                "}"
            ),
            encoding="utf-8",
        )
        rows = [
            {
                "active_round": 0,
                "queried_training_labels": 6,
                "queried_training_label_fraction": 0.15,
                "queried_positive_labels": 1,
                "validation_average_precision": 0.2,
                "test_average_precision": 0.15,
                "risk_calibration_feasible": True,
                "risk_calibration_upper_risk": 0.04,
                "test_verification_budget_ratio": 0.4,
                "test_verification_positive_recall": 0.9,
                "search_path_prob_K90": 20,
            },
            {
                "active_round": 1,
                "queried_training_labels": 10,
                "queried_training_label_fraction": 0.25,
                "queried_positive_labels": 2,
                "validation_average_precision": final_ap,
                "test_average_precision": final_ap - 0.02,
                "risk_calibration_feasible": True,
                "risk_calibration_upper_risk": 0.04,
                "test_verification_budget_ratio": 0.3,
                "test_verification_positive_recall": 0.85,
                "search_path_prob_K90": 10,
            },
        ]
        pd.DataFrame(rows).to_csv(
            run / "active_label_replay_round_metrics.csv",
            index=False,
            encoding="utf-8-sig",
        )
    output = tmp_path / "summary"
    result = summarize(root, output)
    assert result["num_methods"] == 2
    assert result["formal_search_metrics_included"] is True
    assert {row["method"] for row in result["methods"]} == {"random", "pmf_bal"}
    assert (output / "ieee118_active_label_replay_comparison.csv").exists()
    assert (output / "ieee118_active_label_replay_aggregate.csv").exists()
