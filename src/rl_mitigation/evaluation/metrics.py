from __future__ import annotations


def summarize_episode(total_reward: float, info: dict) -> dict:
    return {
        "episode_return": total_reward,
        "negative_return": -total_reward,
        "initial_outages": ",".join(str(x) for x in info.get("initial_outages", [])),
        "initial_outage_type": info.get("initial_outage_type", ""),
        "initial_outage_order": info.get("initial_outage_order", 0),
        "chronic_index": info.get("chronic_index", -1),
        "load_scale": info.get("load_scale", 1.0),
        "gen_scale": info.get("gen_scale", 1.0),
        "num_generations": info.get("num_generations", 0),
        "num_line_outages": info.get("num_line_outages", 0),
        "load_shed_MW": info.get("load_shed_MW", 0.0),
        "load_shed_ratio": info.get("load_shed_ratio", 0.0),
        "num_proactive_actions": info.get("num_proactive_actions", 0),
        "num_invalid_actions": info.get("num_invalid_actions", 0),
        "pf_failed": info.get("pf_failed", False),
    }
