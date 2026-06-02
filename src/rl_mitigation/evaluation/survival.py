from __future__ import annotations

import numpy as np


def survival_curve(values):
    xs = np.sort(np.asarray(values, dtype=float))
    if len(xs) == 0:
        return xs, xs
    ys = 1.0 - np.arange(len(xs)) / len(xs)
    return xs, ys
