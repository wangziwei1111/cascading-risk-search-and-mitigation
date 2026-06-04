from __future__ import annotations

from typing import Iterable

import numpy as np
import torch
import torch.nn.functional as F
from pypower.idx_brch import BR_STATUS

from rts79_cascade import line_label_to_index_1based


def make_candidate_mask(case: dict, used_lines: Iterable[str] | None = None) -> np.ndarray:
    branch = case["branch"]
    mask = branch[:, BR_STATUS].astype(int) == 1
    for label in used_lines or []:
        idx = line_label_to_index_1based(str(label).upper()) - 1
        if idx < 0 or idx >= len(mask):
            raise ValueError(f"Invalid used line label: {label}")
        mask[idx] = False
    return mask.astype(bool)


def apply_candidate_probability_mask(probability, candidate_mask):
    if isinstance(probability, torch.Tensor):
        mask = torch.as_tensor(candidate_mask, dtype=torch.bool, device=probability.device)
        while mask.ndim < probability.ndim:
            mask = mask.unsqueeze(0)
        return torch.where(mask, probability, torch.zeros_like(probability))
    prob = np.asarray(probability).copy()
    mask = np.asarray(candidate_mask, dtype=bool)
    while mask.ndim < prob.ndim:
        mask = np.expand_dims(mask, axis=0)
    return np.where(mask, prob, np.zeros_like(prob))


def compute_mask_invalid_loss(probability: torch.Tensor, candidate_mask: torch.Tensor) -> torch.Tensor:
    mask = candidate_mask.to(device=probability.device, dtype=torch.bool)
    while mask.ndim < probability.ndim:
        mask = mask.unsqueeze(0)
    invalid_probability = torch.where(mask, torch.zeros_like(probability), probability)
    return torch.mean(invalid_probability.pow(2))


def compute_relay_priority_loss(
    probability: torch.Tensor,
    loading_ratio: torch.Tensor,
    candidate_mask: torch.Tensor | None = None,
    beta: float = 1.2,
    p_min_relay: float = 0.5,
) -> torch.Tensor:
    relay_candidates = loading_ratio > float(beta)
    if candidate_mask is not None:
        relay_candidates = relay_candidates & candidate_mask.to(device=probability.device, dtype=torch.bool)
    if not torch.any(relay_candidates):
        return probability.sum() * 0.0
    return F.relu(float(p_min_relay) - probability[relay_candidates]).mean()


def compute_loading_monotonic_loss(
    probability: torch.Tensor,
    loading_ratio: torch.Tensor,
    candidate_mask: torch.Tensor | None = None,
    monotonic_margin: float = 0.0,
) -> torch.Tensor:
    if probability.ndim == 1:
        probability = probability.unsqueeze(0)
        loading_ratio = loading_ratio.unsqueeze(0)
        if candidate_mask is not None:
            candidate_mask = candidate_mask.unsqueeze(0)
    losses = []
    for prob_row, loading_row, mask_row in zip(
        probability,
        loading_ratio,
        candidate_mask if candidate_mask is not None else torch.ones_like(probability, dtype=torch.bool),
    ):
        valid_idx = torch.where(mask_row.to(device=probability.device, dtype=torch.bool))[0]
        if valid_idx.numel() < 2:
            continue
        load = loading_row[valid_idx]
        prob = prob_row[valid_idx]
        load_diff = load.unsqueeze(1) - load.unsqueeze(0)
        prob_diff = prob.unsqueeze(0) - prob.unsqueeze(1)
        pair_mask = load_diff > 1e-6
        if torch.any(pair_mask):
            losses.append(F.relu(float(monotonic_margin) + prob_diff[pair_mask]).mean())
    if not losses:
        return probability.sum() * 0.0
    return torch.stack(losses).mean()


def compute_reachable_pairwise_ranking_loss(
    probability: torch.Tensor,
    y_reachable: torch.Tensor,
    candidate_mask: torch.Tensor,
    max_pairs: int = 512,
    margin: float = 0.05,
) -> torch.Tensor:
    if probability.ndim == 1:
        probability = probability.unsqueeze(0)
        y_reachable = y_reachable.unsqueeze(0)
        candidate_mask = candidate_mask.unsqueeze(0)
    losses = []
    for prob_row, label_row, mask_row in zip(probability, y_reachable, candidate_mask):
        valid = mask_row.to(device=probability.device, dtype=torch.bool)
        labels = label_row.to(device=probability.device, dtype=torch.long)
        pos_idx = torch.where(valid & (labels == 1))[0]
        neg_idx = torch.where(valid & (labels == 0))[0]
        if pos_idx.numel() == 0 or neg_idx.numel() == 0:
            continue
        pair_count = int(pos_idx.numel() * neg_idx.numel())
        pos_grid = pos_idx.repeat_interleave(neg_idx.numel())
        neg_grid = neg_idx.repeat(pos_idx.numel())
        if pair_count > int(max_pairs):
            sample = torch.linspace(0, pair_count - 1, steps=int(max_pairs), device=probability.device).long()
            pos_grid = pos_grid[sample]
            neg_grid = neg_grid[sample]
        diff = prob_row[pos_grid] - prob_row[neg_grid]
        losses.append(F.relu(float(margin) - diff).mean())
    if not losses:
        return probability.sum() * 0.0
    loss = torch.stack(losses).mean()
    if not torch.isfinite(loss):
        raise ValueError("reachable_pairwise_ranking_loss produced NaN/Inf.")
    return loss


def compute_physics_constraint_loss(
    probability: torch.Tensor,
    candidate_mask: torch.Tensor,
    loading_ratio: torch.Tensor | None = None,
    lambda_mask: float = 0.0,
    lambda_relay: float = 0.0,
    lambda_monotonic: float = 0.0,
    beta: float = 1.2,
    p_min_relay: float = 0.5,
    monotonic_margin: float = 0.0,
) -> dict[str, torch.Tensor]:
    zero = probability.sum() * 0.0
    mask_loss = compute_mask_invalid_loss(probability, candidate_mask) if lambda_mask else zero
    if loading_ratio is None:
        relay_loss = zero
        monotonic_loss = zero
    else:
        relay_loss = (
            compute_relay_priority_loss(probability, loading_ratio, candidate_mask, beta, p_min_relay)
            if lambda_relay
            else zero
        )
        monotonic_loss = (
            compute_loading_monotonic_loss(probability, loading_ratio, candidate_mask, monotonic_margin)
            if lambda_monotonic
            else zero
        )
    total = float(lambda_mask) * mask_loss + float(lambda_relay) * relay_loss + float(lambda_monotonic) * monotonic_loss
    for name, value in {
        "mask_invalid_loss": mask_loss,
        "relay_priority_loss": relay_loss,
        "loading_monotonic_loss": monotonic_loss,
        "total_physics_loss": total,
    }.items():
        if not torch.isfinite(value):
            raise ValueError(f"{name} produced NaN/Inf.")
    return {
        "mask_invalid_loss": mask_loss,
        "relay_priority_loss": relay_loss,
        "loading_monotonic_loss": monotonic_loss,
        "total_physics_loss": total,
    }
