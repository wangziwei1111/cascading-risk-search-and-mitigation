from __future__ import annotations

from typing import Any

import torch
from torch import nn


class MechanismAwareTrainingWrapper(nn.Module):
    """Training-only heads around an unchanged PaperStyleRts79Gcn instance."""

    def __init__(self, primary_model: nn.Module, hidden_channels: int = 4) -> None:
        super().__init__()
        self.primary_model = primary_model
        self.relay_head = nn.Linear(int(hidden_channels), 1)
        self.island_head = nn.Linear(int(hidden_channels), 1)
        self.load_shed_head = nn.Linear(int(hidden_channels), 1)

    def forward(
        self, x: torch.Tensor, adjacency_powers: torch.Tensor
    ) -> dict[str, torch.Tensor]:
        primary = self.primary_model
        hidden = torch.relu(primary.graph_1(x, adjacency_powers))
        hidden = torch.relu(primary.graph_2(hidden, adjacency_powers))
        return {
            "critical_logits": primary.classifier(hidden),
            "log1p_relay_trips": self.relay_head(hidden).squeeze(-1),
            "log1p_island_shed": self.island_head(hidden).squeeze(-1),
            "log1p_load_shed": self.load_shed_head(hidden).squeeze(-1),
        }


def masked_binary_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    mask: torch.Tensor,
    *,
    positive_weight: float,
) -> torch.Tensor:
    if not bool(mask.any()):
        return logits.sum() * 0.0
    weight = torch.tensor(float(positive_weight), dtype=logits.dtype)
    values = nn.functional.binary_cross_entropy_with_logits(
        logits,
        targets.to(dtype=logits.dtype),
        reduction="none",
        pos_weight=weight,
    )
    return values[mask].mean()


def masked_positive_severity_loss(
    prediction: torch.Tensor,
    target: torch.Tensor,
    known_mask: torch.Tensor,
) -> torch.Tensor:
    mask = known_mask & (target > 0)
    if not bool(mask.any()):
        return prediction.sum() * 0.0
    return nn.functional.smooth_l1_loss(
        prediction[mask], target[mask].to(dtype=prediction.dtype)
    )


def auxiliary_positive_weight(target: Any, mask: Any, cap: float = 20.0) -> float:
    truth = torch.as_tensor(target, dtype=torch.bool)
    known = torch.as_tensor(mask, dtype=torch.bool)
    positives = int((truth & known).sum())
    negatives = int((~truth & known).sum())
    if positives == 0:
        return 1.0
    return float(min(max(negatives / positives, 1.0), float(cap)))


def primary_protected_pcgrad(
    primary_gradients: list[torch.Tensor | None],
    auxiliary_gradients: list[torch.Tensor | None],
    shared_mask: list[bool],
) -> tuple[list[torch.Tensor | None], dict[str, float | bool]]:
    """Project only auxiliary shared gradients that oppose the primary task."""

    if not (
        len(primary_gradients) == len(auxiliary_gradients) == len(shared_mask)
    ):
        raise ValueError("PCGrad inputs must have the same length.")
    pairs = [
        (primary, auxiliary)
        for primary, auxiliary, shared in zip(
            primary_gradients, auxiliary_gradients, shared_mask
        )
        if shared and primary is not None and auxiliary is not None
    ]
    dot = sum((primary * auxiliary).sum() for primary, auxiliary in pairs)
    primary_norm_sq = sum((primary * primary).sum() for primary, _ in pairs)
    auxiliary_norm_sq = sum((auxiliary * auxiliary).sum() for _, auxiliary in pairs)
    conflict = bool(pairs) and float(dot.detach()) < 0.0
    coefficient = (
        dot / primary_norm_sq.clamp_min(1e-12)
        if conflict
        else torch.zeros((), dtype=dot.dtype if pairs else torch.float32)
    )
    combined: list[torch.Tensor | None] = []
    for primary, auxiliary, shared in zip(
        primary_gradients, auxiliary_gradients, shared_mask
    ):
        projected_auxiliary = auxiliary
        if conflict and shared and primary is not None and auxiliary is not None:
            projected_auxiliary = auxiliary - coefficient * primary
        if primary is None:
            combined.append(projected_auxiliary)
        elif projected_auxiliary is None:
            combined.append(primary)
        else:
            combined.append(primary + projected_auxiliary)
    cosine = float(
        dot.detach()
        / (primary_norm_sq.sqrt() * auxiliary_norm_sq.sqrt()).clamp_min(1e-12)
    ) if pairs else 0.0
    return combined, {
        "gradient_conflict": conflict,
        "primary_auxiliary_cosine": cosine,
    }
