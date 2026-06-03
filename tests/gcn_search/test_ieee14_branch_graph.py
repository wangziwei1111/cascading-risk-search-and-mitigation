import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from gcn_search.ieee14.branch_graph import build_branch_graph, normalized_adjacency_with_self_loops, static_branch_features
from rl_mitigation.cases import make_ieee14_case


def test_ieee14_branch_graph_uses_case14_lines():
    case = make_ieee14_case()
    graph = build_branch_graph(case)
    assert len(graph.lines) == 20
    assert graph.adjacency.shape == (20, 20)
    assert np.allclose(graph.adjacency, graph.adjacency.T)
    assert np.all(np.diag(graph.adjacency) == 0.0)
    assert graph.edge_index.shape[0] == 2
    assert int(graph.degrees[0]) > 0


def test_static_features_and_normalized_adjacency_shapes():
    case = make_ieee14_case()
    graph = build_branch_graph(case)
    features = static_branch_features(case, graph)
    norm_adj = normalized_adjacency_with_self_loops(graph.adjacency)
    assert features.shape == (20, 5)
    assert norm_adj.shape == (20, 20)
    assert np.all(norm_adj.diagonal() > 0.0)

