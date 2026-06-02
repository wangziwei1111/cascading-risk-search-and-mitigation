from __future__ import annotations

import itertools
import numpy as np


def n_minus_1(case: dict) -> list[tuple[int, ...]]:
    return [(i,) for i in range(case["num_lines"])]


def common_bus_n_minus_2(case: dict) -> list[tuple[int, int]]:
    pairs = []
    for i, j in itertools.combinations(range(case["num_lines"]), 2):
        if set(case["lines"][i]) & set(case["lines"][j]):
            pairs.append((i, j))
    return pairs


class ContingencySampler:
    def __init__(self, case: dict, seed: int = 0):
        self.case = case
        self.rng = np.random.default_rng(seed)
        self.pool = n_minus_1(case) + common_bus_n_minus_2(case)

    def sample(self, size: int = 1) -> list[tuple[int, ...]]:
        idx = self.rng.integers(0, len(self.pool), size=size)
        return [self.pool[int(i)] for i in idx]
