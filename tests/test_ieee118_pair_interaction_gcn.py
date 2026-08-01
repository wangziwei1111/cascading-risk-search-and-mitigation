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
