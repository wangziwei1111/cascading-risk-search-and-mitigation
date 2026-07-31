from __future__ import annotations

import numpy as np


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
