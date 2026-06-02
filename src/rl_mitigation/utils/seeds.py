from __future__ import annotations

import random
import numpy as np


def set_seed(seed: int | None) -> np.random.Generator:
    if seed is None:
        seed = 0
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)
