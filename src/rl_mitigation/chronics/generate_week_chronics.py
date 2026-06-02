from __future__ import annotations

import numpy as np


def generate_week_chronics(num_steps: int = 7 * 24 * 12, seed: int = 0) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    t = np.arange(num_steps)
    daily = 1.0 + 0.18 * np.sin(2 * np.pi * t / (24 * 12) - 0.7)
    weekly = 1.0 + 0.08 * np.sin(2 * np.pi * t / num_steps)
    wind = 0.35 + 0.18 * np.sin(2 * np.pi * t / (18 * 12)) + 0.05 * rng.normal(size=num_steps)
    wind = np.clip(wind, 0.05, 0.85)
    load_scale = np.clip(daily * weekly + 0.02 * rng.normal(size=num_steps), 0.65, 1.35)
    gen_scale = np.clip(1.0 + 0.08 * rng.normal(size=num_steps), 0.75, 1.25)
    return {"load_scale": load_scale.astype(np.float32), "gen_scale": gen_scale.astype(np.float32), "wind": wind.astype(np.float32)}
