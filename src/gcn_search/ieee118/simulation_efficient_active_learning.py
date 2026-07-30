from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


FORBIDDEN_INPUT_FIELDS = frozenset(
    {
        "critical",
        "critical_mechanism",
        "has_overload_cascade",
        "relay_cascade",
        "total_load_shed_mw",
        "num_relay_trips",
        "max_event_loading_ratio",
        "max_pre_redispatch_loading_ratio",
        "label_critical",
        "label_relay_cascade",
        "label_load_shed_positive",
        "y_gcn",
        "y_critical",
        "y_residual_reachable",
    }
)


@dataclass(frozen=True)
class AcquisitionBatch:
    state_indices: np.ndarray
    line_indices: np.ndarray
    acquisition_score: np.ndarray
    predictive_entropy: np.ndarray
    ensemble_disagreement: np.ndarray
    physics_severity: np.ndarray

    @property
    def size(self) -> int:
        return int(len(self.state_indices))

    def pairs(self) -> np.ndarray:
        return np.column_stack((self.state_indices, self.line_indices))


def assert_no_label_leakage(feature_names: Iterable[str]) -> None:
    normalized = {str(name).strip().lower() for name in feature_names}
    leaked = sorted(
        name
        for name in normalized
        if name in FORBIDDEN_INPUT_FIELDS or name.startswith("label_")
    )
    if leaked:
        raise ValueError(f"Outcome/label fields cannot be used as active-GCN inputs: {leaked}")


def binary_entropy(probability: np.ndarray) -> np.ndarray:
    probability = np.asarray(probability, dtype=np.float64)
    clipped = np.clip(probability, 1e-12, 1.0 - 1e-12)
    return -(clipped * np.log(clipped) + (1.0 - clipped) * np.log(1.0 - clipped))


def ensemble_disagreement(member_probability: np.ndarray) -> np.ndarray:
    member_probability = np.asarray(member_probability, dtype=np.float64)
    if member_probability.ndim < 2:
        raise ValueError("member_probability must have member and sample dimensions.")
    if member_probability.shape[0] == 0:
        raise ValueError("member_probability must contain at least one ensemble member.")
    if member_probability.shape[0] == 1:
        return np.zeros_like(member_probability[0])
    mean_probability = member_probability.mean(axis=0)
    mutual_information = binary_entropy(mean_probability) - binary_entropy(member_probability).mean(axis=0)
    return np.maximum(mutual_information, 0.0)


def candidate_pairs(valid_mask: np.ndarray, queried_mask: np.ndarray | None = None) -> np.ndarray:
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if valid_mask.ndim != 2:
        raise ValueError("valid_mask must be a state-by-line matrix.")
    available = valid_mask.copy()
    if queried_mask is not None:
        queried_mask = np.asarray(queried_mask, dtype=bool)
        if queried_mask.shape != valid_mask.shape:
            raise ValueError("queried_mask must match valid_mask.")
        available &= ~queried_mask
    return np.argwhere(available).astype(np.int64)


def build_candidate_descriptors(x_gcn: np.ndarray, pairs: np.ndarray) -> np.ndarray:
    x_gcn = np.asarray(x_gcn, dtype=np.float64)
    pairs = np.asarray(pairs, dtype=np.int64)
    if x_gcn.ndim != 3:
        raise ValueError("x_gcn must have shape states x lines x channels.")
    if pairs.ndim != 2 or pairs.shape[1] != 2:
        raise ValueError("pairs must have shape candidates x 2.")
    if len(pairs) == 0:
        return np.empty((0, 3 * x_gcn.shape[2] + 1), dtype=np.float64)
    state_idx, line_idx = pairs[:, 0], pairs[:, 1]
    if state_idx.min() < 0 or state_idx.max() >= x_gcn.shape[0]:
        raise IndexError("Candidate state index is outside x_gcn.")
    if line_idx.min() < 0 or line_idx.max() >= x_gcn.shape[1]:
        raise IndexError("Candidate line index is outside x_gcn.")
    candidate = x_gcn[state_idx, line_idx]
    state_mean = x_gcn.mean(axis=1)[state_idx]
    state_max = x_gcn.max(axis=1)[state_idx]
    normalized_line = line_idx[:, None] / max(x_gcn.shape[1] - 1, 1)
    descriptor = np.concatenate((candidate, state_mean, state_max, normalized_line), axis=1)
    if not np.isfinite(descriptor).all():
        raise ValueError("Candidate descriptors contain NaN or Inf.")
    return descriptor


def candidate_physics_severity(
    x_gcn: np.ndarray,
    pairs: np.ndarray,
    feature_names: Iterable[str],
) -> np.ndarray:
    names = [str(name).strip().lower() for name in feature_names]
    assert_no_label_leakage(names)
    preferred = ("relay_loading_ratio", "loading_ratio", "x_p")
    feature_idx = next((names.index(name) for name in preferred if name in names), None)
    if feature_idx is None:
        feature_idx = 1 if np.asarray(x_gcn).shape[2] > 1 else 0
    pairs = np.asarray(pairs, dtype=np.int64)
    if len(pairs) == 0:
        return np.empty(0, dtype=np.float64)
    severity = np.asarray(x_gcn, dtype=np.float64)[pairs[:, 0], pairs[:, 1], feature_idx]
    return np.maximum(severity, 0.0)


def _standardize_rows(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("Descriptor values must be a matrix.")
    if len(values) == 0:
        return values.copy()
    scale = values.std(axis=0)
    scale[scale < 1e-12] = 1.0
    return (values - values.mean(axis=0)) / scale


def _rank01(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("Rank input must be one-dimensional.")
    if len(values) <= 1:
        return np.ones(len(values), dtype=np.float64)
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=np.float64)
    position = 0
    while position < len(values):
        end = position + 1
        while end < len(values) and values[order[end]] == values[order[position]]:
            end += 1
        ranks[order[position:end]] = 0.5 * (position + end - 1)
        position = end
    return ranks / float(len(values) - 1)


def farthest_first_indices(
    descriptors: np.ndarray,
    num_select: int,
    *,
    seed_indices: Iterable[int] = (),
    priority: np.ndarray | None = None,
) -> np.ndarray:
    descriptors = _standardize_rows(descriptors)
    if num_select < 0:
        raise ValueError("num_select must be non-negative.")
    if num_select == 0 or len(descriptors) == 0:
        return np.empty(0, dtype=np.int64)
    num_select = min(int(num_select), len(descriptors))
    selected: list[int] = []
    used = np.zeros(len(descriptors), dtype=bool)
    for idx in seed_indices:
        idx = int(idx)
        if idx < 0 or idx >= len(descriptors):
            raise IndexError("seed index is outside descriptor rows.")
        if not used[idx]:
            selected.append(idx)
            used[idx] = True
        if len(selected) == num_select:
            return np.asarray(selected, dtype=np.int64)
    if not selected:
        if priority is None:
            first = 0
        else:
            priority = np.asarray(priority, dtype=np.float64)
            if priority.shape != (len(descriptors),):
                raise ValueError("priority must have one value per descriptor row.")
            first = int(np.argmax(priority))
        selected.append(first)
        used[first] = True
    minimum_distance = np.full(len(descriptors), np.inf, dtype=np.float64)
    for idx in selected:
        distance = np.sum((descriptors - descriptors[idx]) ** 2, axis=1)
        minimum_distance = np.minimum(minimum_distance, distance)
    while len(selected) < num_select:
        minimum_distance[used] = -np.inf
        maximum = np.max(minimum_distance)
        ties = np.flatnonzero(np.isclose(minimum_distance, maximum))
        if priority is not None and len(ties) > 1:
            next_idx = int(ties[np.argmax(priority[ties])])
        else:
            next_idx = int(ties[0])
        selected.append(next_idx)
        used[next_idx] = True
        distance = np.sum((descriptors - descriptors[next_idx]) ** 2, axis=1)
        minimum_distance = np.minimum(minimum_distance, distance)
    return np.asarray(selected, dtype=np.int64)


def select_random_batch(
    valid_mask: np.ndarray,
    batch_size: int,
    *,
    queried_mask: np.ndarray | None = None,
    random_seed: int,
) -> np.ndarray:
    pairs = candidate_pairs(valid_mask, queried_mask)
    if batch_size < 0:
        raise ValueError("batch_size must be non-negative.")
    if len(pairs) == 0 or batch_size == 0:
        return np.empty((0, 2), dtype=np.int64)
    rng = np.random.default_rng(random_seed)
    chosen = rng.choice(len(pairs), size=min(int(batch_size), len(pairs)), replace=False)
    return pairs[chosen]


def select_initial_batch(
    x_gcn: np.ndarray,
    valid_mask: np.ndarray,
    feature_names: Iterable[str],
    batch_size: int,
    *,
    physics_fraction: float = 0.5,
    pool_multiplier: int = 10,
    max_diversity_selections: int = 500,
    random_seed: int = 0,
) -> AcquisitionBatch:
    if not 0.0 <= physics_fraction <= 1.0:
        raise ValueError("physics_fraction must be in [0, 1].")
    if pool_multiplier <= 0:
        raise ValueError("pool_multiplier must be positive.")
    if max_diversity_selections < 0:
        raise ValueError("max_diversity_selections must be non-negative.")
    pairs = candidate_pairs(valid_mask)
    if batch_size < 0:
        raise ValueError("batch_size must be non-negative.")
    batch_size = min(int(batch_size), len(pairs))
    if batch_size == 0:
        empty = np.empty(0, dtype=np.float64)
        return AcquisitionBatch(
            np.empty(0, dtype=np.int64),
            np.empty(0, dtype=np.int64),
            empty,
            empty,
            empty,
            empty,
        )
    severity = candidate_physics_severity(x_gcn, pairs, feature_names)
    physics_count = min(int(round(batch_size * physics_fraction)), batch_size)
    severity_order = np.argsort(-severity, kind="stable")
    physics_indices = severity_order[:physics_count]
    rng = np.random.default_rng(random_seed)
    remaining_mask = np.ones(len(pairs), dtype=bool)
    remaining_mask[physics_indices] = False
    remaining = np.flatnonzero(remaining_mask)
    remaining_count = batch_size - len(physics_indices)
    pool_size = min(
        len(remaining),
        max(remaining_count, remaining_count * int(pool_multiplier)),
    )
    pool = (
        rng.choice(remaining, size=pool_size, replace=False)
        if pool_size
        else np.empty(0, dtype=np.int64)
    )
    diversity_count = min(remaining_count, int(max_diversity_selections))
    if diversity_count:
        descriptors = build_candidate_descriptors(x_gcn, pairs[pool])
        local_diverse = farthest_first_indices(
            descriptors,
            diversity_count,
            priority=_rank01(severity[pool]),
        )
        diverse = pool[local_diverse]
    else:
        local_diverse = np.empty(0, dtype=np.int64)
        diverse = np.empty(0, dtype=np.int64)
    fill_count = remaining_count - len(diverse)
    pool_fill_mask = np.ones(len(pool), dtype=bool)
    pool_fill_mask[local_diverse] = False
    fill = pool[pool_fill_mask][:fill_count]
    chosen = np.concatenate((physics_indices, diverse, fill))
    chosen_pairs = pairs[chosen]
    chosen_severity = severity[chosen]
    return AcquisitionBatch(
        state_indices=chosen_pairs[:, 0],
        line_indices=chosen_pairs[:, 1],
        acquisition_score=_rank01(chosen_severity),
        predictive_entropy=np.zeros(batch_size, dtype=np.float64),
        ensemble_disagreement=np.zeros(batch_size, dtype=np.float64),
        physics_severity=chosen_severity,
    )


def select_active_query_batch(
    member_probability: np.ndarray,
    x_gcn: np.ndarray,
    valid_mask: np.ndarray,
    queried_mask: np.ndarray,
    feature_names: Iterable[str],
    batch_size: int,
    *,
    shortlist_multiplier: int = 10,
    max_diversity_selections: int = 500,
    uncertainty_weight: float = 0.55,
    severity_weight: float = 0.30,
    positive_weight: float = 0.15,
) -> AcquisitionBatch:
    member_probability = np.asarray(member_probability, dtype=np.float64)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    queried_mask = np.asarray(queried_mask, dtype=bool)
    if member_probability.ndim != 3:
        raise ValueError("member_probability must have shape members x states x lines.")
    if max_diversity_selections < 0:
        raise ValueError("max_diversity_selections must be non-negative.")
    if member_probability.shape[1:] != valid_mask.shape:
        raise ValueError("member probabilities must match valid_mask state/line dimensions.")
    pairs = candidate_pairs(valid_mask, queried_mask)
    batch_size = min(max(int(batch_size), 0), len(pairs))
    if batch_size == 0:
        empty = np.empty(0, dtype=np.float64)
        return AcquisitionBatch(
            np.empty(0, dtype=np.int64),
            np.empty(0, dtype=np.int64),
            empty,
            empty,
            empty,
            empty,
        )
    state_idx, line_idx = pairs[:, 0], pairs[:, 1]
    mean_probability_matrix = member_probability.mean(axis=0)
    entropy_matrix = binary_entropy(mean_probability_matrix)
    disagreement_matrix = ensemble_disagreement(member_probability)
    mean_probability = mean_probability_matrix[state_idx, line_idx]
    entropy = entropy_matrix[state_idx, line_idx]
    disagreement = disagreement_matrix[state_idx, line_idx]
    severity = candidate_physics_severity(x_gcn, pairs, feature_names)
    uncertainty = 0.5 * _rank01(entropy) + 0.5 * _rank01(disagreement)
    score = (
        float(uncertainty_weight) * uncertainty
        + float(severity_weight) * _rank01(severity)
        + float(positive_weight) * _rank01(mean_probability)
    )
    shortlist_size = min(
        len(pairs),
        max(batch_size, batch_size * max(int(shortlist_multiplier), 1)),
    )
    shortlist = np.argsort(-score, kind="stable")[:shortlist_size]
    shortlist_pairs = pairs[shortlist]
    diversity_count = min(batch_size, int(max_diversity_selections))
    if diversity_count:
        descriptors = build_candidate_descriptors(x_gcn, shortlist_pairs)
        local = farthest_first_indices(
            descriptors,
            diversity_count,
            priority=score[shortlist],
        )
    else:
        local = np.empty(0, dtype=np.int64)
    fill_count = batch_size - len(local)
    fill_mask = np.ones(len(shortlist), dtype=bool)
    fill_mask[local] = False
    fill = np.flatnonzero(fill_mask)[:fill_count]
    chosen = shortlist[np.concatenate((local, fill))]
    chosen_pairs = pairs[chosen]
    return AcquisitionBatch(
        state_indices=chosen_pairs[:, 0],
        line_indices=chosen_pairs[:, 1],
        acquisition_score=score[chosen],
        predictive_entropy=entropy[chosen],
        ensemble_disagreement=disagreement[chosen],
        physics_severity=severity[chosen],
    )


def update_query_mask(mask: np.ndarray, batch: AcquisitionBatch | np.ndarray) -> np.ndarray:
    updated = np.asarray(mask, dtype=bool).copy()
    pairs = batch.pairs() if isinstance(batch, AcquisitionBatch) else np.asarray(batch, dtype=np.int64)
    if pairs.ndim != 2 or pairs.shape[1] != 2:
        raise ValueError("batch pairs must have shape candidates x 2.")
    if len(pairs):
        updated[pairs[:, 0], pairs[:, 1]] = True
    return updated
