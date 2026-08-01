from __future__ import annotations

import numpy as np
import pandas as pd


def gcn_upper_confidence_scores(
    member_probability: np.ndarray,
    *,
    uncertainty_weight: float,
) -> np.ndarray:
    """Rank uncertain high-risk candidates without reading outcome labels."""

    members = np.asarray(member_probability, dtype=np.float64)
    if members.ndim < 2 or members.shape[0] < 2:
        raise ValueError("GCN UCB requires at least two ensemble members.")
    if uncertainty_weight < 0:
        raise ValueError("GCN uncertainty weight must be non-negative.")
    return members.mean(axis=0) + float(uncertainty_weight) * members.std(axis=0)


def _descending_ranks(
    score: np.ndarray,
    line_labels: np.ndarray,
    valid_mask: np.ndarray,
) -> np.ndarray:
    values = np.asarray(score, dtype=np.float64)
    labels = np.asarray(line_labels, dtype=str)
    valid = np.asarray(valid_mask, dtype=bool)
    if values.shape != labels.shape or values.shape != valid.shape:
        raise ValueError("Scores, line labels, and valid mask must align.")
    ranks = np.zeros(len(values), dtype=np.int64)
    indices = np.flatnonzero(valid)
    order = np.lexsort((labels[indices], -values[indices]))
    ranks[indices[order]] = np.arange(1, len(indices) + 1)
    return ranks


def reciprocal_rank_fusion_scores(
    gcn_probability: np.ndarray,
    physics_proxy: np.ndarray,
    line_labels: np.ndarray,
    valid_mask: np.ndarray,
    *,
    uncertainty: np.ndarray | None = None,
    rrf_k: float = 60.0,
    uncertainty_weight: float = 0.25,
) -> np.ndarray:
    """Fuse label-free rankings while leaving invalid candidates at zero."""

    if rrf_k <= 0:
        raise ValueError("RRF k must be positive.")
    valid = np.asarray(valid_mask, dtype=bool)
    gcn_rank = _descending_ranks(gcn_probability, line_labels, valid)
    proxy_rank = _descending_ranks(physics_proxy, line_labels, valid)
    fused = np.zeros(len(valid), dtype=np.float64)
    fused[valid] = (
        1.0 / (float(rrf_k) + gcn_rank[valid])
        + 1.0 / (float(rrf_k) + proxy_rank[valid])
    )
    if uncertainty is not None and uncertainty_weight > 0:
        uncertainty_rank = _descending_ranks(uncertainty, line_labels, valid)
        fused[valid] += float(uncertainty_weight) / (
            float(rrf_k) + uncertainty_rank[valid]
        )
    return fused


def weighted_two_ranker_rrf_scores(
    first_score: np.ndarray,
    second_score: np.ndarray,
    line_labels: np.ndarray,
    valid_mask: np.ndarray,
    *,
    second_weight: float = 0.5,
    rrf_k: float = 60.0,
) -> np.ndarray:
    """Fuse two candidate rankings without depending on score calibration."""

    if rrf_k <= 0:
        raise ValueError("RRF k must be positive.")
    if not 0.0 <= second_weight <= 1.0:
        raise ValueError("Second-ranker weight must be between zero and one.")
    valid = np.asarray(valid_mask, dtype=bool)
    first_rank = _descending_ranks(first_score, line_labels, valid)
    second_rank = _descending_ranks(second_score, line_labels, valid)
    fused = np.zeros(len(valid), dtype=np.float64)
    fused[valid] = (
        (1.0 - float(second_weight))
        / (float(rrf_k) + first_rank[valid])
        + float(second_weight)
        / (float(rrf_k) + second_rank[valid])
    )
    return fused


def weighted_global_path_rrf_ranking(
    primary: pd.DataFrame,
    secondary: pd.DataFrame,
    *,
    primary_weight: float = 0.5,
    rrf_k: float = 60.0,
) -> pd.DataFrame:
    """Fuse global path rankings while retaining each ranker's score scale."""

    if not 0.0 <= primary_weight <= 1.0:
        raise ValueError("Primary-ranker weight must be between zero and one.")
    if rrf_k <= 0.0:
        raise ValueError("RRF k must be positive.")
    required = {"path", "first_line", "second_line"}
    if required - set(primary) or required - set(secondary):
        raise ValueError("Global RRF rankings are missing path identity columns.")
    if primary["path"].duplicated().any() or secondary["path"].duplicated().any():
        raise ValueError("Global RRF input rankings must contain unique paths.")

    first = primary.reset_index(drop=True).copy()
    second = secondary.reset_index(drop=True).copy()
    first_rank = dict(zip(first["path"].astype(str), np.arange(1, len(first) + 1)))
    second_rank = dict(zip(second["path"].astype(str), np.arange(1, len(second) + 1)))
    union = pd.concat([first, second], ignore_index=True).drop_duplicates(
        "path", keep="first"
    )
    missing_first = len(first) + 1
    missing_second = len(second) + 1
    union["primary_global_rank"] = union["path"].astype(str).map(
        lambda value: first_rank.get(value, missing_first)
    )
    union["secondary_global_rank"] = union["path"].astype(str).map(
        lambda value: second_rank.get(value, missing_second)
    )
    union["global_rrf_score"] = (
        float(primary_weight)
        / (float(rrf_k) + union["primary_global_rank"].to_numpy(dtype=float))
        + (1.0 - float(primary_weight))
        / (float(rrf_k) + union["secondary_global_rank"].to_numpy(dtype=float))
    )
    union = union.sort_values(
        ["global_rrf_score", "path"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    union["rank"] = np.arange(1, len(union) + 1)
    return union
