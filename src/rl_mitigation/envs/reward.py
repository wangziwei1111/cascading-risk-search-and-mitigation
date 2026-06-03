from __future__ import annotations

import math


def cascade_reward_terms(
    *,
    terminal: bool,
    pf_failed: bool,
    alpha: float,
    action: int,
    num_new_outages: int,
    previous_load: float,
    current_load: float,
    generation: int,
) -> dict[str, float]:
    if generation == 0:
        return {
            "nonterminal_penalty": 0.0,
            "pf_failure_penalty": 0.0,
            "proactive_action_penalty": 0.0,
            "new_outage_penalty": 0.0,
            "load_shed_penalty": 0.0,
        }
    load_shed_penalty = 0.0
    if previous_load > 0:
        load_shed_penalty = -max(0.0, previous_load - current_load) / previous_load
    return {
        "nonterminal_penalty": 0.0 if terminal else -1.0,
        "pf_failure_penalty": -100.0 if pf_failed else 0.0,
        "proactive_action_penalty": -float(alpha) if action != 0 else 0.0,
        "new_outage_penalty": -100.0 * (1.0 - math.exp(-0.01 * max(0, num_new_outages))),
        "load_shed_penalty": float(load_shed_penalty),
    }


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
    return float(sum(cascade_reward_terms(
        terminal=terminal,
        pf_failed=pf_failed,
        alpha=alpha,
        action=action,
        num_new_outages=num_new_outages,
        previous_load=previous_load,
        current_load=current_load,
        generation=generation,
    ).values()))
