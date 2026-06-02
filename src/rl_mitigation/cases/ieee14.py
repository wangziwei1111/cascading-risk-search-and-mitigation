"""IEEE14-style case metadata.

This uses the canonical 14-bus/20-branch topology shape for reproduction
plumbing. Exact paper chronics are not public in this workspace.
"""

from __future__ import annotations


def make_ieee14_case() -> dict:
    lines = [
        (0, 1), (0, 4), (1, 2), (1, 3), (1, 4),
        (2, 3), (3, 4), (3, 6), (3, 8), (4, 5),
        (5, 10), (5, 11), (5, 12), (6, 7), (6, 8),
        (8, 9), (8, 13), (9, 10), (11, 12), (12, 13),
    ]
    return {
        "name": "ieee14_surrogate",
        "num_buses": 14,
        "num_lines": len(lines),
        "lines": lines,
        "generators": [
            {"bus": 0, "pmax": 232.0}, {"bus": 1, "pmax": 40.0},
            {"bus": 2, "pmax": 30.0}, {"bus": 5, "pmax": 25.0},
            {"bus": 7, "pmax": 20.0}, {"bus": 10, "pmax": 20.0},
        ],
        "loads": [{"bus": b, "p": p} for b, p in zip(
            [1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13],
            [21.7, 94.2, 47.8, 7.6, 11.2, 29.5, 9.0, 3.5, 6.1, 13.5, 14.9],
        )],
        "base_flows": [
            0.72, 0.48, 0.66, 0.59, 0.52, 0.46, 0.77, 0.88, 0.70, 0.62,
            0.43, 0.39, 0.35, 0.56, 0.61, 0.54, 0.58, 0.47, 0.41, 0.45,
        ],
        "line_limits": [1.0] * len(lines),
        "initial_outages": [0],
    }
