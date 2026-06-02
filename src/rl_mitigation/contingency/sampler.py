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
    def __init__(
        self,
        case: dict,
        seed: int = 0,
        include_n_minus_1: bool = True,
        include_common_bus_n_minus_2: bool = True,
    ):
        self.case = case
        self.rng = np.random.default_rng(seed)
        self.pool = []
        if include_n_minus_1:
            self.pool.extend(n_minus_1(case))
        if include_common_bus_n_minus_2:
            self.pool.extend(common_bus_n_minus_2(case))
        if not self.pool:
            raise ValueError("ContingencySampler requires at least one contingency type")

    def sample(self, size: int = 1) -> list[tuple[int, ...]]:
        idx = self.rng.integers(0, len(self.pool), size=size)
        return [self.pool[int(i)] for i in idx]

    def sample_one(self) -> tuple[int, ...]:
        return self.sample(1)[0]

    def describe(self, contingency: tuple[int, ...] | list[int]) -> dict:
        lines = [int(x) for x in contingency]
        if len(lines) == 1:
            return {"lines": lines, "order": 1, "type": "N-1", "common_bus": None}
        common = set(self.case["lines"][lines[0]])
        for idx in lines[1:]:
            common &= set(self.case["lines"][idx])
        common_bus = min(common) if common else None
        return {
            "lines": lines,
            "order": len(lines),
            "type": "common_bus_N-2" if len(lines) == 2 and common_bus is not None else f"N-{len(lines)}",
            "common_bus": common_bus,
        }
