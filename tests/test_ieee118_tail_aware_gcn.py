from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
IEEE118_DIR = ROOT / "src" / "gcn_search" / "ieee118"
LEGACY_DIR = ROOT / "src" / "gcn_search" / "legacy_rts79"
for path in (IEEE118_DIR, LEGACY_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


torch = pytest.importorskip("torch")

from tail_aware_gcn_loss import (  # noqa: E402
    hard_bipartite_tail_ranking_loss,
    masked_focal_cross_entropy,
)
from tail_active_acquisition import select_tail_disagreement_batch  # noqa: E402
from train_rts79_paper_gcn import PaperStyleRts79Gcn  # noqa: E402


def _binary_logits(scores: list[list[float]]) -> torch.Tensor:
    positive = torch.tensor(scores, dtype=torch.float32)
    return torch.stack((torch.zeros_like(positive), positive), dim=-1)


def test_tail_rank_loss_penalizes_missed_positive_above_ordered_pair() -> None:
    labels = torch.tensor([[1, 0, 1, 0]], dtype=torch.long)
    mask = torch.ones_like(labels, dtype=torch.bool)
    ordered = _binary_logits([[3.0, -2.0, 2.0, -1.0]])
    reversed_order = _binary_logits([[-2.0, 3.0, -1.0, 2.0]])

    good = hard_bipartite_tail_ranking_loss(ordered, labels, mask)
    bad = hard_bipartite_tail_ranking_loss(reversed_order, labels, mask)

    assert bad > good
    assert float(bad) > 1.0


def test_tail_rank_loss_pushes_hard_positive_up_and_hard_negative_down() -> None:
    logits = _binary_logits([[-1.0, 2.0, 1.0, -2.0]]).requires_grad_(True)
    labels = torch.tensor([[1, 0, 1, 0]], dtype=torch.long)
    mask = torch.ones_like(labels, dtype=torch.bool)

    loss = hard_bipartite_tail_ranking_loss(
        logits,
        labels,
        mask,
        max_hard_positives=1,
        max_hard_negatives=1,
    )
    loss.backward()

    positive_score_gradient = logits.grad[0, 0, 1] - logits.grad[0, 0, 0]
    negative_score_gradient = logits.grad[0, 1, 1] - logits.grad[0, 1, 0]
    assert positive_score_gradient < 0.0
    assert negative_score_gradient > 0.0


def test_tail_rank_loss_ignores_unqueried_labels() -> None:
    labels = torch.tensor([[1, 0, 1, 0]], dtype=torch.long)
    mask = torch.tensor([[True, True, False, False]])
    first = _binary_logits([[-1.0, 2.0, -100.0, 100.0]])
    second = _binary_logits([[-1.0, 2.0, 100.0, -100.0]])

    assert hard_bipartite_tail_ranking_loss(
        first, labels, mask
    ) == pytest.approx(hard_bipartite_tail_ranking_loss(second, labels, mask))


def test_masked_focal_cross_entropy_downweights_easy_examples() -> None:
    labels = torch.tensor([[1, 0]], dtype=torch.long)
    mask = torch.ones_like(labels, dtype=torch.bool)
    easy = _binary_logits([[8.0, -8.0]])
    hard = _binary_logits([[0.1, -0.1]])
    weight = torch.tensor([1.0, 4.0], dtype=torch.float32)

    easy_loss = masked_focal_cross_entropy(easy, labels, mask, weight, gamma=2.0)
    hard_loss = masked_focal_cross_entropy(hard, labels, mask, weight, gamma=2.0)

    assert hard_loss > easy_loss


def test_tail_aware_training_keeps_original_model_class() -> None:
    from train_ieee118_tail_aware_gcn import (
        FORMAL_MODEL_CLASS,
        critical_retrieval_k,
    )

    assert FORMAL_MODEL_CLASS is PaperStyleRts79Gcn
    probability = torch.tensor([[0.9, 0.8, 0.7, 0.6]])
    labels = torch.tensor([[1, 0, 1, 0]])
    mask = torch.ones_like(labels, dtype=torch.bool)
    assert critical_retrieval_k(probability, labels, mask, 0.5) == 1
    assert critical_retrieval_k(probability, labels, mask, 1.0) == 3

    from run_ieee118_prospective_oracle import parse_args

    args = parse_args(["--seed", "20260709", "--gcn-checkpoint", "tail.pt"])
    assert args.gcn_checkpoint == Path("tail.pt")


def test_tail_acquisition_prioritizes_low_gcn_high_physics_candidate() -> None:
    import numpy as np

    probability = np.asarray([[0.90, 0.05, 0.40], [0.40, 0.40, 0.40]])
    disagreement = np.zeros_like(probability)
    proxy = np.asarray([[0.1, 10.0, 0.2], [0.1, 0.2, 0.3]])
    candidate = np.ones_like(probability, dtype=bool)

    selected = select_tail_disagreement_batch(
        probability,
        disagreement,
        proxy,
        candidate,
        batch_size=1,
    )

    assert selected.tolist() == [[0, 1]]


def test_tail_acquisition_is_reproducible_and_covers_states() -> None:
    import numpy as np

    probability = np.full((3, 4), 0.2)
    disagreement = np.zeros_like(probability)
    proxy = np.tile(np.asarray([4.0, 3.0, 2.0, 1.0]), (3, 1))
    candidate = np.ones_like(probability, dtype=bool)

    first = select_tail_disagreement_batch(
        probability,
        disagreement,
        proxy,
        candidate,
        batch_size=3,
    )
    second = select_tail_disagreement_batch(
        probability,
        disagreement,
        proxy,
        candidate,
        batch_size=3,
    )

    assert np.array_equal(first, second)
    assert sorted(first[:, 0].tolist()) == [0, 1, 2]


def test_rrf_combines_complementary_label_free_rankings() -> None:
    import numpy as np

    from tail_rank_fusion import reciprocal_rank_fusion_scores

    labels = np.asarray(["L001", "L002", "L003", "L004"])
    valid = np.asarray([True, True, True, False])
    fused = reciprocal_rank_fusion_scores(
        np.asarray([0.9, 0.8, 0.1, 1.0]),
        np.asarray([0.1, 0.9, 0.8, 1.0]),
        labels,
        valid,
        rrf_k=60.0,
    )

    assert fused[1] > fused[0]
    assert fused[1] > fused[2]
    assert fused[3] == 0.0


def test_prospective_fallback_fusion_cli_is_explicit() -> None:
    from run_ieee118_prospective_oracle import parse_args

    args = parse_args(
        [
            "--seed",
            "20260709",
            "--fallback-score-mode",
            "rrf_gcn_proxy_uncertainty",
        ]
    )
    assert args.fallback_score_mode == "rrf_gcn_proxy_uncertainty"
    assert args.rrf_k == 60.0
