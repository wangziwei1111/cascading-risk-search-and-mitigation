from __future__ import annotations

import numpy as np


def survival_curve(values):
    xs = np.sort(np.asarray(values, dtype=float))
    if len(xs) == 0:
        return xs, xs
    ys = 1.0 - np.arange(len(xs)) / len(xs)
    return xs, ys


def survival_by_policy(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(row["policy"], []).append(float(row["negative_return"]))
    out = []
    for policy, values in grouped.items():
        xs, ys = survival_curve(values)
        for x, y in zip(xs, ys):
            out.append({
                "policy": policy,
                "negative_return": float(x),
                "survival_probability": float(y),
            })
    return out
