from __future__ import annotations

from rl_mitigation.rl.torch_utils import import_torch


torch = import_torch()
from torch import nn


class BranchGCN(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 32):
        super().__init__()
        self.input = nn.Linear(input_dim, hidden_dim)
        self.hidden = nn.Linear(hidden_dim, hidden_dim)
        self.output = nn.Linear(hidden_dim, 1)

    def forward(self, features, normalized_adjacency):
        adj = normalized_adjacency.to(features.device)
        x = torch.einsum("ij,bjf->bif", adj, features)
        x = torch.relu(self.input(x))
        x = torch.einsum("ij,bjf->bif", adj, x)
        x = torch.relu(self.hidden(x))
        x = torch.einsum("ij,bjf->bif", adj, x)
        return self.output(x).squeeze(-1)

