from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse.csgraph import shortest_path


LEAKAGE_FIELDS = frozenset(
    {
        "critical",
        "critical_mechanism",
        "relay_cascade",
        "total_load_shed_mw",
        "num_relay_trips",
        "max_event_loading_ratio",
        "label_critical",
        "label_relay_cascade",
    }
)


def normalized_line_graph_distances(adjacency: np.ndarray) -> np.ndarray:
    """Return finite line-graph shortest-path distances scaled to [0, 1]."""

    matrix = np.asarray(adjacency, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("Line-graph adjacency must be square.")
    distance = shortest_path(matrix, directed=False, unweighted=True)
    finite = np.isfinite(distance)
    if not finite.all():
        raise ValueError("Line graph must be connected for pair interaction features.")
    maximum = float(distance.max())
    return (distance / max(maximum, 1.0)).astype(np.float32)


def build_pair_interaction_features(
    base_probability: np.ndarray,
    x_state: np.ndarray,
    active_first_lines: np.ndarray,
    line_labels: np.ndarray,
    normalized_distance: np.ndarray,
    *,
    mode: str = "gcn_pair_relation",
) -> tuple[np.ndarray, np.ndarray, tuple[str, ...]]:
    """Build deployable first-line/candidate features without outcome fields."""

    probability = np.asarray(base_probability, dtype=np.float32)
    x = np.asarray(x_state, dtype=np.float32)
    active = np.asarray(active_first_lines, dtype=str)
    labels = np.asarray(line_labels, dtype=str)
    distance = np.asarray(normalized_distance, dtype=np.float32)
    if x.ndim != 3 or probability.shape != x.shape[:2]:
        raise ValueError("Probability and state feature arrays must align.")
    if active.shape != (x.shape[0],) or labels.shape != (x.shape[1],):
        raise ValueError("First-line and line-label arrays must align with states.")
    if distance.shape != (x.shape[1], x.shape[1]):
        raise ValueError("Distance matrix must align with line labels.")
    if mode not in {"gcn_logit", "gcn_candidate", "gcn_pair_relation"}:
        raise ValueError(f"Unsupported pair interaction mode: {mode}")

    clipped = np.clip(probability, 1e-6, 1.0 - 1e-6)
    logit = np.log(clipped / (1.0 - clipped))[..., None].astype(np.float32)
    if mode == "gcn_logit":
        return logit, active != "", ("gcn_logit",)
    candidate_names = tuple(f"candidate_x_{idx}" for idx in range(x.shape[2]))
    if mode == "gcn_candidate":
        return (
            np.concatenate([logit, x], axis=2),
            active != "",
            ("gcn_logit", *candidate_names),
        )

    position = {label: idx for idx, label in enumerate(labels.tolist())}
    first_index = np.asarray([position.get(value, -1) for value in active], dtype=np.int64)
    known = first_index >= 0
    first_x = np.zeros((x.shape[0], x.shape[2]), dtype=np.float32)
    first_x[known] = x[np.flatnonzero(known), first_index[known]]
    pair_distance = np.zeros(probability.shape, dtype=np.float32)
    pair_distance[known] = distance[first_index[known]]
    broadcast_first = np.broadcast_to(first_x[:, None, :], x.shape)
    features = np.concatenate(
        [
            logit,
            pair_distance[..., None],
            x,
            broadcast_first,
            np.abs(x - broadcast_first),
            x * broadcast_first,
        ],
        axis=2,
    ).astype(np.float32)
    first_names = tuple(f"first_x_{idx}" for idx in range(x.shape[2]))
    difference_names = tuple(f"abs_difference_x_{idx}" for idx in range(x.shape[2]))
    product_names = tuple(f"interaction_product_x_{idx}" for idx in range(x.shape[2]))
    names = (
        "gcn_logit",
        "normalized_line_graph_distance",
        *candidate_names,
        *first_names,
        *difference_names,
        *product_names,
    )
    if LEAKAGE_FIELDS.intersection(names):
        raise AssertionError("Outcome leakage field entered pair features.")
    return features, known, names


def fit_linear_interaction_head(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    positive_weight: float,
    epochs: int,
    learning_rate: float,
    weight_decay: float,
    random_seed: int,
) -> dict[str, Any]:
    """Fit a tiny weighted linear head while leaving the GCN frozen."""

    import torch

    x = np.asarray(features, dtype=np.float32)
    y = np.asarray(labels, dtype=np.float32)
    if x.ndim != 2 or y.shape != (x.shape[0],):
        raise ValueError("Head training features and labels must align.")
    if not np.isin(y, [0.0, 1.0]).all():
        raise ValueError("Head labels must be binary.")
    if positive_weight <= 0.0 or epochs <= 0 or learning_rate <= 0.0:
        raise ValueError("Head optimization parameters must be positive.")
    mean = x.mean(axis=0)
    scale = np.maximum(x.std(axis=0), 1e-6)
    x_tensor = torch.tensor((x - mean) / scale, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32)
    torch.manual_seed(int(random_seed))
    head = torch.nn.Linear(x.shape[1], 1)
    optimizer = torch.optim.AdamW(
        head.parameters(), lr=float(learning_rate), weight_decay=float(weight_decay)
    )
    positive = torch.tensor([float(positive_weight)], dtype=torch.float32)
    final_loss = float("nan")
    for _ in range(int(epochs)):
        optimizer.zero_grad()
        logits = head(x_tensor).squeeze(1)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            logits, y_tensor, pos_weight=positive
        )
        loss.backward()
        optimizer.step()
        final_loss = float(loss.detach())
    return {
        "feature_mean": mean.astype(np.float32),
        "feature_scale": scale.astype(np.float32),
        "weight": head.weight.detach().cpu().numpy().reshape(-1).astype(np.float32),
        "bias": float(head.bias.detach().cpu().item()),
        "final_train_loss": final_loss,
    }


def predict_linear_interaction_head(
    features: np.ndarray,
    state: dict[str, Any],
) -> np.ndarray:
    x = np.asarray(features, dtype=np.float32)
    mean = np.asarray(state["feature_mean"], dtype=np.float32)
    scale = np.asarray(state["feature_scale"], dtype=np.float32)
    weight = np.asarray(state["weight"], dtype=np.float32)
    if x.shape[-1] != len(mean) or len(mean) != len(scale) or len(mean) != len(weight):
        raise ValueError("Interaction head and feature dimensions do not match.")
    logits = ((x - mean) / scale) @ weight + float(state["bias"])
    return (1.0 / (1.0 + np.exp(-np.clip(logits, -40.0, 40.0)))).astype(np.float32)


class FrozenPairInteractionReranker:
    """Inference wrapper for the compact relation head checkpoint."""

    def __init__(
        self,
        checkpoint_path: Path,
        *,
        adjacency: np.ndarray,
        line_labels: np.ndarray,
    ) -> None:
        import torch

        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        if checkpoint.get("model_type") != "linear_pair_interaction_head":
            raise ValueError("Not an IEEE118 pair interaction head checkpoint.")
        if checkpoint.get("gcn_core_modified") is not False:
            raise ValueError("Pair interaction checkpoint must preserve the GCN core.")
        expected = np.asarray(checkpoint["line_labels"], dtype=str)
        actual = np.asarray(line_labels, dtype=str)
        if not np.array_equal(expected, actual):
            raise ValueError("Pair interaction checkpoint line labels do not align.")
        self.mode = str(checkpoint["feature_mode"])
        self.feature_names = tuple(checkpoint["feature_names"])
        self.state = checkpoint["head_state"]
        self.line_labels = actual
        self.distance = normalized_line_graph_distances(adjacency)

    def predict(
        self,
        base_probability: np.ndarray,
        x_state: np.ndarray,
        first_line: str,
    ) -> np.ndarray:
        features, known, names = build_pair_interaction_features(
            np.asarray(base_probability, dtype=np.float32)[None, :],
            np.asarray(x_state, dtype=np.float32)[None, :, :],
            np.asarray([first_line], dtype=str),
            self.line_labels,
            self.distance,
            mode=self.mode,
        )
        if not bool(known[0]) or names != self.feature_names:
            raise ValueError("Pair interaction inference metadata do not align.")
        return predict_linear_interaction_head(features[0], self.state)
