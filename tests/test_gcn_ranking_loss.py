import sys
from pathlib import Path

import torch

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from gcn_physics_constraints import compute_reachable_pairwise_ranking_loss


def test_ranking_loss_is_zero_when_positive_exceeds_negative_by_margin():
    probability = torch.tensor([[0.90, 0.10, 0.20]], dtype=torch.float32)
    labels = torch.tensor([[1, 0, 0]], dtype=torch.long)
    mask = torch.tensor([[1, 1, 1]], dtype=torch.bool)
    loss = compute_reachable_pairwise_ranking_loss(probability, labels, mask, margin=0.05)
    assert torch.isfinite(loss)
    assert float(loss) < 1e-6


def test_ranking_loss_positive_when_positive_scores_below_negative():
    probability = torch.tensor([[0.10, 0.80, 0.70]], dtype=torch.float32)
    labels = torch.tensor([[1, 0, 0]], dtype=torch.long)
    mask = torch.tensor([[1, 1, 1]], dtype=torch.bool)
    loss = compute_reachable_pairwise_ranking_loss(probability, labels, mask, margin=0.05)
    assert torch.isfinite(loss)
    assert float(loss) > 0.0


def test_ranking_loss_zero_without_positive_or_negative_pairs():
    mask = torch.tensor([[1, 1, 1]], dtype=torch.bool)
    no_positive = compute_reachable_pairwise_ranking_loss(
        torch.tensor([[0.1, 0.2, 0.3]]),
        torch.tensor([[0, 0, 0]]),
        mask,
    )
    no_negative = compute_reachable_pairwise_ranking_loss(
        torch.tensor([[0.1, 0.2, 0.3]]),
        torch.tensor([[1, 1, 1]]),
        mask,
    )
    assert float(no_positive) == 0.0
    assert float(no_negative) == 0.0


def test_ranking_loss_supports_batch_input_and_is_finite():
    probability = torch.tensor([[0.9, 0.2, 0.1], [0.1, 0.8, 0.7]], dtype=torch.float32)
    labels = torch.tensor([[1, 0, 0], [1, 0, 0]], dtype=torch.long)
    mask = torch.tensor([[1, 1, 1], [1, 1, 1]], dtype=torch.bool)
    loss = compute_reachable_pairwise_ranking_loss(probability, labels, mask, max_pairs=2, margin=0.05)
    assert torch.isfinite(loss)
    assert float(loss) > 0.0
