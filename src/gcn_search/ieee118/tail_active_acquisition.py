from __future__ import annotations

import numpy as np


def _rank01(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    result = np.zeros_like(values, dtype=np.float64)
    for row in range(values.shape[0]):
        indices = np.flatnonzero(mask[row])
        if len(indices) == 0:
            continue
        selected = values[row, indices]
        unique = np.unique(selected)
        if len(unique) == 1:
            result[row, indices] = 0.5
        else:
            result[row, indices] = np.searchsorted(unique, selected) / (
                len(unique) - 1
            )
    return result


def select_tail_disagreement_batch(
    probability: np.ndarray,
    disagreement: np.ndarray,
    proxy_score: np.ndarray,
    candidate_mask: np.ndarray,
    *,
    batch_size: int,
    missed_risk_weight: float = 0.60,
    uncertainty_weight: float = 0.25,
    disagreement_weight: float = 0.15,
) -> np.ndarray:
    """Select label-free tail candidates with round-robin state diversity."""

    probability = np.asarray(probability, dtype=np.float64)
    disagreement = np.asarray(disagreement, dtype=np.float64)
    proxy_score = np.asarray(proxy_score, dtype=np.float64)
    candidate = np.asarray(candidate_mask, dtype=bool)
    if not (
        probability.shape
        == disagreement.shape
        == proxy_score.shape
        == candidate.shape
    ):
        raise ValueError("Tail acquisition arrays must have the same shape.")
    if probability.ndim != 2:
        raise ValueError("Tail acquisition arrays must be state by line matrices.")
    if batch_size <= 0 or batch_size > int(candidate.sum()):
        raise ValueError("batch_size must fit the available candidate pool.")
    weights = np.asarray(
        [missed_risk_weight, uncertainty_weight, disagreement_weight],
        dtype=np.float64,
    )
    if np.any(weights < 0.0) or not np.isfinite(weights).all() or weights.sum() <= 0:
        raise ValueError("Tail acquisition weights must be finite and non-negative.")
    if not np.isfinite(probability[candidate]).all() or not np.isfinite(
        proxy_score[candidate]
    ).all() or not np.isfinite(disagreement[candidate]).all():
        raise ValueError("Tail acquisition inputs must be finite on candidates.")

    clipped = np.clip(probability, 1e-8, 1.0 - 1e-8)
    entropy = -clipped * np.log(clipped) - (1.0 - clipped) * np.log(
        1.0 - clipped
    )
    proxy_rank = _rank01(proxy_score, candidate)
    uncertainty_rank = _rank01(entropy, candidate)
    disagreement_rank = _rank01(disagreement, candidate)
    missed_risk = proxy_rank * (1.0 - clipped)
    utility = (
        weights[0] * missed_risk
        + weights[1] * uncertainty_rank
        + weights[2] * disagreement_rank
    ) / weights.sum()
    utility[~candidate] = -np.inf

    per_state = []
    for state in range(candidate.shape[0]):
        lines = np.flatnonzero(candidate[state])
        order = sorted(lines.tolist(), key=lambda line: (-utility[state, line], line))
        per_state.append(order)
    selected: list[tuple[int, int]] = []
    depth = 0
    while len(selected) < batch_size:
        added = False
        state_order = sorted(
            range(len(per_state)),
            key=lambda state: (
                -utility[state, per_state[state][depth]]
                if depth < len(per_state[state])
                else float("inf"),
                state,
            ),
        )
        for state in state_order:
            if depth >= len(per_state[state]):
                continue
            selected.append((state, per_state[state][depth]))
            added = True
            if len(selected) == batch_size:
                break
        if not added:
            raise RuntimeError("Tail acquisition exhausted candidates early.")
        depth += 1
    return np.asarray(selected, dtype=np.int64)
