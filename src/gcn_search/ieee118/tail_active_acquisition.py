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


def select_groupwise_dense_batch(
    probability: np.ndarray,
    disagreement: np.ndarray,
    proxy_score: np.ndarray,
    candidate_mask: np.ndarray,
    *,
    batch_size: int,
    group_ids: np.ndarray | None = None,
    state_top_fraction: float = 0.10,
) -> np.ndarray:
    """Spend a fixed query budget on nearly complete, high-risk state lists.

    State selection is label-free.  It uses the same missed-risk, uncertainty,
    and ensemble-disagreement evidence as the scattered selector, then queries
    every available candidate in a selected state before moving to the next.
    Optional group IDs provide round-robin diversity across load scenarios.
    """

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
        raise ValueError("Groupwise acquisition arrays must have the same shape.")
    if probability.ndim != 2:
        raise ValueError("Groupwise acquisition arrays must be state by line matrices.")
    if batch_size <= 0 or batch_size > int(candidate.sum()):
        raise ValueError("batch_size must fit the available candidate pool.")
    if not 0.0 < state_top_fraction <= 1.0:
        raise ValueError("state_top_fraction must be in (0, 1].")
    if group_ids is None:
        groups = np.arange(candidate.shape[0], dtype=np.int64)
    else:
        groups = np.asarray(group_ids)
        if groups.shape != (candidate.shape[0],):
            raise ValueError("group_ids must contain one value per state.")
    if not np.isfinite(probability[candidate]).all() or not np.isfinite(
        proxy_score[candidate]
    ).all() or not np.isfinite(disagreement[candidate]).all():
        raise ValueError("Groupwise acquisition inputs must be finite on candidates.")

    clipped = np.clip(probability, 1e-8, 1.0 - 1e-8)
    entropy = -clipped * np.log(clipped) - (1.0 - clipped) * np.log(
        1.0 - clipped
    )
    proxy_rank = _rank01(proxy_score, candidate)
    uncertainty_rank = _rank01(entropy, candidate)
    disagreement_rank = _rank01(disagreement, candidate)
    utility = (
        0.60 * proxy_rank * (1.0 - clipped)
        + 0.25 * uncertainty_rank
        + 0.15 * disagreement_rank
    )
    utility[~candidate] = -np.inf

    state_utility = np.full(candidate.shape[0], -np.inf, dtype=np.float64)
    for state in np.flatnonzero(candidate.any(axis=1)):
        values = utility[state, candidate[state]]
        top_count = max(1, int(np.ceil(state_top_fraction * len(values))))
        state_utility[state] = float(np.partition(values, -top_count)[-top_count:].mean())

    group_to_states: dict[object, list[int]] = {}
    for state in np.flatnonzero(candidate.any(axis=1)):
        group_to_states.setdefault(groups[state].item(), []).append(int(state))
    for states in group_to_states.values():
        states.sort(key=lambda state: (-state_utility[state], state))
    ordered_groups = sorted(
        group_to_states,
        key=lambda group: (-state_utility[group_to_states[group][0]], str(group)),
    )
    state_order: list[int] = []
    depth = 0
    while True:
        added = False
        for group in ordered_groups:
            states = group_to_states[group]
            if depth < len(states):
                state_order.append(states[depth])
                added = True
        if not added:
            break
        depth += 1

    selected: list[tuple[int, int]] = []
    for state in state_order:
        lines = np.flatnonzero(candidate[state])
        lines = np.asarray(
            sorted(lines.tolist(), key=lambda line: (-utility[state, line], line)),
            dtype=np.int64,
        )
        take = min(len(lines), batch_size - len(selected))
        selected.extend((int(state), int(line)) for line in lines[:take])
        if len(selected) == batch_size:
            break
    if len(selected) != batch_size:
        raise RuntimeError("Groupwise acquisition exhausted candidates early.")
    return np.asarray(selected, dtype=np.int64)
