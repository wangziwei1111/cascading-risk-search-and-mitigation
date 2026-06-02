from __future__ import annotations

from .action_value import scan_scenario_actions


def choose_best_initial_action(env, scenario: dict) -> tuple[int, dict]:
    rows = scan_scenario_actions(env, scenario)
    valid_rows = [row for row in rows if row.get("is_valid_action")]
    best = min(valid_rows or rows, key=lambda row: float(row["negative_return"]))
    return int(best["action"]), best
