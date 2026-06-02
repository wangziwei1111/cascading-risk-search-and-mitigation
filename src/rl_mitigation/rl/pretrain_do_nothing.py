from __future__ import annotations

import numpy as np

from .networks import ActorCritic


def collect_random_states(env, n_states: int = 512, seed: int = 0):
    rng = np.random.default_rng(seed)
    states = []
    obs, _ = env.reset(seed=seed)
    for _ in range(n_states):
        states.append(obs)
        action = int(rng.integers(0, env.action_space_n))
        obs, _, done, _, _ = env.step(action)
        if done:
            obs, _ = env.reset()
    return np.asarray(states, dtype=np.float32), np.zeros(len(states), dtype=np.int64)


def pretrain_policy(env, n_states: int = 512, epochs: int = 5, entropy_coef: float = 0.001, seed: int = 0):
    states, actions = collect_random_states(env, n_states=n_states, seed=seed)
    model = ActorCritic(states.shape[1], env.action_space_n, seed=seed)
    lr = 0.05
    for _ in range(epochs):
        for x in states:
            probs = model.action_probs(x, np.ones(env.action_space_n, dtype=bool))
            grad = probs
            grad[0] -= 1.0
            model.weights -= lr * np.outer(x, grad)
            model.bias -= lr * grad
            model.bias += entropy_coef * 0.001
    return model, states, actions
