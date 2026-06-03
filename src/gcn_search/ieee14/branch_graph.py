from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BranchGraph:
    lines: list[tuple[int, int]]
    edge_index: np.ndarray
    adjacency: np.ndarray
    degrees: np.ndarray


def build_branch_graph(case: dict) -> BranchGraph:
    """Build the IEEE14 branch graph where branches sharing a bus are adjacent."""
    lines = [(int(a), int(b)) for a, b in case["lines"]]
    num_lines = len(lines)
    adjacency = np.zeros((num_lines, num_lines), dtype=np.float32)
    for i, line_i in enumerate(lines):
        buses_i = set(line_i)
        for j in range(i + 1, num_lines):
            if buses_i.intersection(lines[j]):
                adjacency[i, j] = 1.0
                adjacency[j, i] = 1.0
    degrees = adjacency.sum(axis=1).astype(np.float32)
    edge_index = np.array(np.nonzero(adjacency), dtype=np.int64)
    return BranchGraph(lines=lines, edge_index=edge_index, adjacency=adjacency, degrees=degrees)


def normalized_adjacency_with_self_loops(adjacency: np.ndarray) -> np.ndarray:
    adj = np.asarray(adjacency, dtype=np.float32)
    adj_hat = adj + np.eye(adj.shape[0], dtype=np.float32)
    degree = adj_hat.sum(axis=1)
    inv_sqrt = np.zeros_like(degree)
    nonzero = degree > 0.0
    inv_sqrt[nonzero] = 1.0 / np.sqrt(degree[nonzero])
    return (inv_sqrt[:, None] * adj_hat * inv_sqrt[None, :]).astype(np.float32)


def static_branch_features(case: dict, graph: BranchGraph | None = None) -> np.ndarray:
    graph = graph or build_branch_graph(case)
    num_lines = len(graph.lines)
    num_buses = max(1, int(case["num_buses"]) - 1)
    max_degree = max(1.0, float(np.max(graph.degrees)))
    branch_rates = np.asarray(case.get("branch_rate_a_original", [0.0] * num_lines), dtype=np.float32)
    finite_rates = branch_rates[np.isfinite(branch_rates) & (branch_rates > 0.0)]
    rate_scale = float(np.max(finite_rates)) if finite_rates.size else 1.0
    features = []
    for idx, (from_bus, to_bus) in enumerate(graph.lines):
        features.append([
            idx / max(1, num_lines - 1),
            from_bus / num_buses,
            to_bus / num_buses,
            graph.degrees[idx] / max_degree,
            float(branch_rates[idx]) / rate_scale if idx < len(branch_rates) and rate_scale > 0.0 else 0.0,
        ])
    return np.asarray(features, dtype=np.float32)

