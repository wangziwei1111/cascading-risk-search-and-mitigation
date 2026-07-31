from __future__ import annotations

from typing import Any


def masked_focal_cross_entropy(
    logits: Any,
    labels: Any,
    mask: Any,
    class_weight: Any,
    *,
    gamma: float,
) -> Any:
    """Weighted focal cross entropy over physically queried labels only."""

    import torch
    from torch.nn import functional as functional

    if logits.ndim != 3 or logits.shape[-1] != 2:
        raise ValueError("logits must have shape batch x lines x 2.")
    if labels.shape != logits.shape[:2] or mask.shape != labels.shape:
        raise ValueError("labels and mask must align with the GCN logits.")
    if gamma < 0.0:
        raise ValueError("gamma must be non-negative.")
    selected = mask.to(dtype=torch.bool)
    if not bool(selected.any()):
        return logits.sum() * 0.0
    loss = functional.cross_entropy(
        logits.reshape(-1, 2),
        labels.reshape(-1),
        weight=class_weight,
        reduction="none",
    ).reshape_as(labels)
    if gamma > 0.0:
        true_probability = torch.softmax(logits, dim=-1).gather(
            -1, labels.unsqueeze(-1)
        ).squeeze(-1)
        loss = loss * (1.0 - true_probability).pow(float(gamma))
    return loss[selected].mean()


def hard_bipartite_tail_ranking_loss(
    logits: Any,
    labels: Any,
    mask: Any,
    *,
    margin: float = 0.05,
    max_hard_positives: int = 8,
    max_hard_negatives: int = 16,
) -> Any:
    """Lift each state's lowest positives above its highest false alarms."""

    import torch
    from torch.nn import functional as functional

    if logits.ndim != 3 or logits.shape[-1] != 2:
        raise ValueError("logits must have shape batch x lines x 2.")
    if labels.shape != logits.shape[:2] or mask.shape != labels.shape:
        raise ValueError("labels and mask must align with the GCN logits.")
    if max_hard_positives <= 0 or max_hard_negatives <= 0:
        raise ValueError("hard positive and negative limits must be positive.")
    if margin < 0.0:
        raise ValueError("margin must be non-negative.")

    score = logits[..., 1] - logits[..., 0]
    losses = []
    for state_score, state_label, state_mask in zip(score, labels, mask):
        selected = state_mask.to(dtype=torch.bool)
        positives = state_score[selected & state_label.eq(1)]
        negatives = state_score[selected & state_label.eq(0)]
        if positives.numel() == 0 or negatives.numel() == 0:
            continue
        hard_positive = torch.topk(
            positives,
            k=min(int(max_hard_positives), positives.numel()),
            largest=False,
        ).values
        hard_negative = torch.topk(
            negatives,
            k=min(int(max_hard_negatives), negatives.numel()),
            largest=True,
        ).values
        pair_gap = (
            hard_negative.unsqueeze(1)
            - hard_positive.unsqueeze(0)
            + float(margin)
        )
        losses.append(functional.softplus(pair_gap).mean())
    if not losses:
        return logits.sum() * 0.0
    return torch.stack(losses).mean()
