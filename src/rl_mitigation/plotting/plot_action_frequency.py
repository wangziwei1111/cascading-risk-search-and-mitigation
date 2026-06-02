from __future__ import annotations


def action_frequency(actions):
    counts = {}
    for action in actions:
        counts[int(action)] = counts.get(int(action), 0) + 1
    return counts
