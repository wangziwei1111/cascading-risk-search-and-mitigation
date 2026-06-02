from __future__ import annotations

from .torch_utils import import_torch

torch = import_torch()
from torch import nn


def mlp(input_dim: int, hidden: list[int], output_dim: int) -> nn.Sequential:
    layers = []
    last = input_dim
    for width in hidden:
        layers.append(nn.Linear(last, width))
        layers.append(nn.Tanh())
        last = width
    layers.append(nn.Linear(last, output_dim))
    return nn.Sequential(*layers)


class TorchActorCritic(nn.Module):
    def __init__(self, obs_dim: int, action_dim: int, policy_hidden=None, value_hidden=None):
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.actor = mlp(obs_dim, policy_hidden or [64, 64], action_dim)
        self.critic = mlp(obs_dim, value_hidden or [64, 8], 1)

    def masked_logits(self, obs, action_mask=None):
        logits = self.actor(obs)
        if action_mask is not None:
            logits = logits.masked_fill(~action_mask.bool(), -1e9)
        return logits

    def value(self, obs):
        return self.critic(obs).squeeze(-1)

    def act(self, obs, action_mask=None, deterministic: bool = False):
        logits = self.masked_logits(obs, action_mask)
        dist = torch.distributions.Categorical(logits=logits)
        action = torch.argmax(logits, dim=-1) if deterministic else dist.sample()
        return action, dist.log_prob(action), dist.entropy(), self.value(obs)
