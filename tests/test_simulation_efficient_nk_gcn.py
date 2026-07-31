from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

from audit_ieee118_gcn_oracle_cost import audit
from evaluate_ieee118_active_dual_anchor import (
    _oracle_costs,
    _single_oracle_cost,
    fuse_probabilities,
)
from active_replay_search_metrics import (
    ActiveReplaySearchContext,
    active_replay_search_thresholds,
    make_active_replay_path_scores,
)
from run_ieee118_active_label_replay import (
    _checkpoint_fingerprint,
    _load_low_fidelity_targets,
    _label_budget_schedule,
    _prior_corrected_positive_weight,
    high_fidelity_data_cost_summary,
    sample_order_sha256,
)
from run_ieee118_active_label_replay import parse_args as parse_replay_args
from run_ieee118_active_label_replay import replay
from run_ieee118_label_efficiency_experiment import (
    _replay_arguments,
    parse_args as parse_experiment_args,
)
from propensity_debiased_active_learning import (
    effective_sample_size,
    levelled_unbiased_risk_weights,
    lure_weight_matrix,
    physics_guided_lure_utility,
    sample_propensity_batch,
)
from dc_lodf_low_fidelity import (
    binary_low_fidelity_target,
    build_dc_lodf_matrix,
    dc_lodf_max_loading_proxy,
)
from build_ieee118_dc_lodf_low_fidelity_targets import (
    low_fidelity_cost_disclosure,
    portable_result_path,
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
from simulation_efficient_prefix_search import (
    adaptive_probe_then_promote_ordered_n2,
    probe_second_line_feedback,
    OrderedPrefixStateCache,
    evaluate_lazy_ranking,
    lazy_best_first_ordered_n2,
)
from summarize_ieee118_active_label_replay import summarize
from evaluate_ieee118_lazy_prefix_search import (
    apply_second_line_physics_gate,
    parse_args as parse_lazy_prefix_args,
    rank_normalize_line_scores,
)
from evaluate_ieee118_iterative_lodf_n1_proxy import (
    parse_args as parse_iterative_proxy_args,
    prepare_proxy_score_export,
)
import evaluate_ieee118_iterative_lodf_n1_proxy as iterative_proxy_module
from select_ieee118_adaptive_probe_policy import (
    ValidationProbeScenario,
    evaluate_validation_probe_grid,
    select_probe_configuration,
)
from summarize_ieee118_simulation_efficient_phase3 import (
    build_phase3_relative_comparisons,
    build_phase3_high_fidelity_cost_accounting,
    extract_lazy_method_row,
)


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


def test_propensity_batch_is_unique_reproducible_and_records_conditional_q() -> None:
    pairs = np.column_stack(
        (
            np.zeros(8, dtype=np.int64),
            np.arange(8, dtype=np.int64),
        )
    )
    utility = np.asarray([0.1, 0.2, 0.3, 0.4, 1.0, 2.0, 3.0, 4.0])
    first = sample_propensity_batch(
        pairs,
        utility,
        5,
        exploration_mass=0.5,
        random_seed=17,
    )
    repeated = sample_propensity_batch(
        pairs,
        utility,
        5,
        exploration_mass=0.5,
        random_seed=17,
    )
    different = sample_propensity_batch(
        pairs,
        utility,
        5,
        exploration_mass=0.5,
        random_seed=18,
    )
    assert np.array_equal(first.pairs(), repeated.pairs())
    assert np.allclose(
        first.proposal_probability,
        repeated.proposal_probability,
    )
    assert not np.array_equal(first.pairs(), different.pairs())
    assert len({tuple(pair) for pair in first.pairs().tolist()}) == 5
    assert np.all((first.proposal_probability > 0.0) & (first.proposal_probability <= 1.0))


def test_lure_uniform_sampling_reduces_to_unit_weights() -> None:
    pool_size = 20
    num_acquired = 7
    remaining = pool_size - np.arange(num_acquired)
    probability = 1.0 / remaining
    weight = levelled_unbiased_risk_weights(pool_size, probability)
    assert np.allclose(weight, 1.0)
    assert effective_sample_size(weight) == pytest.approx(num_acquired)


def test_lure_estimator_is_unbiased_for_weighted_without_replacement_sampling() -> None:
    losses = np.asarray([0.0, 0.2, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0])
    pairs = np.column_stack(
        (
            np.zeros(len(losses), dtype=np.int64),
            np.arange(len(losses), dtype=np.int64),
        )
    )
    utility = np.asarray([4.0, 3.0, 2.0, 1.0, 0.8, 0.5, 0.2, 0.1])
    estimates = []
    for seed in range(4000):
        batch = sample_propensity_batch(
            pairs,
            utility,
            3,
            exploration_mass=0.4,
            random_seed=seed,
        )
        weight = levelled_unbiased_risk_weights(
            len(losses),
            batch.proposal_probability,
        )
        estimates.append(
            float(np.dot(weight, losses[batch.line_indices]) / batch.size)
        )
    assert np.mean(estimates) == pytest.approx(losses.mean(), abs=0.04)


def test_lure_weight_matrix_maps_acquisition_order_back_to_graph_labels() -> None:
    position = np.asarray([[2, -1, 0], [1, -1, -1]])
    probability = np.zeros_like(position, dtype=float)
    probability[0, 2] = 1.0 / 6.0
    probability[1, 0] = 1.0 / 5.0
    probability[0, 0] = 1.0 / 4.0
    weight = lure_weight_matrix(
        position,
        probability,
        pool_size=6,
        num_acquired=3,
    )
    assert np.allclose(weight[position >= 0], 1.0)
    assert np.all(weight[position < 0] == 0.0)


def test_physics_guided_lure_utility_uses_only_model_and_input_features() -> None:
    rng = np.random.default_rng(22)
    x = np.abs(rng.normal(size=(3, 4, 4))).astype(np.float32)
    pairs = np.argwhere(np.ones((3, 4), dtype=bool))
    members = rng.uniform(0.01, 0.99, size=(2, 3, 4))
    utility, entropy, disagreement, severity = physics_guided_lure_utility(
        members,
        x,
        pairs,
        FEATURE_NAMES,
        mode="physics_guided",
    )
    assert utility.shape == (12,)
    assert entropy.shape == disagreement.shape == severity.shape == utility.shape
    assert np.isfinite(utility).all()
    assert np.all(utility >= 0.0)
    with pytest.raises(ValueError, match="Outcome/label"):
        physics_guided_lure_utility(
            members,
            x,
            pairs,
            ["critical", "a", "b", "c"],
            mode="physics_guided",
        )


def test_dc_lodf_proxy_is_finite_for_meshed_active_candidates() -> None:
    matrix = build_dc_lodf_matrix(
        np.asarray([1, 2, 1]),
        np.asarray([2, 3, 3]),
        np.asarray([0.1, 0.1, 0.2]),
        np.ones(3, dtype=bool),
    )
    proxy = dc_lodf_max_loading_proxy(
        np.asarray([50.0, 30.0, 20.0]),
        np.asarray([1.0, 1.0, -1.0]),
        np.asarray([100.0, 100.0, 100.0]),
        np.ones(3, dtype=bool),
        matrix,
    )
    assert proxy.shape == (3,)
    assert np.isfinite(proxy).all()
    assert np.all(proxy >= 0.0)


def test_dc_lodf_with_transformer_taps_matches_pypower_ieee118() -> None:
    from pypower.case118 import case118
    from pypower.ext2int import ext2int
    from pypower.idx_brch import BR_STATUS, BR_X, F_BUS, TAP, T_BUS
    from pypower.makeLODF import makeLODF
    from pypower.makePTDF import makePTDF

    case = ext2int(case118())
    branch = case["branch"]
    tap = branch[:, TAP].astype(float)
    tap[tap == 0.0] = 1.0
    assert np.count_nonzero(~np.isclose(tap, 1.0)) == 9
    reference = makeLODF(
        branch,
        makePTDF(case["baseMVA"], case["bus"], branch),
    )
    matrix = build_dc_lodf_matrix(
        branch[:, F_BUS],
        branch[:, T_BUS],
        branch[:, BR_X],
        branch[:, BR_STATUS].astype(bool),
        branch_tap_ratio=tap,
    )
    finite = np.isfinite(reference) & np.isfinite(matrix.lodf)
    assert finite.any()
    assert np.max(np.abs(reference[finite] - matrix.lodf[finite])) < 1e-8


def test_label_free_iterative_proxy_forwards_transformer_taps(monkeypatch) -> None:
    observed_taps: list[np.ndarray] = []

    def fake_proxy(
        signed_flow,
        rate_a,
        initial_branch_status,
        initial_outage_index,
        *,
        branch_tap_ratio,
        **kwargs,
    ):
        observed_taps.append(np.asarray(branch_tap_ratio, dtype=float).copy())
        return iterative_proxy_module.IterativeRelayProxyResult(
            num_relay_trips=0,
            max_event_loading_ratio=float(branch_tap_ratio[0]),
            num_singular_outages=0,
            final_branch_status=np.asarray(initial_branch_status, dtype=bool),
        )

    monkeypatch.setattr(
        iterative_proxy_module,
        "iterative_dc_lodf_relay_proxy",
        fake_proxy,
    )
    taps = np.asarray([1.25, 1.0, 1.0])
    table = iterative_proxy_module.compute_label_free_iterative_proxy_scores(
        signed_flow=np.asarray([10.0, 8.0, 2.0]),
        rate_a=np.asarray([20.0, 20.0, 20.0]),
        line_labels=np.asarray(["L001", "L002", "L003"]),
        branch_from_bus=np.asarray([1, 2, 1]),
        branch_to_bus=np.asarray([2, 3, 3]),
        branch_x=np.asarray([0.1, 0.1, 0.2]),
        branch_tap_ratio=taps,
        beta=1.2,
        max_rounds=5,
    )

    assert len(observed_taps) == 3
    assert all(np.array_equal(value, taps) for value in observed_taps)
    assert table["iterative_max_event_loading_ratio"].eq(1.25).all()


def test_label_free_iterative_proxy_skips_already_open_branch(monkeypatch) -> None:
    called_indices: list[int] = []

    def fake_proxy(
        signed_flow,
        rate_a,
        initial_branch_status,
        initial_outage_index,
        **kwargs,
    ):
        called_indices.append(int(initial_outage_index))
        return iterative_proxy_module.IterativeRelayProxyResult(
            num_relay_trips=0,
            max_event_loading_ratio=0.5,
            num_singular_outages=0,
            final_branch_status=np.asarray(initial_branch_status, dtype=bool),
        )

    monkeypatch.setattr(
        iterative_proxy_module,
        "iterative_dc_lodf_relay_proxy",
        fake_proxy,
    )
    table = iterative_proxy_module.compute_label_free_iterative_proxy_scores(
        signed_flow=np.asarray([0.0, 8.0, 2.0]),
        rate_a=np.asarray([20.0, 20.0, 20.0]),
        line_labels=np.asarray(["L001", "L002", "L003"]),
        branch_from_bus=np.asarray([1, 2, 1]),
        branch_to_bus=np.asarray([2, 3, 3]),
        branch_x=np.asarray([0.1, 0.1, 0.2]),
        branch_tap_ratio=np.ones(3),
        beta=1.2,
        max_rounds=5,
        initial_branch_status=np.asarray([False, True, True]),
    )

    assert called_indices == [1, 2]
    assert table.loc[0, "iterative_composite_score"] == 0.0


def test_low_fidelity_quantile_is_frozen_on_training_scores_only() -> None:
    score = np.asarray(
        [
            [0.1, 0.2, 0.3, 0.4],
            [100.0, 200.0, 300.0, 400.0],
            [500.0, 600.0, 700.0, 800.0],
        ]
    )
    mask = np.ones_like(score, dtype=bool)
    target, threshold = binary_low_fidelity_target(
        score,
        mask,
        np.asarray(["train", "validation", "test"]),
        mode="top_quantile",
        upper_quantile=0.75,
    )
    assert threshold == pytest.approx(np.quantile(score[0], 0.75))
    assert target[0].sum() == 1
    assert target[1].sum() == 4


def test_low_fidelity_per_state_quantile_preserves_each_state_tail() -> None:
    score = np.asarray(
        [
            [0.1, 0.2, 0.3, 0.4],
            [10.0, 20.0, 30.0, 40.0],
        ]
    )
    target, representative_threshold = binary_low_fidelity_target(
        score,
        np.ones_like(score, dtype=bool),
        np.asarray(["train", "validation"]),
        mode="per_state_top_quantile",
        upper_quantile=0.75,
    )
    assert target.sum(axis=1).tolist() == [1, 1]
    assert representative_threshold == pytest.approx(
        np.median(
            [
                np.quantile(score[0], 0.75),
                np.quantile(score[1], 0.75),
            ]
        )
    )


def test_low_fidelity_cost_disclosure_does_not_erase_source_s1_cost() -> None:
    disclosure = low_fidelity_cost_disclosure("active_first_only")
    assert disclosure["incremental_target_builder_n1_cascade_calls"] == 0
    assert disclosure["incremental_target_builder_n2_cascade_calls"] == 0
    assert disclosure["source_state_cost_reclaimed"] is False
    assert "pre-existing S0/S1" in disclosure["source_state_dependency"]


def test_low_fidelity_metadata_uses_repo_relative_paths() -> None:
    path = ROOT / "results" / "gcn_search" / "local_only.npz"
    assert portable_result_path(path) == str(
        Path("results") / "gcn_search" / "local_only.npz"
    )


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
    seed = np.arange(num_states, dtype=np.int64) + 100
    active_first_line = np.asarray(
        [f"L{(idx % num_lines) + 1:03d}" for idx in range(num_states)],
        dtype=str,
    )
    dataset = tmp_path / "tiny_replay.npz"
    np.savez(
        dataset,
        x_gcn=x,
        y_gcn=y,
        loss_mask=np.ones_like(y, dtype=bool),
        seed=seed,
        split=split,
        sample_type=np.asarray(["S1"] * num_states, dtype=str),
        active_first_line=active_first_line,
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


def test_pg_lure_replay_uses_exact_budget_weights_and_resume(tmp_path: Path) -> None:
    rng = np.random.default_rng(24)
    num_states = 11
    num_lines = 4
    x = np.abs(rng.normal(size=(num_states, num_lines, 4))).astype(np.float32)
    y = np.zeros((num_states, num_lines), dtype=np.int64)
    for state_idx in range(num_states):
        y[state_idx, state_idx % num_lines] = 1
    split = np.asarray(
        ["train"] * 7 + ["validation"] * 2 + ["test"] * 2,
        dtype=str,
    )
    seed = np.arange(num_states, dtype=np.int64) + 200
    active_first_line = np.asarray(
        [f"L{(idx % num_lines) + 1:03d}" for idx in range(num_states)],
        dtype=str,
    )
    dataset = tmp_path / "tiny_lure_replay.npz"
    np.savez(
        dataset,
        x_gcn=x,
        y_gcn=y,
        loss_mask=np.ones_like(y, dtype=bool),
        seed=seed,
        split=split,
        sample_type=np.asarray(["S1"] * num_states, dtype=str),
        active_first_line=active_first_line,
        line_labels=np.asarray([f"L{i + 1:03d}" for i in range(num_lines)], dtype=str),
        branch_from_bus=np.asarray([1, 2, 3, 4]),
        branch_to_bus=np.asarray([2, 3, 4, 1]),
        feature_names=FEATURE_NAMES,
    )
    output = tmp_path / "pg_lure"
    values = [
        "--dataset-npz",
        str(dataset),
        "--output-dir",
        str(output),
        "--acquisition-mode",
        "pg_lure",
        "--label-budgets",
        "5",
        "9",
        "--epochs-per-round",
        "1",
        "--ensemble-members",
        "1",
        "--batch-size",
        "4",
        "--k-gcn",
        "1",
        "--lure-exploration-mass",
        "0.5",
    ]
    summary = replay(parse_replay_args(values))
    assert summary["status"] == "complete"
    assert summary["research_stage"].startswith("Phase 3")
    assert summary["num_available_training_oracle_labels"] == 28
    assert summary["num_queried_training_oracle_labels"] == 9
    assert summary["train_config"]["lure_training_correction_enabled"] is True
    metrics = pd.read_csv(output / "active_label_replay_round_metrics.csv")
    assert len(metrics) == 2
    assert metrics["lure_weight_min"].gt(0.0).all()
    assert metrics["lure_weight_effective_sample_fraction"].between(0.0, 1.0).all()
    checkpoint = np.load(output / "active_label_replay_local_checkpoint.npz")
    selected_position = checkpoint["acquisition_position"]
    assert np.array_equal(
        np.sort(selected_position[selected_position >= 0]),
        np.arange(9),
    )
    selected_probability = checkpoint["acquisition_probability"][
        selected_position >= 0
    ]
    assert np.all(selected_probability > 0.0)

    resumed = replay(parse_replay_args(values + ["--resume"]))
    assert resumed["resumed_from_checkpoint"] is True
    assert resumed["num_queried_training_oracle_labels"] == 9


def test_low_fidelity_pretrain_warm_starts_original_gcn(tmp_path: Path) -> None:
    rng = np.random.default_rng(31)
    num_states = 12
    num_lines = 4
    x = np.abs(rng.normal(size=(num_states, num_lines, 4))).astype(np.float32)
    y = np.zeros((num_states, num_lines), dtype=np.int64)
    for state_idx in range(num_states):
        y[state_idx, state_idx % num_lines] = 1
    split = np.asarray(
        ["train"] * 7 + ["validation"] * 3 + ["test"] * 2,
        dtype=str,
    )
    seed = np.arange(num_states, dtype=np.int64) + 300
    sample_type = np.asarray(["S1"] * num_states, dtype=str)
    active_first_line = np.asarray(
        [f"L{(idx % num_lines) + 1:03d}" for idx in range(num_states)],
        dtype=str,
    )
    line_labels = np.asarray(
        [f"L{i + 1:03d}" for i in range(num_lines)],
        dtype=str,
    )
    dataset = tmp_path / "tiny_multifidelity_replay.npz"
    np.savez(
        dataset,
        x_gcn=x,
        y_gcn=y,
        loss_mask=np.ones_like(y, dtype=bool),
        seed=seed,
        split=split,
        sample_type=sample_type,
        active_first_line=active_first_line,
        line_labels=line_labels,
        branch_from_bus=np.asarray([1, 2, 3, 4]),
        branch_to_bus=np.asarray([2, 3, 4, 1]),
        feature_names=FEATURE_NAMES,
    )
    low_fidelity_path = tmp_path / "low_fidelity.npz"
    np.savez(
        low_fidelity_path,
        proxy_score=np.abs(rng.normal(size=y.shape)).astype(np.float32),
        proxy_mask=np.ones_like(y, dtype=bool),
        line_labels=line_labels,
        seed=seed,
        split=split,
        sample_type=sample_type,
        active_first_line=active_first_line,
    )
    output = tmp_path / "multifidelity"
    summary = replay(
        parse_replay_args(
            [
                "--dataset-npz",
                str(dataset),
                "--output-dir",
                str(output),
                "--acquisition-mode",
                "pmf_hybrid_prior_corrected",
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
                "--low-fidelity-target-npz",
                str(low_fidelity_path),
                "--low-fidelity-pretrain-epochs",
                "1",
                "--low-fidelity-upper-quantile",
                "0.75",
            ]
        )
    )
    assert summary["model_class"] == "PaperStyleRts79Gcn"
    assert summary["model_core_modified"] is False
    assert summary["low_fidelity_pretraining"]["enabled"] is True
    assert summary["low_fidelity_pretraining"]["num_training_proxy_labels"] == 28
    training_log = pd.read_csv(output / "active_label_replay_training_log.csv")
    assert "low_fidelity_pretrain" in set(training_log["training_stage"])
    assert "high_fidelity_active" in set(training_log["training_stage"])


def test_high_fidelity_cost_reports_shared_validation_and_audit_labels() -> None:
    valid = np.ones((5, 4), dtype=bool)
    query = np.zeros_like(valid)
    query[0, :3] = True
    query[1, :2] = True
    split = np.asarray(
        ["train", "train", "validation", "validation", "test"],
        dtype=str,
    )

    cost = high_fidelity_data_cost_summary(
        query,
        valid,
        split,
        policy_selection_label_count=6,
        policy_selection_reuses_validation=True,
        formal_search_audit_label_count=12,
    )

    assert cost["num_training_query_labels"] == 5
    assert cost["num_validation_model_selection_labels"] == 8
    assert cost["num_calibration_labels"] == 8
    assert cost["num_policy_selection_labels"] == 6
    assert cost["policy_selection_reuses_validation_labels"] is True
    assert cost["num_unique_development_high_fidelity_labels"] == 13
    assert cost["num_test_audit_labels"] == 4
    assert cost["num_formal_search_audit_path_labels"] == 12
    assert cost["num_full_label_reference_development_labels"] == 16
    assert cost["training_query_reduction_fraction"] == pytest.approx(3 / 8)
    assert cost["total_development_label_reduction_fraction"] == pytest.approx(3 / 16)


def test_checkpoint_fingerprint_changes_when_dataset_content_changes(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "same_path.npz"
    np.savez(dataset, value=np.asarray([1, 2, 3], dtype=np.int64))
    args = parse_replay_args(["--dataset-npz", str(dataset)])
    indices = np.asarray([0, 1], dtype=np.int64)
    first = _checkpoint_fingerprint(
        args,
        indices,
        [2],
        sample_order_digest="order-a",
    )

    np.savez(dataset, value=np.asarray([1, 2, 4], dtype=np.int64))
    second = _checkpoint_fingerprint(
        args,
        indices,
        [2],
        sample_order_digest="order-a",
    )

    assert first != second


def test_sample_order_digest_changes_when_first_line_order_changes() -> None:
    data = {
        "seed": np.asarray([1, 1, 2]),
        "split": np.asarray(["train", "validation", "test"]),
        "sample_type": np.asarray(["S0", "S1", "S1"]),
        "active_first_line": np.asarray(["", "L001", "L002"]),
    }
    indices = np.asarray([0, 1, 2], dtype=np.int64)
    first = sample_order_sha256(data, indices)
    data["active_first_line"] = np.asarray(["", "L002", "L001"])
    second = sample_order_sha256(data, indices)
    assert first != second


def test_low_fidelity_identity_mismatch_is_rejected(tmp_path: Path) -> None:
    shape = (3, 2)
    labels = np.asarray(["L001", "L002"], dtype=str)
    seed = np.asarray([1, 2, 3], dtype=np.int64)
    split = np.asarray(["train", "validation", "test"], dtype=str)
    sample_type = np.asarray(["S0", "S1", "S1"], dtype=str)
    first_line = np.asarray(["", "L001", "L002"], dtype=str)
    path = tmp_path / "misaligned_proxy.npz"
    np.savez(
        path,
        proxy_score=np.ones(shape, dtype=np.float32),
        proxy_mask=np.ones(shape, dtype=bool),
        line_labels=labels,
        seed=seed[[1, 0, 2]],
        split=split,
        sample_type=sample_type,
        active_first_line=first_line,
    )

    with pytest.raises(ValueError, match="seed sample order"):
        _load_low_fidelity_targets(
            path,
            original_indices=np.asarray([0, 1, 2], dtype=np.int64),
            full_shape=shape,
            expected_line_labels=labels,
            expected_seed=seed,
            expected_split=split,
            expected_sample_type=sample_type,
            expected_active_first_line=first_line,
            split=split,
            args=parse_replay_args([]),
        )


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


def test_single_model_oracle_cost_counts_only_training_query_mask() -> None:
    checkpoint = {
        "source_indices": np.asarray([3, 0, 2], dtype=np.int64),
        "query_mask": np.asarray(
            [
                [True, True, False],
                [True, False, False],
                [True, True, True],
            ],
            dtype=bool,
        ),
    }
    full_split = np.asarray(["validation", "test", "train", "train"])
    assert _single_oracle_cost(checkpoint, full_split) == 5


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
            json.dumps(
                {
                    "acquisition_mode": method,
                    "high_fidelity_label_costs": {
                        "num_validation_model_selection_labels": 8,
                        "num_calibration_labels": 8,
                        "num_test_audit_labels": 4,
                        "num_full_label_reference_development_labels": 48,
                    },
                    "final_formal_search_thresholds": {
                        "search_num_valid_paths": 12,
                    },
                }
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
    aggregate = pd.read_csv(output / "ieee118_active_label_replay_aggregate.csv")
    final = aggregate.loc[aggregate["queried_training_labels"].eq(10)]
    assert final["validation_model_selection_labels"].eq(8).all()
    assert final["unique_development_high_fidelity_labels"].eq(18).all()
    assert final["total_development_label_reduction_fraction"].eq(0.625).all()
    assert final["formal_search_audit_path_labels"].eq(12).all()


def test_phase3_cost_accounting_does_not_double_count_policy_validation() -> None:
    replay_row = {
        "queried_training_labels": 5,
        "queried_training_label_fraction": 0.25,
        "validation_model_selection_labels": 8,
        "calibration_labels": 8,
        "unique_development_high_fidelity_labels": 13,
        "full_label_reference_development_labels": 28,
        "total_development_label_reduction_fraction": 15 / 28,
        "test_audit_labels": 4,
        "formal_search_audit_path_labels": 12,
    }
    policy = {
        "num_policy_selection_high_fidelity_labels": 6,
        "policy_selection_labels_are_subset_of_training_validation_labels": True,
    }

    cost = build_phase3_high_fidelity_cost_accounting(
        replay_row,
        policy,
        online_probe_n2_calls=3,
    )

    assert cost["training_query_high_fidelity_labels"] == 5
    assert cost["validation_model_selection_high_fidelity_labels"] == 8
    assert cost["policy_selection_high_fidelity_labels"] == 6
    assert cost["policy_selection_incremental_unique_labels"] == 0
    assert cost["unique_development_high_fidelity_labels"] == 13
    assert cost["training_query_label_reduction_fraction"] == pytest.approx(0.75)
    assert cost["total_development_label_reduction_fraction"] == pytest.approx(
        15 / 28
    )
    assert cost["online_probe_n2_calls_included_in_ranked_candidate_count"] == 3
    assert cost["formal_search_audit_path_labels_not_counted_as_development"] == 12


def test_ordered_prefix_cache_does_not_merge_outage_order() -> None:
    cache = OrderedPrefixStateCache()
    calls = []

    def build(value: str) -> str:
        calls.append(value)
        return value

    assert cache.get_or_build("S", ("L001", "L002"), lambda: build("forward")) == "forward"
    assert cache.get_or_build("S", ("L001", "L002"), lambda: build("duplicate")) == "forward"
    assert cache.get_or_build("S", ("L002", "L001"), lambda: build("reverse")) == "reverse"
    assert calls == ["forward", "reverse"]
    assert cache.hits == 1
    assert cache.misses == 2


def test_lazy_prefix_search_matches_exhaustive_product_order_and_delays_s1() -> None:
    labels = ["L001", "L002", "L003"]
    first = {"L001": 0.9, "L002": 0.2, "L003": 0.1}
    second = {
        "L001": {"L002": 0.8, "L003": 0.7},
        "L002": {"L001": 1.0, "L003": 0.5},
        "L003": {"L001": 0.9, "L002": 0.8},
    }
    provider_calls = []

    def provider(first_line: str) -> dict[str, float]:
        provider_calls.append(first_line)
        return second[first_line]

    top_one = lazy_best_first_ordered_n2(
        first_line_scores=first,
        line_labels=labels,
        second_score_provider=provider,
        max_candidates=1,
    )
    assert top_one.ranking["path"].tolist() == ["L001->L002"]
    assert top_one.num_activated_first_lines == 1
    assert provider_calls == ["L001"]

    provider_calls.clear()
    full = lazy_best_first_ordered_n2(
        first_line_scores=first,
        line_labels=labels,
        second_score_provider=provider,
        max_candidates=6,
    )
    exhaustive = sorted(
        (
            (first[first_line] * conditional, f"{first_line}->{second_line}")
            for first_line, values in second.items()
            for second_line, conditional in values.items()
        ),
        key=lambda item: (-item[0], item[1]),
    )
    assert full.ranking["path"].tolist() == [path for _, path in exhaustive]
    assert full.num_activated_first_lines == 3
    assert len(provider_calls) == 3


def test_lazy_prefix_search_accepts_non_probability_physics_bound() -> None:
    result = lazy_best_first_ordered_n2(
        first_line_scores={"L001": 4.0, "L002": 0.5},
        line_labels=["L001", "L002"],
        second_score_provider=lambda first: {
            "L002" if first == "L001" else "L001": 0.25
        },
        max_candidates=2,
    )
    assert result.ranking["path"].tolist() == [
        "L001->L002",
        "L002->L001",
    ]
    assert result.ranking.iloc[0]["path_product_score"] == pytest.approx(1.0)


def test_rank_normalized_physics_scores_are_bounded_and_ordered() -> None:
    normalized = rank_normalize_line_scores(
        np.asarray([10.0, 30.0, 20.0]),
        np.asarray(["L001", "L002", "L003"]),
    )
    assert np.all((normalized > 0.0) & (normalized <= 1.0))
    assert normalized[1] > normalized[2] > normalized[0]


def test_lazy_prefix_metrics_separate_n1_and_n2_physics_costs() -> None:
    ranking = pd.DataFrame(
        [
            {
                "rank": 1,
                "path": "L001->L002",
                "n1_state_constructions_so_far": 1,
                "n2_verifications_so_far": 1,
                "total_physical_evaluations_so_far": 2,
            },
            {
                "rank": 2,
                "path": "L001->L003",
                "n1_state_constructions_so_far": 1,
                "n2_verifications_so_far": 2,
                "total_physical_evaluations_so_far": 3,
            },
        ]
    )
    truth = pd.DataFrame(
        [
            {
                "path": "L001->L002",
                "critical": True,
                "relay_cascade": True,
                "total_load_shed_mw": 10.0,
            },
            {
                "path": "L001->L003",
                "critical": False,
                "relay_cascade": False,
                "total_load_shed_mw": 0.0,
            },
        ]
    )
    metrics = evaluate_lazy_ranking(ranking, truth, [1, 2], method="lazy")
    first_row = metrics.iloc[0]
    assert first_row["n2_physical_verifications"] == 1
    assert first_row["n1_state_constructions"] == 1
    assert first_row["total_physical_evaluations"] == 2
    assert first_row["recall_critical"] == pytest.approx(1.0)
    assert first_row["recall_relay_cascade"] == pytest.approx(1.0)


def test_adaptive_probe_promotes_second_line_using_only_queried_outcomes() -> None:
    labels = ["L001", "L002", "L003", "L004", "L005"]
    fallback = pd.DataFrame(
        [
            {
                "path": f"{first}->{second}",
                "first_line": first,
                "second_line": second,
            }
            for first in labels
            for second in labels
            if first != second
        ]
    )
    oracle_calls: list[str] = []

    def oracle(path: str) -> bool:
        oracle_calls.append(path)
        return path.endswith("->L003")

    result = adaptive_probe_then_promote_ordered_n2(
        first_line_scores={
            "L001": 0.9,
            "L002": 0.8,
            "L003": 0.7,
            "L004": 0.6,
            "L005": 0.5,
        },
        line_labels=labels,
        fallback_ranking=fallback,
        gate_second_lines=["L003", "L004"],
        outcome_oracle=oracle,
        state_builder=lambda first_line: {"first_line": first_line},
        probes_per_second_line=2,
        promotion_min_positives=2,
        max_candidates=7,
    )

    assert result.probe_paths == (
        "L001->L003",
        "L001->L004",
        "L002->L003",
        "L002->L004",
    )
    assert result.promoted_second_lines == ("L003",)
    assert result.ranking["search_stage"].tolist() == [
        "probe",
        "probe",
        "probe",
        "probe",
        "promoted_line_expansion",
        "promoted_line_expansion",
        "fallback",
    ]
    assert result.ranking.iloc[4]["path"] == "L004->L003"
    assert result.ranking.iloc[5]["path"] == "L005->L003"
    assert oracle_calls == result.ranking["path"].tolist()
    assert len(set(oracle_calls)) == len(oracle_calls)


def test_adaptive_probe_constructs_s1_once_and_never_queries_hidden_paths() -> None:
    labels = ["L001", "L002", "L003"]
    fallback = pd.DataFrame(
        [
            {
                "path": "L003->L001",
                "first_line": "L003",
                "second_line": "L001",
            },
            {
                "path": "L002->L001",
                "first_line": "L002",
                "second_line": "L001",
            },
            {
                "path": "L001->L002",
                "first_line": "L001",
                "second_line": "L002",
            },
            {
                "path": "L001->L003",
                "first_line": "L001",
                "second_line": "L003",
            },
            {
                "path": "L002->L003",
                "first_line": "L002",
                "second_line": "L003",
            },
            {
                "path": "L003->L002",
                "first_line": "L003",
                "second_line": "L002",
            },
        ]
    )
    built: list[str] = []
    queried: list[str] = []

    result = adaptive_probe_then_promote_ordered_n2(
        first_line_scores={"L001": 0.9, "L002": 0.8, "L003": 0.7},
        line_labels=labels,
        fallback_ranking=fallback,
        gate_second_lines=["L003"],
        outcome_oracle=lambda path: queried.append(path) or False,
        state_builder=lambda first_line: built.append(first_line) or first_line,
        probes_per_second_line=1,
        promotion_min_positives=1,
        max_candidates=2,
    )

    assert queried == ["L001->L003", "L003->L001"]
    assert built == ["L001", "L003"]
    assert result.num_n2_verifications == 2
    assert result.num_activated_first_lines == 2
    assert result.ranking["n1_state_constructions_so_far"].tolist() == [1, 2]
    assert result.ranking["total_physical_evaluations_so_far"].tolist() == [2, 4]


def test_lazy_evaluator_accepts_feedback_probe_policy_options() -> None:
    args = parse_lazy_prefix_args(
        [
            "--adaptive-probes-per-second-line",
            "3",
            "--adaptive-promotion-min-positives",
            "2",
            "--adaptive-target",
            "critical",
        ]
    )
    assert args.adaptive_probes_per_second_line == 3
    assert args.adaptive_promotion_min_positives == 2
    assert args.adaptive_target == "critical"

    fused = parse_lazy_prefix_args(
        [
            "--fallback-anchor-run-root",
            "anchor_runs",
            "--fallback-anchor-acquisition-mode",
            "random",
            "--fallback-score-fusion",
            "mean",
        ]
    )
    assert fused.fallback_anchor_run_root == Path("anchor_runs")
    assert fused.fallback_anchor_acquisition_mode == "random"
    assert fused.fallback_score_fusion == "mean"


def test_proxy_score_export_keeps_validation_truth_out_of_policy_input() -> None:
    table = pd.DataFrame(
        [
            {
                "seed": 1,
                "split": "validation",
                "line_label": "L001",
                "n1_critical": 1,
                "proxy": 0.2,
            },
            {
                "seed": 1,
                "split": "validation",
                "line_label": "L002",
                "n1_critical": 0,
                "proxy": 0.8,
            },
        ]
    )
    policy, audit = prepare_proxy_score_export(table, "proxy")
    assert "n1_critical" not in policy.columns
    assert policy["line_label"].tolist() == ["L002", "L001"]
    assert policy["selected_proxy_rank"].tolist() == [1, 2]
    assert audit["n1_critical"].tolist() == [0, 1]


def test_iterative_proxy_default_output_matches_policy_consumer_directory() -> None:
    assert (
        parse_iterative_proxy_args([]).output_dir.name
        == "phase3_iterative_lodf_n1_proxy"
    )


def test_probe_feedback_selects_promotions_without_building_fallback_table() -> None:
    calls: list[str] = []
    result = probe_second_line_feedback(
        first_line_scores={"L001": 0.9, "L002": 0.8, "L003": 0.7},
        gate_second_lines=["L002", "L003"],
        query_outcome=lambda path: calls.append(path) or path.endswith("L003"),
        probes_per_second_line=2,
        promotion_min_positives=2,
    )
    assert result.probe_paths == (
        "L001->L002",
        "L001->L003",
        "L003->L002",
        "L002->L003",
    )
    assert result.promoted_second_lines == ("L003",)
    assert result.positive_counts == {"L002": 0, "L003": 2}
    assert calls == list(result.probe_paths)


def test_validation_grid_selects_lowest_cost_recall_feasible_probe_policy() -> None:
    scenario = ValidationProbeScenario(
        seed=11,
        first_line_scores={"L001": 0.9, "L002": 0.8, "L003": 0.7},
        gate_second_lines=("L002", "L003"),
        path_truth={
            "L001->L002": False,
            "L001->L003": True,
            "L002->L001": False,
            "L002->L003": True,
            "L003->L001": False,
            "L003->L002": False,
        },
    )
    per_seed, summary = evaluate_validation_probe_grid(
        [scenario],
        configurations=[(1, 1), (2, 1), (2, 2)],
        gate_size=2,
    )
    selected = select_probe_configuration(
        summary,
        min_mean_gate_recall=0.9,
        min_worst_gate_recall=0.9,
    )
    assert selected["probes_per_second_line"] == 1
    assert selected["promotion_min_positives"] == 1
    assert selected["gate_critical_recall_mean"] == pytest.approx(1.0)
    assert per_seed["num_complete_subset_path_labels"].eq(6).all()
    assert summary["num_complete_subset_validation_path_labels"].eq(6).all()
    assert selected["num_complete_subset_validation_path_labels"] == 6


def test_validation_probe_hit_counts_even_without_line_promotion() -> None:
    scenario = ValidationProbeScenario(
        seed=12,
        first_line_scores={"L001": 0.9, "L002": 0.8, "L003": 0.7},
        gate_second_lines=("L003",),
        path_truth={
            "L001->L003": True,
            "L002->L003": False,
            "L003->L001": False,
            "L003->L002": False,
        },
        source_s1_state_count=3,
        system_first_line_count=3,
    )
    per_seed, summary = evaluate_validation_probe_grid(
        [scenario],
        configurations=[(2, 2)],
        gate_size=1,
    )
    row = per_seed.iloc[0]
    assert row["num_promoted_second_lines"] == 0
    assert row["num_probe_positives"] == 1
    assert row["num_captured_critical_paths"] == 1
    assert row["complete_subset_critical_recall"] == pytest.approx(1.0)
    assert "global_critical_recall" not in per_seed.columns
    assert summary.iloc[0]["complete_subset_critical_recall_mean"] == pytest.approx(
        1.0
    )
    assert row["complete_first_line_fraction_of_source_s1"] == pytest.approx(1.0)


def test_validation_policy_prioritizes_worst_case_recall_before_cost() -> None:
    summary = pd.DataFrame(
        [
            {
                "probes_per_second_line": 1,
                "promotion_min_positives": 1,
                "gate_critical_recall_mean": 0.91,
                "gate_critical_recall_min": 0.81,
                "estimated_n2_queries_mean": 100.0,
            },
            {
                "probes_per_second_line": 3,
                "promotion_min_positives": 1,
                "gate_critical_recall_mean": 0.98,
                "gate_critical_recall_min": 0.94,
                "estimated_n2_queries_mean": 200.0,
            },
        ]
    )
    selected = select_probe_configuration(
        summary,
        min_mean_gate_recall=0.9,
        min_worst_gate_recall=0.8,
    )
    assert selected["probes_per_second_line"] == 3


def test_adaptive_feedback_replaces_blanket_physics_gate_in_fallback() -> None:
    assert apply_second_line_physics_gate(
        0.2,
        in_physics_gate=True,
        physics_gate_floor=0.9,
        adaptive_feedback_enabled=False,
    ) == pytest.approx(0.92)
    assert apply_second_line_physics_gate(
        0.2,
        in_physics_gate=True,
        physics_gate_floor=0.9,
        adaptive_feedback_enabled=True,
    ) == pytest.approx(0.2)


def test_phase3_summary_extracts_separate_n1_and_n2_threshold_costs(
    tmp_path: Path,
) -> None:
    path = tmp_path / "thresholds.csv"
    rows = []
    for target, base, std in (
        ("critical", 1900.0, 10.0),
        ("relay_cascade", 1827.0, 0.0),
    ):
        for offset, fraction in enumerate((0.90, 0.95, 0.99)):
            rows.append(
                {
                    "target": target,
                    "target_fraction": fraction,
                    "candidate_evaluations_mean": base + 100 * offset,
                    "candidate_evaluations_std": std,
                    "n1_state_constructions_mean": 176.0,
                    "total_physical_evaluations_mean": base + 176 + 100 * offset,
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False)
    row = extract_lazy_method_row(path, method="adaptive")
    assert row["critical_K90"] == pytest.approx(1900.0)
    assert row["critical_K90_n1_state_constructions"] == pytest.approx(176.0)
    assert row["critical_K90_total_physical"] == pytest.approx(2076.0)
    assert row["relay_K90"] == pytest.approx(1827.0)


def test_phase3_summary_reports_matched_controls_and_tail_tradeoff() -> None:
    comparison = pd.DataFrame(
        [
            {
                "method": "full_label_GCN_exact_N1_gate",
                "critical_K90": 1793.0,
                "critical_K99": 4305.0,
                "critical_K90_total_physical": 1979.0,
            },
            {
                "method": "MF_active_GCN_adaptive_probe_gate26",
                "critical_K90": 1900.4,
                "critical_K99": 20052.4,
                "critical_K90_total_physical": 2076.4,
            },
            {
                "method": "Phase2_active_GCN_adaptive_probe_gate26",
                "critical_K90": 1918.8,
                "critical_K99": 21171.0,
                "critical_K90_total_physical": 2094.8,
            },
            {
                "method": "random_label_GCN_adaptive_probe_gate26",
                "critical_K90": 1952.4,
                "critical_K99": 11194.2,
                "critical_K90_total_physical": 2128.4,
            },
            {
                "method": "MF_active_plus_random_anchor_mean_adaptive_probe",
                "critical_K90": 1926.8,
                "critical_K99": 10975.2,
                "critical_K90_total_physical": 2102.8,
            },
        ]
    )
    result = build_phase3_relative_comparisons(comparison)
    assert result["main_vs_phase2_active"]["critical_K90_reduction"] == pytest.approx(
        18.4
    )
    assert result["main_vs_random_label"]["critical_K90_reduction"] == pytest.approx(
        52.0
    )
    assert result["tail_anchor_tradeoff"]["critical_K99_reduction"] == pytest.approx(
        9077.2
    )
    assert result["tail_anchor_tradeoff"]["critical_K90_increase"] == pytest.approx(
        26.4
    )
