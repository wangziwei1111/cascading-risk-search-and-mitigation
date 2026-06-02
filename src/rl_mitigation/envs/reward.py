from __future__ import annotations

import math


def cascade_reward(
    *,
    terminal: bool,
    pf_failed: bool,
    alpha: float,
    action: int,
    num_new_outages: int,
    previous_load: float,
    current_load: float,
    generation: int,
) -> float:
    if generation == 0:
        return 0.0
    reward = 0.0 if terminal else -1.0
    if pf_failed:
        reward -= 100.0
    if action != 0:
        reward -= alpha
    reward -= 100.0 * (1.0 - math.exp(-0.01 * max(0, num_new_outages)))
    if previous_load > 0:
        reward -= max(0.0, previous_load - current_load) / previous_load
    return float(reward)
