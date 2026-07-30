from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class RiskCalibration:
    threshold: float
    alpha: float
    num_calibration_units: int
    num_valid_candidates: int
    num_selected_candidates: int
    empirical_mean_missed_positive_fraction: float
    crc_upper_risk: float
    feasible: bool

    def to_dict(self) -> dict:
        return asdict(self)


def missed_positive_fraction_by_unit(
    labels: np.ndarray,
    selected_mask: np.ndarray,
    valid_mask: np.ndarray,
) -> np.ndarray:
    labels = np.asarray(labels, dtype=bool)
    selected_mask = np.asarray(selected_mask, dtype=bool)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if labels.shape != selected_mask.shape or labels.shape != valid_mask.shape:
        raise ValueError("labels, selected_mask, and valid_mask must have matching shapes.")
    if labels.ndim != 2:
        raise ValueError("Risk-control arrays must be state-by-candidate matrices.")
    positive = labels & valid_mask
    total_positive = positive.sum(axis=1)
    missed = (positive & ~selected_mask).sum(axis=1)
    loss = np.zeros(labels.shape[0], dtype=np.float64)
    has_positive = total_positive > 0
    loss[has_positive] = missed[has_positive] / total_positive[has_positive]
    return loss


def crc_upper_mean_risk(empirical_mean_risk: float, num_units: int, bound: float = 1.0) -> float:
    if num_units <= 0:
        raise ValueError("num_units must be positive.")
    if bound <= 0:
        raise ValueError("bound must be positive.")
    return (
        num_units * float(empirical_mean_risk) + float(bound)
    ) / float(num_units + 1)


def calibrate_missed_positive_risk(
    probability: np.ndarray,
    labels: np.ndarray,
    valid_mask: np.ndarray,
    *,
    alpha: float,
) -> RiskCalibration:
    probability = np.asarray(probability, dtype=np.float64)
    labels = np.asarray(labels, dtype=bool)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if probability.shape != labels.shape or probability.shape != valid_mask.shape:
        raise ValueError("probability, labels, and valid_mask must have matching shapes.")
    if probability.ndim != 2:
        raise ValueError("Calibration arrays must be state-by-candidate matrices.")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1).")
    active_units = valid_mask.any(axis=1)
    probability = probability[active_units]
    labels = labels[active_units]
    valid_mask = valid_mask[active_units]
    num_units = int(len(probability))
    if num_units == 0:
        raise ValueError("Calibration data contains no valid candidates.")
    if not np.isfinite(probability[valid_mask]).all():
        raise ValueError("Valid calibration probabilities contain NaN or Inf.")

    positive = labels & valid_mask
    total_positive = positive.sum(axis=1)
    missed_positive = total_positive.astype(np.int64).copy()
    losses = np.zeros(num_units, dtype=np.float64)
    has_positive = total_positive > 0
    losses[has_positive] = 1.0
    loss_sum = float(losses.sum())

    flat_state, flat_line = np.where(valid_mask)
    flat_score = probability[flat_state, flat_line]
    order = np.argsort(-flat_score, kind="stable")
    selected_count = 0
    best_threshold = float("-inf")
    best_selected_count = int(valid_mask.sum())
    best_empirical = 0.0
    best_upper = crc_upper_mean_risk(0.0, num_units)
    feasible = best_upper <= alpha

    position = 0
    while position < len(order):
        score = float(flat_score[order[position]])
        end = position
        while end < len(order) and float(flat_score[order[end]]) == score:
            entry = order[end]
            state_idx = int(flat_state[entry])
            line_idx = int(flat_line[entry])
            if positive[state_idx, line_idx] and total_positive[state_idx] > 0:
                old_loss = missed_positive[state_idx] / total_positive[state_idx]
                missed_positive[state_idx] -= 1
                new_loss = missed_positive[state_idx] / total_positive[state_idx]
                loss_sum += float(new_loss - old_loss)
            end += 1
        selected_count = end
        empirical = loss_sum / num_units
        upper = crc_upper_mean_risk(empirical, num_units)
        if upper <= alpha:
            best_threshold = score
            best_selected_count = selected_count
            best_empirical = empirical
            best_upper = upper
            feasible = True
            break
        position = end

    return RiskCalibration(
        threshold=float(best_threshold),
        alpha=float(alpha),
        num_calibration_units=num_units,
        num_valid_candidates=int(valid_mask.sum()),
        num_selected_candidates=int(best_selected_count),
        empirical_mean_missed_positive_fraction=float(best_empirical),
        crc_upper_risk=float(best_upper),
        feasible=bool(feasible),
    )


def selected_for_physical_verification(
    probability: np.ndarray,
    valid_mask: np.ndarray,
    calibration: RiskCalibration,
    *,
    uncertainty: np.ndarray | None = None,
    uncertainty_threshold: float | None = None,
) -> np.ndarray:
    probability = np.asarray(probability, dtype=np.float64)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if probability.shape != valid_mask.shape:
        raise ValueError("probability and valid_mask must have matching shapes.")
    selected = valid_mask & (probability >= calibration.threshold)
    if uncertainty is not None:
        if uncertainty_threshold is None:
            raise ValueError("uncertainty_threshold is required when uncertainty is provided.")
        uncertainty = np.asarray(uncertainty, dtype=np.float64)
        if uncertainty.shape != valid_mask.shape:
            raise ValueError("uncertainty must match valid_mask.")
        selected |= valid_mask & (uncertainty >= float(uncertainty_threshold))
    return selected
