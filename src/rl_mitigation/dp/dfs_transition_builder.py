from __future__ import annotations

from collections import defaultdict
import pickle

import numpy as np


def state_key(line_status: np.ndarray) -> str:
    return "".join(str(int(x)) for x in line_status)


def build_transition_counts(case: dict, max_depth: int = 4) -> dict:
    n = case["num_lines"]
    dependencies = case.get("critical_dependencies", {})
    initial = np.ones(n, dtype=np.int8)
    for idx in case.get("initial_outages", []):
        initial[idx] = 0
    counts = defaultdict(lambda: defaultdict(int))

    def dfs(status: np.ndarray, depth: int):
        if depth >= max_depth:
            return
        s = state_key(status)
        for action in range(n + 1):
            nxt = status.copy()
            if action > 0 and nxt[action - 1]:
                nxt[action - 1] = 0
            tripped = []
            for outaged in np.where(nxt == 0)[0]:
                for dep in dependencies.get(int(outaged), []):
                    if nxt[dep]:
                        tripped.append(dep)
            if tripped:
                dep = tripped[0]
                nxt[dep] = 0
            sp = state_key(nxt)
            reward = -float(len(tripped)) - (0.1 if action else 0.0)
            counts[(s, action)][(sp, reward)] += 1
            if sp != s:
                dfs(nxt, depth + 1)

    dfs(initial, 0)
    return {k: dict(v) for k, v in counts.items()}


def save_transition_counts(counts: dict, path: str) -> None:
    with open(path, "wb") as f:
        pickle.dump(counts, f)
