from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .metrics import summarize_episode
from ..rl.torch_networks import torch


def run_policy(
    env,
    episodes: int = 10,
    model=None,
    with_agent: bool = False,
    seed: int = 0,
    scenarios: list[dict] | None = None,
    eval_mode: str = "deterministic",
):
    rows = []
    rng = np.random.default_rng(seed)
    scenario_list = scenarios if scenarios is not None else [None] * episodes
    for ep, scenario in enumerate(scenario_list[:episodes]):
        reset_seed = int(scenario.get("seed", rng.integers(0, 1_000_000))) if scenario else int(rng.integers(0, 1_000_000))
        obs, info = env.reset(seed=reset_seed, options={"scenario": scenario} if scenario else None)
        total = 0.0
        done = False
        last_info = info
        while not done:
            if with_agent and model is not None:
                mask = last_info.get("action_mask", np.ones(env.action_space_n, dtype=bool))
                if hasattr(model, "act"):
                    obs_t = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                    mask_t = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
                    with torch.no_grad():
                        action_t, _, _, _ = model.act(obs_t, mask_t, deterministic=(eval_mode == "deterministic"))
                    action = int(action_t.item())
                else:
                    action = int(np.argmax(model.masked_logits(obs, mask)))
            else:
                action = 0
            obs, reward, done, _, last_info = env.step(action)
            total += float(reward)
        row = summarize_episode(total, last_info)
        row["episode"] = ep
        row["scenario_id"] = scenario.get("scenario_id", ep) if scenario else ep
        row["policy"] = "agent" if with_agent else "do_nothing"
        rows.append(row)
    return rows


def save_eval_csv(rows: list[dict], path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({k for row in rows for k in row})
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
