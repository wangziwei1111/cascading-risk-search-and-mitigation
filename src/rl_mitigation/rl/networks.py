from __future__ import annotations

import pickle

import numpy as np


class ActorCritic:
    """Small numpy actor used for smoke training when torch is unavailable."""

    def __init__(self, obs_dim: int, action_dim: int, seed: int = 0, policy_hidden=None, value_hidden=None):
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        rng = np.random.default_rng(seed)
        self.weights = rng.normal(0.0, 0.01, size=(self.obs_dim, self.action_dim)).astype(np.float32)
        self.bias = np.zeros(self.action_dim, dtype=np.float32)

    def logits(self, obs: np.ndarray) -> np.ndarray:
        x = np.asarray(obs, dtype=np.float32)
        return x @ self.weights + self.bias

    def masked_logits(self, obs: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        logits = self.logits(obs)
        if mask is not None:
            logits = np.where(mask.astype(bool), logits, -1e9)
        return logits

    def action_probs(self, obs: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
        logits = self.masked_logits(obs, mask)
        logits = logits - np.max(logits)
        exp = np.exp(logits)
        return exp / np.sum(exp)

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump({"obs_dim": self.obs_dim, "action_dim": self.action_dim, "weights": self.weights, "bias": self.bias}, f)

    @classmethod
    def load(cls, path: str):
        with open(path, "rb") as f:
            data = pickle.load(f)
        model = cls(data["obs_dim"], data["action_dim"])
        model.weights = data["weights"]
        model.bias = data["bias"]
        return model
