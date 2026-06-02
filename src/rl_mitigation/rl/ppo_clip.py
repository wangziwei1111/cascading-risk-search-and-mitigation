from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .rollout_buffer import RolloutBuffer
from .torch_networks import TorchActorCritic, torch


def load_pretrained_actor(model: TorchActorCritic, path: str) -> bool:
    checkpoint = Path(path)
    if not checkpoint.exists():
        return False
    data = torch.load(checkpoint, map_location="cpu")
    state = data.get("actor_state_dict", data)
    model.actor.load_state_dict(state, strict=False)
    return True


def save_checkpoint(model: TorchActorCritic, path: str, step: int, best_score: float | None = None):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "model_state_dict": model.state_dict(),
        "obs_dim": model.obs_dim,
        "action_dim": model.action_dim,
        "step": step,
        "best_score": best_score,
    }, path)


def load_checkpoint(path: str) -> TorchActorCritic:
    data = torch.load(path, map_location="cpu")
    model = TorchActorCritic(data["obs_dim"], data["action_dim"])
    model.load_state_dict(data["model_state_dict"])
    return model


def train_ppo_clip(
    env,
    total_steps: int = 60000,
    learning_rate: float = 1e-3,
    gamma: float = 1.0,
    gae_lambda: float = 0.95,
    entropy_coef: float = 0.001,
    clip_range: float = 0.2,
    value_clip: float = 0.2,
    n_steps: int = 1024,
    batch_size: int = 256,
    epochs: int = 10,
    policy_hidden_layers: list[int] | None = None,
    value_hidden_layers: list[int] | None = None,
    pretrained_actor_path: str | None = None,
    log_path: str | None = None,
    checkpoint_dir: str | None = None,
    seed: int = 0,
):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = TorchActorCritic(
        env.observation_space_shape[0],
        env.action_space_n,
        policy_hidden=policy_hidden_layers or [64, 64],
        value_hidden=value_hidden_layers or [64, 8],
    )
    if pretrained_actor_path:
        load_pretrained_actor(model, pretrained_actor_path)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    buffer = RolloutBuffer()
    log_rows = []
    obs, info = env.reset(seed=seed)
    last_done = False
    episode = 0
    best_return = None
    step = 0
    while step < total_steps:
        buffer.clear()
        sampled_invalid_action_count = 0
        valid_action_counts = []
        for _ in range(min(n_steps, total_steps - step)):
            env_mask = info.get("action_mask", np.ones(env.action_space_n, dtype=bool))
            mask = env_mask if getattr(env, "use_action_mask", False) else np.ones(env.action_space_n, dtype=bool)
            mask_arr = np.asarray(mask, dtype=bool)
            valid_action_counts.append(int(mask_arr.sum()))
            obs_t = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
            mask_t = torch.tensor(mask_arr, dtype=torch.bool).unsqueeze(0)
            with torch.no_grad():
                action_t, log_prob_t, _, value_t = model.act(obs_t, mask_t)
            action = int(action_t.item())
            if not mask_arr[action]:
                sampled_invalid_action_count += 1
            next_obs, reward, done, _, next_info = env.step(action)
            buffer.add(obs, action, float(log_prob_t.item()), reward, done, float(value_t.item()), mask_arr)
            step += 1
            obs, info = next_obs, next_info
            last_done = done
            if done:
                episode += 1
                log_rows.append(_episode_log_row(step, episode, info))
                ep_return = float(info.get("episode_return", 0.0))
                if best_return is None or ep_return > best_return:
                    best_return = ep_return
                    if checkpoint_dir:
                        save_checkpoint(model, str(Path(checkpoint_dir) / "best.pt"), step, best_return)
                obs, info = env.reset(seed=int(rng.integers(0, 1_000_000)))
                last_done = False
            if step >= total_steps:
                break
        if last_done:
            last_value = 0.0
        else:
            with torch.no_grad():
                last_value = float(model.value(torch.tensor(obs, dtype=torch.float32).unsqueeze(0)).item())
        returns, advantages = buffer.compute_returns_advantages(
            gamma=gamma,
            gae_lambda=gae_lambda,
            last_value=last_value,
            last_done=last_done,
        )
        metrics = _update(model, optimizer, buffer, returns, advantages, clip_range, value_clip, entropy_coef, batch_size, epochs)
        metrics["mask_enabled"] = bool(getattr(env, "use_action_mask", False))
        metrics["mean_valid_action_count"] = float(np.mean(valid_action_counts)) if valid_action_counts else 0.0
        metrics["sampled_invalid_action_count"] = int(sampled_invalid_action_count)
        if log_rows:
            log_rows[-1].update(metrics)
        if checkpoint_dir:
            save_checkpoint(model, str(Path(checkpoint_dir) / "latest.pt"), step, best_return)
    if log_path:
        _write_logs(log_rows, log_path)
    return model, log_rows


def _update(model, optimizer, buffer, returns, advantages, clip_range, value_clip, entropy_coef, batch_size, epochs):
    obs = torch.tensor(np.asarray(buffer.obs), dtype=torch.float32)
    actions = torch.tensor(buffer.actions, dtype=torch.long)
    old_log_probs = torch.tensor(buffer.log_probs, dtype=torch.float32)
    old_values = torch.tensor(buffer.values, dtype=torch.float32)
    masks = torch.tensor(np.asarray(buffer.masks), dtype=torch.bool)
    returns_t = torch.tensor(returns, dtype=torch.float32)
    advantages_t = torch.tensor(advantages, dtype=torch.float32)
    n = len(actions)
    metrics = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "approx_kl": 0.0, "clip_fraction": 0.0}
    if n == 0:
        return metrics
    for _ in range(epochs):
        indices = torch.randperm(n)
        for start in range(0, n, batch_size):
            idx = indices[start:start + batch_size]
            logits = model.masked_logits(obs[idx], masks[idx])
            dist = torch.distributions.Categorical(logits=logits)
            new_log_probs = dist.log_prob(actions[idx])
            entropy = dist.entropy().mean()
            ratio = torch.exp(new_log_probs - old_log_probs[idx])
            unclipped = ratio * advantages_t[idx]
            clipped = torch.clamp(ratio, 1.0 - clip_range, 1.0 + clip_range) * advantages_t[idx]
            policy_loss = -torch.min(unclipped, clipped).mean()
            values = model.value(obs[idx])
            values_clipped = old_values[idx] + torch.clamp(values - old_values[idx], -value_clip, value_clip)
            value_loss = 0.5 * torch.max((values - returns_t[idx]).pow(2), (values_clipped - returns_t[idx]).pow(2)).mean()
            loss = policy_loss + value_loss - entropy_coef * entropy
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
            optimizer.step()
            with torch.no_grad():
                approx_kl = (old_log_probs[idx] - new_log_probs).mean().abs()
                clip_fraction = ((ratio - 1.0).abs() > clip_range).float().mean()
            metrics = {
                "policy_loss": float(policy_loss.item()),
                "value_loss": float(value_loss.item()),
                "entropy": float(entropy.item()),
                "approx_kl": float(approx_kl.item()),
                "clip_fraction": float(clip_fraction.item()),
            }
    return metrics


def _episode_log_row(step: int, episode: int, info: dict) -> dict:
    return {
        "step": step,
        "episode": episode,
        "episode_return": info.get("episode_return", 0.0),
        "negative_return": info.get("negative_return", 0.0),
        "initial_outages": ",".join(str(x) for x in info.get("initial_outages", [])),
        "initial_outage_type": info.get("initial_outage_type", ""),
        "initial_outage_order": info.get("initial_outage_order", 0),
        "chronic_index": info.get("chronic_index", -1),
        "mask_enabled": info.get("action_mask") is not None,
        "mean_valid_action_count": 0.0,
        "sampled_invalid_action_count": 0,
        "policy_loss": 0.0,
        "value_loss": 0.0,
        "entropy": 0.0,
        "approx_kl": 0.0,
        "clip_fraction": 0.0,
        "num_generations": info.get("num_generations", 0),
        "num_line_outages": info.get("num_line_outages", 0),
        "load_shed_MW": info.get("load_shed_MW", 0.0),
        "num_proactive_actions": info.get("num_proactive_actions", 0),
        "num_invalid_actions": info.get("num_invalid_actions", 0),
    }


def _write_logs(rows: list[dict], path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "step", "episode", "episode_return", "negative_return", "initial_outages",
        "initial_outage_type", "initial_outage_order", "chronic_index", "mask_enabled",
        "mean_valid_action_count", "sampled_invalid_action_count", "policy_loss", "value_loss",
        "entropy", "approx_kl", "clip_fraction", "num_generations", "num_line_outages",
        "load_shed_MW", "num_proactive_actions", "num_invalid_actions",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
