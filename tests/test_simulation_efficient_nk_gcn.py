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
from run_ieee118_active_label_replay import parse_args as parse_replay_args
from run_ieee118_active_label_replay import replay
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
    args = parse_replay_args(
        [
            "--dataset-npz",
            str(dataset),
            "--output-dir",
            str(output),
            "--acquisition-mode",
            "pmf_bal",
            "--initial-labels",
            "6",
            "--query-batch-size",
            "4",
            "--rounds",
            "2",
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
    )
    summary = replay(args)
    assert summary["status"] == "complete"
    assert summary["model_class"] == "PaperStyleRts79Gcn"
    assert summary["model_core_modified"] is False
    assert summary["hidden_outcome_labels_used_as_features"] is False
    assert summary["num_available_training_oracle_labels"] == 40
    assert summary["num_queried_training_oracle_labels"] == 10
    assert summary["queried_training_oracle_fraction"] == pytest.approx(0.25)
    assert (output / "active_label_replay_round_metrics.csv").exists()
    assert (output / "active_label_replay_retrieval_metrics.csv").exists()


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
    assert {row["method"] for row in result["methods"]} == {"random", "pmf_bal"}
    assert (output / "ieee118_active_label_replay_comparison.csv").exists()
    assert (output / "ieee118_active_label_replay_aggregate.csv").exists()
