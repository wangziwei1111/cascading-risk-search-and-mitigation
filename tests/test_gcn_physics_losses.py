import sys
from pathlib import Path

import torch

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from gcn_physics_constraints import (
    compute_loading_monotonic_loss,
    compute_mask_invalid_loss,
    compute_physics_constraint_loss,
    compute_relay_priority_loss,
)


def test_total_physics_loss_zero_when_lambdas_zero():
    prob = torch.tensor([[0.8, 0.3, 0.2]])
    mask = torch.tensor([[True, False, True]])
    loading = torch.tensor([[1.1, 0.5, 0.2]])
    losses = compute_physics_constraint_loss(prob, mask, loading_ratio=loading)
    assert float(losses["total_physics_loss"]) == 0.0


def test_invalid_probability_increases_mask_loss():
    mask = torch.tensor([[True, False]])
    low = compute_mask_invalid_loss(torch.tensor([[0.2, 0.1]]), mask)
    high = compute_mask_invalid_loss(torch.tensor([[0.2, 0.9]]), mask)
    assert high > low


def test_relay_and_monotonic_losses_behave():
    mask = torch.tensor([[True, True]])
    loading = torch.tensor([[1.2, 0.2]])
    relay_loss = compute_relay_priority_loss(torch.tensor([[0.1, 0.9]]), loading, mask, p_min_relay=0.5)
    assert relay_loss > 0
    monotonic_loss = compute_loading_monotonic_loss(torch.tensor([[0.1, 0.9]]), loading, mask)
    assert monotonic_loss > 0
