from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .networks import ActorCritic


def train_ppo_smoke(env, steps: int = 2048, seed: int = 0, log_path: str | None = None, model: ActorCritic | None = None):
    rng = np.random.default_rng(seed)
    obs, info = env.reset(seed=seed)
    model = model or ActorCritic(len(obs), env.action_space_n, seed=seed)
    rows = []
    episode_return = 0.0
    for step in range(int(steps)):
        mask = info.get("action_mask", np.ones(env.action_space_n, dtype=bool))
        probs = model.action_probs(obs, mask)
        action = int(rng.choice(env.action_space_n, p=probs))
        next_obs, reward, done, _, info = env.step(action)
        grad = probs.copy()
        grad[action] -= 1.0
        model.weights += 0.001 * float(reward) * np.outer(obs, -grad)
        model.bias += 0.001 * float(reward) * (-grad)
        episode_return += float(reward)
        if done:
            rows.append({"step": step + 1, "episode_return": episode_return, "negative_return": -episode_return})
            obs, info = env.reset(seed=int(rng.integers(0, 1_000_000)))
            episode_return = 0.0
        else:
            obs = next_obs
    if log_path:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["step", "episode_return", "negative_return"])
            writer.writeheader()
            writer.writerows(rows)
    return model, rows
