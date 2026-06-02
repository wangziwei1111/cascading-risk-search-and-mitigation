from __future__ import annotations

import json

from .metrics import summarize_episode


def run_episode_with_first_action(env, scenario: dict, action: int) -> dict:
    _, info = env.reset(seed=int(scenario["seed"]), options={"scenario": scenario})
    mask = info.get("action_mask")
    is_valid = bool(mask[action]) if mask is not None and action < len(mask) else False
    total = 0.0
    done = False
    first = True
    last_info = info
    while not done:
        chosen = action if first else 0
        _, reward, done, _, last_info = env.step(chosen)
        total += float(reward)
        first = False
    row = summarize_episode(total, last_info)
    row.update({
        "scenario_id": scenario["scenario_id"],
        "action": action,
        "action_type": "do_nothing" if action == 0 else "open_line",
        "action_line": "" if action == 0 else action - 1,
        "is_valid_action": is_valid,
        "cascade_trace_json": json.dumps(last_info.get("cascade_trace", []), ensure_ascii=False),
    })
    return row


def scan_scenario_actions(env, scenario: dict) -> list[dict]:
    return [run_episode_with_first_action(env, scenario, action) for action in range(env.action_space_n)]
