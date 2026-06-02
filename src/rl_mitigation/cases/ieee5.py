"""Small 5-bus mechanism-reproduction case for the paper's DP example."""

from __future__ import annotations


def make_ieee5_case() -> dict:
    lines = [
        (0, 1), (0, 2), (1, 2), (1, 3),
        (2, 3), (2, 4), (3, 4), (0, 4),
    ]
    return {
        "name": "ieee5_mechanism",
        "num_buses": 5,
        "num_lines": len(lines),
        "lines": lines,
        "generators": [{"bus": 0, "pmax": 110.0}, {"bus": 1, "pmax": 80.0}],
        "loads": [{"bus": 2, "p": 45.0}, {"bus": 3, "p": 55.0}, {"bus": 4, "p": 35.0}],
        "base_flows": [0.48, 0.63, 0.35, 0.82, 0.92, 0.74, 0.58, 0.68],
        "line_limits": [1.0] * len(lines),
        "initial_outages": [0, 1],
        "critical_dependencies": {0: [3, 4], 1: [5], 3: [6], 4: [7]},
    }
