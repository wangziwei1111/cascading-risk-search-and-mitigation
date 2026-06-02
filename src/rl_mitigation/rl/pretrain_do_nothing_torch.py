from __future__ import annotations

from pathlib import Path

import numpy as np

from .torch_networks import TorchActorCritic, torch


def collect_random_states(env, n_states: int = 1024, seed: int = 0):
    rng = np.random.default_rng(seed)
    obs, _ = env.reset(seed=seed)
    states = []
    for _ in range(n_states):
        states.append(obs)
        action = int(rng.integers(0, env.action_space_n))
        obs, _, done, _, _ = env.step(action)
        if done:
            obs, _ = env.reset(seed=int(rng.integers(0, 1_000_000)))
    return np.asarray(states, dtype=np.float32), np.zeros(len(states), dtype=np.int64)


def pretrain_do_nothing_actor(
    env,
    output_dir: str,
    n_states: int = 1024,
    epochs: int = 10,
    learning_rate: float = 1e-3,
    entropy_coef: float = 0.001,
    seed: int = 0,
):
    torch.manual_seed(seed)
    states, actions = collect_random_states(env, n_states=n_states, seed=seed)
    model = TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    optimizer = torch.optim.Adam(model.actor.parameters(), lr=learning_rate)
    x = torch.tensor(states, dtype=torch.float32)
    y = torch.tensor(actions, dtype=torch.long)
    for _ in range(epochs):
        logits = model.actor(x)
        ce = torch.nn.functional.cross_entropy(logits, y)
        probs = torch.softmax(logits, dim=-1)
        entropy = -(probs * torch.log(probs + 1e-8)).sum(dim=-1).mean()
        loss = ce - entropy_coef * entropy
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / "states_actions.npz", states=states, actions=actions)
    torch.save({"actor_state_dict": model.actor.state_dict(), "obs_dim": model.obs_dim, "action_dim": model.action_dim}, out / "policy_pretrained_torch.pt")
    return model, states, actions
