from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def generate_eval_scenarios(env, episodes: int, seed: int = 0) -> list[dict]:
    rng = np.random.default_rng(seed)
    load = env.chronics.get("load_scale", np.ones(1))
    gen = env.chronics.get("gen_scale", np.ones(len(load)))
    scenarios = []
    for scenario_id in range(episodes):
        chronic_index = int(rng.integers(0, len(load)))
        contingency = env.contingency_sampler.sample_one()
        desc = env.contingency_sampler.describe(contingency)
        scenarios.append({
            "scenario_id": scenario_id,
            "seed": int(rng.integers(0, 1_000_000)),
            "chronic_index": chronic_index,
            "load_scale": float(load[chronic_index]),
            "gen_scale": float(gen[chronic_index]),
            "initial_outages": desc["lines"],
            "initial_outage_type": desc["type"],
            "initial_outage_order": desc["order"],
            "initial_outage_mode": "sampled",
        })
    return scenarios


def save_scenarios(scenarios: list[dict], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=2)


def load_scenarios(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
