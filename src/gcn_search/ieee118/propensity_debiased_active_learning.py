from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from simulation_efficient_active_learning import (
    _rank01,
    assert_no_label_leakage,
    binary_entropy,
    candidate_physics_severity,
    ensemble_disagreement,
)


@dataclass(frozen=True)
class PropensityQueryBatch:
    state_indices: np.ndarray
    line_indices: np.ndarray
    proposal_probability: np.ndarray
    acquisition_utility: np.ndarray
    predictive_entropy: np.ndarray
    ensemble_disagreement: np.ndarray
    physics_severity: np.ndarray

    @property
    def size(self) -> int:
        return int(len(self.state_indices))

    def pairs(self) -> np.ndarray:
        return np.column_stack((self.state_indices, self.line_indices))


def physics_guided_lure_utility(
    member_probability: np.ndarray,
    x_gcn: np.ndarray,
    pairs: np.ndarray,
    feature_names: Iterable[str],
    *,
    mode: str,
    uncertainty_weight: float = 0.45,
    risk_weight: float = 0.35,
    physics_weight: float = 0.20,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build a non-negative proposal utility without using hidden labels."""
    member_probability = np.asarray(member_probability, dtype=np.float64)
    pairs = np.asarray(pairs, dtype=np.int64)
    if member_probability.ndim != 3:
        raise ValueError("member_probability must have shape members x states x lines.")
    if pairs.ndim != 2 or pairs.shape[1] != 2:
        raise ValueError("pairs must have shape candidates x 2.")
    if mode not in {"entropy", "physics_guided"}:
        raise ValueError("mode must be 'entropy' or 'physics_guided'.")
    if min(uncertainty_weight, risk_weight, physics_weight) < 0.0:
        raise ValueError("LURE utility weights must be non-negative.")
    if uncertainty_weight + risk_weight + physics_weight <= 0.0:
        raise ValueError("At least one LURE utility weight must be positive.")
    names = [str(name) for name in feature_names]
    assert_no_label_leakage(names)
    if len(pairs) == 0:
        empty = np.empty(0, dtype=np.float64)
        return empty, empty, empty, empty

    state_idx, line_idx = pairs[:, 0], pairs[:, 1]
    mean_matrix = member_probability.mean(axis=0)
    entropy_matrix = binary_entropy(mean_matrix)
    disagreement_matrix = ensemble_disagreement(member_probability)
    mean_probability = mean_matrix[state_idx, line_idx]
    entropy = entropy_matrix[state_idx, line_idx]
    disagreement = disagreement_matrix[state_idx, line_idx]
    severity = candidate_physics_severity(x_gcn, pairs, names)
    if mode == "entropy":
        utility = entropy / np.log(2.0)
    else:
        uncertainty = 0.7 * _rank01(entropy) + 0.3 * _rank01(disagreement)
        risk = 0.8 * _rank01(mean_probability) + 0.2 * _rank01(severity)
        total_weight = uncertainty_weight + risk_weight + physics_weight
        utility = (
            uncertainty_weight * uncertainty
            + risk_weight * risk
            + physics_weight * _rank01(severity)
        ) / total_weight
    utility = np.maximum(np.asarray(utility, dtype=np.float64), 0.0)
    if not np.isfinite(utility).all():
        raise ValueError("LURE acquisition utility contains NaN or Inf.")
    return utility, entropy, disagreement, severity


def _proposal_base_weight(
    utility: np.ndarray,
    exploration_mass: float,
    utility_power: float,
) -> np.ndarray:
    utility = np.asarray(utility, dtype=np.float64)
    if utility.ndim != 1:
        raise ValueError("utility must be one-dimensional.")
    if not 0.0 < exploration_mass <= 1.0:
        raise ValueError("exploration_mass must be in (0, 1].")
    if utility_power <= 0.0:
        raise ValueError("utility_power must be positive.")
    if len(utility) == 0:
        return utility.copy()
    if not np.isfinite(utility).all() or np.any(utility < 0.0):
        raise ValueError("utility must be finite and non-negative.")
    powered_utility = np.power(utility, float(utility_power))
    mean_utility = float(powered_utility.mean())
    normalized = (
        powered_utility / mean_utility
        if mean_utility > 1e-12
        else np.ones(len(utility), dtype=np.float64)
    )
    base_weight = (
        float(exploration_mass)
        + (1.0 - float(exploration_mass)) * normalized
    )
    if np.any(base_weight <= 0.0) or not np.isfinite(base_weight).all():
        raise RuntimeError("Randomized LURE proposal lost positive support.")
    return base_weight


def sample_propensity_batch(
    pairs: np.ndarray,
    utility: np.ndarray,
    batch_size: int,
    *,
    exploration_mass: float,
    random_seed: int,
    utility_power: float = 1.0,
    predictive_entropy: np.ndarray | None = None,
    disagreement: np.ndarray | None = None,
    physics_severity: np.ndarray | None = None,
) -> PropensityQueryBatch:
    """Draw an ordered Plackett-Luce batch and retain exact conditional q_m."""
    pairs = np.asarray(pairs, dtype=np.int64)
    utility = np.asarray(utility, dtype=np.float64)
    if pairs.ndim != 2 or pairs.shape[1] != 2:
        raise ValueError("pairs must have shape candidates x 2.")
    if utility.shape != (len(pairs),):
        raise ValueError("utility must have one value per candidate pair.")
    if batch_size < 0:
        raise ValueError("batch_size must be non-negative.")
    batch_size = min(int(batch_size), len(pairs))
    components = []
    for name, value in (
        ("predictive_entropy", predictive_entropy),
        ("disagreement", disagreement),
        ("physics_severity", physics_severity),
    ):
        component = (
            np.zeros(len(pairs), dtype=np.float64)
            if value is None
            else np.asarray(value, dtype=np.float64)
        )
        if component.shape != (len(pairs),):
            raise ValueError(f"{name} must have one value per candidate pair.")
        components.append(component)
    if batch_size == 0:
        empty = np.empty(0, dtype=np.float64)
        return PropensityQueryBatch(
            np.empty(0, dtype=np.int64),
            np.empty(0, dtype=np.int64),
            empty,
            empty,
            empty,
            empty,
            empty,
        )

    base_weight = _proposal_base_weight(
        utility,
        exploration_mass,
        utility_power,
    )
    rng = np.random.default_rng(random_seed)
    # Exponential races generate the sequential weighted-without-replacement law.
    race_key = rng.exponential(scale=1.0 / base_weight)
    if batch_size == len(pairs):
        selected = np.arange(len(pairs), dtype=np.int64)
    else:
        selected = np.argpartition(race_key, batch_size - 1)[:batch_size]
    order = selected[np.argsort(race_key[selected], kind="stable")]
    remaining_mass = float(base_weight.sum())
    proposal_probability = np.empty(batch_size, dtype=np.float64)
    for position, candidate_idx in enumerate(order):
        proposal_probability[position] = (
            base_weight[candidate_idx] / remaining_mass
        )
        remaining_mass -= float(base_weight[candidate_idx])
    if np.any(proposal_probability <= 0.0):
        raise RuntimeError("LURE proposal probability must stay positive.")
    chosen_pairs = pairs[order]
    entropy, disagreement_value, severity = components
    return PropensityQueryBatch(
        state_indices=chosen_pairs[:, 0],
        line_indices=chosen_pairs[:, 1],
        proposal_probability=proposal_probability,
        acquisition_utility=utility[order],
        predictive_entropy=entropy[order],
        ensemble_disagreement=disagreement_value[order],
        physics_severity=severity[order],
    )


def levelled_unbiased_risk_weights(
    pool_size: int,
    proposal_probability_by_order: np.ndarray,
) -> np.ndarray:
    """Return the finite-pool LURE weights from Farquhar et al. (ICLR 2021)."""
    probability = np.asarray(proposal_probability_by_order, dtype=np.float64)
    if pool_size <= 0:
        raise ValueError("pool_size must be positive.")
    if probability.ndim != 1:
        raise ValueError("proposal probabilities must be one-dimensional.")
    num_acquired = len(probability)
    if num_acquired > pool_size:
        raise ValueError("Cannot acquire more labels than the finite pool size.")
    if num_acquired == 0:
        return np.empty(0, dtype=np.float64)
    if np.any(probability <= 0.0) or not np.isfinite(probability).all():
        raise ValueError("proposal probabilities must be finite and positive.")
    if num_acquired == pool_size:
        return np.ones(num_acquired, dtype=np.float64)

    position = np.arange(1, num_acquired + 1, dtype=np.float64)
    remaining_before_draw = float(pool_size) - position + 1.0
    if np.any(probability > 1.0 + 1e-12):
        raise ValueError("A recorded proposal probability exceeds one.")
    level_factor = (
        (float(pool_size) - float(num_acquired))
        / (float(pool_size) - position)
    )
    weight = 1.0 + level_factor * (
        1.0 / (remaining_before_draw * probability) - 1.0
    )
    if np.any(weight < -1e-9) or not np.isfinite(weight).all():
        raise RuntimeError("Computed LURE weights are invalid.")
    return np.maximum(weight, 0.0)


def lure_weight_matrix(
    acquisition_position: np.ndarray,
    acquisition_probability: np.ndarray,
    *,
    pool_size: int,
    num_acquired: int,
) -> np.ndarray:
    acquisition_position = np.asarray(acquisition_position, dtype=np.int64)
    acquisition_probability = np.asarray(
        acquisition_probability,
        dtype=np.float64,
    )
    if acquisition_position.shape != acquisition_probability.shape:
        raise ValueError("LURE acquisition position/probability shapes do not match.")
    selected = acquisition_position >= 0
    if int(selected.sum()) != int(num_acquired):
        raise ValueError("LURE acquisition history does not match num_acquired.")
    position = acquisition_position[selected]
    if not np.array_equal(
        np.sort(position),
        np.arange(num_acquired, dtype=np.int64),
    ):
        raise ValueError("LURE acquisition positions must be contiguous from zero.")
    probability_by_order = np.empty(num_acquired, dtype=np.float64)
    probability_by_order[position] = acquisition_probability[selected]
    weight_by_order = levelled_unbiased_risk_weights(
        pool_size,
        probability_by_order,
    )
    result = np.zeros(acquisition_position.shape, dtype=np.float32)
    result[selected] = weight_by_order[position].astype(np.float32)
    return result


def effective_sample_size(weight: np.ndarray) -> float:
    weight = np.asarray(weight, dtype=np.float64)
    positive = weight[weight > 0.0]
    if len(positive) == 0:
        return 0.0
    return float(positive.sum() ** 2 / np.square(positive).sum())
