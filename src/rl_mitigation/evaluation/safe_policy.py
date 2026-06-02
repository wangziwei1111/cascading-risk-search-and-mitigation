from __future__ import annotations

from pathlib import Path

import numpy as np

from ..rl.torch_networks import TorchActorCritic, torch


def load_actor_policy(path: str | Path) -> TorchActorCritic:
    data = torch.load(path, map_location="cpu")
    model = TorchActorCritic(data["obs_dim"], data["action_dim"])
    if "model_state_dict" in data:
        model.load_state_dict(data["model_state_dict"])
    else:
        model.actor.load_state_dict(data["actor_state_dict"], strict=False)
    return model


def action_probabilities(model, obs, action_mask) -> np.ndarray:
    with torch.no_grad():
        logits = model.masked_logits(
            torch.tensor(obs, dtype=torch.float32).unsqueeze(0),
            torch.tensor(action_mask, dtype=torch.bool).unsqueeze(0),
        )[0]
        return torch.softmax(logits, dim=-1).cpu().numpy()


def safe_gate_action(probs: np.ndarray, active_prob_threshold: float = 0.35, margin_threshold: float = 0.05) -> int:
    if len(probs) <= 1:
        return 0
    nonzero = probs.copy()
    nonzero[0] = -1.0
    action = int(np.argmax(nonzero))
    p_active = float(probs[action])
    p_do_nothing = float(probs[0])
    if p_active >= active_prob_threshold and (p_active - p_do_nothing) >= margin_threshold:
        return action
    return 0


def run_safe_policy(env, scenarios: list[dict], model, policy_name: str, active_prob_threshold: float, margin_threshold: float, episodes: int | None = None) -> list[dict]:
    from .metrics import summarize_episode

    rows = []
    for ep, scenario in enumerate(scenarios[: episodes or len(scenarios)]):
        obs, info = env.reset(seed=int(scenario["seed"]), options={"scenario": scenario})
        total = 0.0
        done = False
        last_info = info
        while not done:
            probs = action_probabilities(model, obs, last_info["action_mask"])
            action = safe_gate_action(probs, active_prob_threshold, margin_threshold)
            obs, reward, done, _, last_info = env.step(action)
            total += float(reward)
        row = summarize_episode(total, last_info)
        row["episode"] = ep
        row["scenario_id"] = scenario.get("scenario_id", ep)
        row["policy"] = policy_name
        row["active_prob_threshold"] = active_prob_threshold
        row["margin_threshold"] = margin_threshold
        rows.append(row)
    return rows


def run_actor_policy(env, scenarios: list[dict], model, policy_name: str, eval_mode: str = "deterministic", episodes: int | None = None) -> list[dict]:
    from .metrics import summarize_episode

    rows = []
    for ep, scenario in enumerate(scenarios[: episodes or len(scenarios)]):
        obs, info = env.reset(seed=int(scenario["seed"]), options={"scenario": scenario})
        total = 0.0
        done = False
        last_info = info
        while not done:
            probs = action_probabilities(model, obs, last_info["action_mask"])
            if eval_mode == "stochastic":
                action = int(np.random.default_rng(int(scenario["seed"]) + ep).choice(np.arange(len(probs)), p=probs / probs.sum()))
            else:
                action = int(np.argmax(probs))
            obs, reward, done, _, last_info = env.step(action)
            total += float(reward)
        row = summarize_episode(total, last_info)
        row["episode"] = ep
        row["scenario_id"] = scenario.get("scenario_id", ep)
        row["policy"] = policy_name
        rows.append(row)
    return rows
