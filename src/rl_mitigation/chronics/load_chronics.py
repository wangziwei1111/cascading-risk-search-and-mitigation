from __future__ import annotations

from .generate_week_chronics import generate_week_chronics


def load_or_generate_week_chronics(seed: int = 0):
    return generate_week_chronics(seed=seed)
