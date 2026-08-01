from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

torch = pytest.importorskip("torch")

from pair_interaction_reranker import (  # noqa: E402
    LEAKAGE_FIELDS,
    FrozenPairInteractionReranker,
    build_pair_interaction_features,
    fit_linear_interaction_head,
    normalized_line_graph_distances,
    predict_linear_interaction_head,
)


def _example() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    probability = np.asarray([[0.2, 0.4, 0.6], [0.3, 0.5, 0.7]], dtype=np.float32)
    x = np.arange(2 * 3 * 4, dtype=np.float32).reshape(2, 3, 4) / 10.0
    active = np.asarray(["L001", "L003"])
    labels = np.asarray(["L001", "L002", "L003"])
    return probability, x, active, labels


def test_pair_features_encode_first_candidate_relation_without_leakage() -> None:
    probability, x, active, labels = _example()
    adjacency = np.asarray([[1, 1, 0], [1, 1, 1], [0, 1, 1]], dtype=float)
    distance = normalized_line_graph_distances(adjacency)

    features, known, names = build_pair_interaction_features(
        probability, x, active, labels, distance
    )

    assert features.shape == (2, 3, 18)
    assert known.tolist() == [True, True]
    assert not LEAKAGE_FIELDS.intersection(names)
    assert not np.array_equal(features[0, 1], features[1, 1])


def test_linear_interaction_head_learns_separable_relation() -> None:
    x = np.asarray([[-2.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [2.0, 0.0]], dtype=np.float32)
    y = np.asarray([0, 0, 1, 1], dtype=np.int64)
    state = fit_linear_interaction_head(
        x,
        y,
        positive_weight=1.0,
        epochs=200,
        learning_rate=0.05,
        weight_decay=0.0,
        random_seed=7,
    )
    probability = predict_linear_interaction_head(x, state)

    assert probability[:2].max() < probability[2:].min()


def test_frozen_reranker_validates_metadata_and_predicts(tmp_path: Path) -> None:
    probability, x, active, labels = _example()
    adjacency = np.asarray([[1, 1, 0], [1, 1, 1], [0, 1, 1]], dtype=float)
    distance = normalized_line_graph_distances(adjacency)
    features, _, names = build_pair_interaction_features(
        probability[:1], x[:1], active[:1], labels, distance
    )
    state = {
        "feature_mean": np.zeros(features.shape[-1], dtype=np.float32),
        "feature_scale": np.ones(features.shape[-1], dtype=np.float32),
        "weight": np.zeros(features.shape[-1], dtype=np.float32),
        "bias": 0.0,
    }
    checkpoint = tmp_path / "head.pt"
    torch.save(
        {
            "model_type": "linear_pair_interaction_head",
            "gcn_core_modified": False,
            "feature_mode": "gcn_pair_relation",
            "feature_names": names,
            "line_labels": labels,
            "head_state": state,
        },
        checkpoint,
    )

    reranker = FrozenPairInteractionReranker(
        checkpoint, adjacency=adjacency, line_labels=labels
    )
    result = reranker.predict(probability[0], x[0], "L001")

    assert result.shape == (3,)
    assert result == pytest.approx(np.full(3, 0.5))


def test_prospective_cli_accepts_explicit_interaction_head() -> None:
    from run_ieee118_prospective_oracle import parse_args

    args = parse_args(
        [
            "--seed",
            "20261206",
            "--interaction-head-checkpoint",
            "head.pt",
        ]
    )
    assert args.interaction_head_checkpoint == Path("head.pt")


def test_weighted_rrf_preserves_both_rankers_and_valid_mask() -> None:
    from tail_rank_fusion import weighted_two_ranker_rrf_scores

    labels = np.asarray(["L001", "L002", "L003", "L004"])
    valid = np.asarray([True, True, True, False])
    first = np.asarray([0.9, 0.1, 0.5, 1.0])
    second = np.asarray([0.1, 0.9, 0.5, 1.0])

    fused = weighted_two_ranker_rrf_scores(
        first, second, labels, valid, second_weight=0.5, rrf_k=60.0
    )

    assert fused[0] == pytest.approx(fused[1])
    assert fused[2] < fused[0]
    assert fused[3] == 0.0


def test_interaction_fusion_cli_is_explicit() -> None:
    from run_ieee118_prospective_oracle import parse_args

    args = parse_args(
        [
            "--seed",
            "20261211",
            "--interaction-head-checkpoint",
            "head.pt",
            "--interaction-fusion-mode",
            "global_rrf",
            "--interaction-fusion-weight",
            "0.7",
        ]
    )
    assert args.interaction_fusion_mode == "global_rrf"
    assert args.interaction_fusion_weight == pytest.approx(0.7)


def test_global_path_rrf_fuses_complete_path_rankings() -> None:
    import pandas as pd

    from tail_rank_fusion import weighted_global_path_rrf_ranking

    primary = pd.DataFrame(
        [
            {"path": "L001->L002", "first_line": "L001", "second_line": "L002"},
            {"path": "L001->L003", "first_line": "L001", "second_line": "L003"},
        ]
    )
    secondary = primary.iloc[::-1].reset_index(drop=True)

    fused = weighted_global_path_rrf_ranking(
        primary, secondary, primary_weight=0.5, rrf_k=60.0
    )

    assert set(fused["path"]) == set(primary["path"])
    assert fused["global_rrf_score"].nunique() == 1
    assert fused["path"].tolist() == sorted(primary["path"].tolist())
