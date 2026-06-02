from __future__ import annotations


def share_bus(line_a: tuple[int, int], line_b: tuple[int, int]) -> bool:
    return bool(set(line_a) & set(line_b))
