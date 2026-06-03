from __future__ import annotations

import json
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .pretrain_do_nothing_torch import collect_random_states
from .torch_networks import TorchActorCritic, torch


def pretrain_paper_do_nothing_actor(
    env,
    output_dir: str,
    n_states: int = 2048,
    epochs: int = 5,
    learning_rate: float = 1e-3,
    entropy_coef: float = 0.01,
    seed: int = 0,
    target_do_nothing_prob: float = 0.60,
    target_do_nothing_prob_min: float = 0.35,
    target_do_nothing_prob_max: float = 0.80,
    early_stop_when_target_reached: bool = True,
    policy_hidden_layers: list[int] | None = None,
    value_hidden_layers: list[int] | None = None,
):
    torch.manual_seed(seed)
    states, actions = collect_random_states(env, n_states=n_states, seed=seed)
    model = TorchActorCritic(
        env.observation_space_shape[0],
        env.action_space_n,
        policy_hidden=policy_hidden_layers or [64, 64],
        value_hidden=value_hidden_layers or [64, 8],
    )
    x = torch.tensor(states, dtype=torch.float32)
    y = torch.tensor(actions, dtype=torch.long)
    before = _prob_stats(model, x)
    optimizer = torch.optim.Adam(model.actor.parameters(), lr=learning_rate)
    history = []
    for epoch in range(1, epochs + 1):
        logits = model.actor(x)
        ce = torch.nn.functional.cross_entropy(logits, y)
        probs = torch.softmax(logits, dim=-1)
        entropy = -(probs * torch.log(probs + 1e-8)).sum(dim=-1).mean()
        over_max_penalty = torch.relu(probs[:, 0].mean() - target_do_nothing_prob_max).pow(2)
        loss = ce + 5.0 * over_max_penalty - entropy_coef * entropy
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        stats = _prob_stats(model, x)
        history.append({
            "epoch": epoch,
            "loss": float(loss.item()),
            "cross_entropy": float(ce.item()),
            "entropy": float(entropy.item()),
            **stats,
        })
        if early_stop_when_target_reached and target_do_nothing_prob_min <= stats["mean_prob_do_nothing"] <= target_do_nothing_prob_max:
            break
    after = _prob_stats(model, x)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / "states_actions.npz", states=states, actions=actions)
    torch.save({"actor_state_dict": model.actor.state_dict(), "obs_dim": model.obs_dim, "action_dim": model.action_dim}, out / "policy_pretrained_torch.pt")
    random_prob = 1.0 / max(1, env.action_space_n)
    warning = None
    if after["mean_prob_do_nothing"] < target_do_nothing_prob_min:
        warning = "do-nothing initialization too weak"
    elif after["mean_prob_do_nothing"] > target_do_nothing_prob_max:
        warning = "do-nothing initialization may be too strong"
    diagnostics = {
        "before": before,
        "after": after,
        **after,
        "p10_prob_do_nothing": after["p10_prob_do_nothing"],
        "p90_prob_do_nothing": after["p90_prob_do_nothing"],
        "random_action_probability": float(random_prob),
        "target_do_nothing_prob": float(target_do_nothing_prob),
        "target_do_nothing_prob_min": float(target_do_nothing_prob_min),
        "target_do_nothing_prob_max": float(target_do_nothing_prob_max),
        "target_reached": bool(target_do_nothing_prob_min <= after["mean_prob_do_nothing"] <= target_do_nothing_prob_max),
        "warning": warning,
        "epochs_run": len(history),
    }
    (out / "pretrain_diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    _write_history(history, out / "pretrain_history.csv")
    _plot_pretrain(before, after, out / "fig_do_nothing_pretrain_action_probability.png")
    return model, diagnostics


def _prob_stats(model, x) -> dict:
    with torch.no_grad():
        probs = torch.softmax(model.actor(x), dim=-1)
        entropy = -(probs * torch.log(probs + 1e-8)).sum(dim=-1)
    return {
        "mean_prob_do_nothing": float(probs[:, 0].mean().item()),
        "median_prob_do_nothing": float(probs[:, 0].median().item()),
        "p10_prob_do_nothing": float(torch.quantile(probs[:, 0], 0.10).item()),
        "p90_prob_do_nothing": float(torch.quantile(probs[:, 0], 0.90).item()),
        "mean_entropy": float(entropy.mean().item()),
        "mean_max_nonzero_prob": float(probs[:, 1:].max(dim=1).values.mean().item()),
    }


def _write_history(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _plot_pretrain(before: dict, after: dict, out_png: Path) -> None:
    labels = ["mean P(0)", "median P(0)", "entropy", "max nonzero P"]
    keys = ["mean_prob_do_nothing", "median_prob_do_nothing", "mean_entropy", "mean_max_nonzero_prob"]
    x = np.arange(len(keys))
    plt.figure(figsize=(6.5, 4), facecolor="white")
    plt.bar(x - 0.18, [before[k] for k in keys], width=0.36, label="before")
    plt.bar(x + 0.18, [after[k] for k in keys], width=0.36, label="after")
    plt.xticks(x, labels, rotation=15, ha="right")
    plt.ylabel("Probability / entropy")
    plt.legend()
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=200)
    plt.savefig(out_png.with_suffix(".pdf"))
    plt.close()
