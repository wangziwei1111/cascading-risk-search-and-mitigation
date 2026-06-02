from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from .torch_networks import TorchActorCritic, torch


def pretrain_oracle_bc(
    env,
    scenarios: list[dict],
    scan_rows: list[dict],
    output_dir: str,
    min_improvement: float = 1.0,
    epochs: int = 20,
    entropy_coef: float = 0.01,
    learning_rate: float = 1e-3,
    seed: int = 0,
):
    by_id = {}
    for row in scan_rows:
        by_id.setdefault(str(row["scenario_id"]), []).append(row)
    samples = []
    for scenario in scenarios:
        rows = by_id.get(str(scenario["scenario_id"]), [])
        if not rows:
            continue
        dn = next(row for row in rows if int(row["action"]) == 0)
        valid = [row for row in rows if str(row.get("is_valid_action")).lower() == "true"]
        best = min(valid or rows, key=lambda r: float(r["negative_return"]))
        improvement = float(dn["negative_return"]) - float(best["negative_return"])
        if improvement >= min_improvement:
            obs, info = env.reset(seed=int(scenario["seed"]), options={"scenario": scenario})
            samples.append((obs, info["action_mask"], int(best["action"]), improvement, scenario["scenario_id"]))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "oracle_bc_dataset.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario_id", "action", "improvement"])
        writer.writeheader()
        for _, _, action, improvement, sid in samples:
            writer.writerow({"scenario_id": sid, "action": action, "improvement": improvement})
    model = TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    mean_prob_best = 0.0
    mean_entropy = 0.0
    if samples:
        torch.manual_seed(seed)
        x = torch.tensor(np.asarray([sample[0] for sample in samples]), dtype=torch.float32)
        masks = torch.tensor(np.asarray([sample[1] for sample in samples]), dtype=torch.bool)
        y = torch.tensor([sample[2] for sample in samples], dtype=torch.long)
        opt = torch.optim.Adam(model.actor.parameters(), lr=learning_rate)
        for _ in range(epochs):
            logits = model.masked_logits(x, masks)
            probs = torch.softmax(logits, dim=-1)
            entropy = -(probs * torch.log(probs + 1e-8)).sum(dim=-1).mean()
            loss = torch.nn.functional.cross_entropy(logits, y) - entropy_coef * entropy
            opt.zero_grad()
            loss.backward()
            opt.step()
        with torch.no_grad():
            logits = model.masked_logits(x, masks)
            probs = torch.softmax(logits, dim=-1)
            mean_prob_best = float(probs[torch.arange(len(samples)), y].mean().item())
            mean_entropy = float((-(probs * torch.log(probs + 1e-8)).sum(dim=-1)).mean().item())
    torch.save({"actor_state_dict": model.actor.state_dict(), "obs_dim": model.obs_dim, "action_dim": model.action_dim}, out / "oracle_bc_policy.pt")
    diagnostics = {
        "num_train_scenarios": len(scenarios),
        "num_bc_samples": len(samples),
        "num_samples": len(samples),
        "min_improvement": min_improvement,
        "action_distribution": dict(Counter(str(sample[2]) for sample in samples)),
        "mean_train_improvement": float(np.mean([sample[3] for sample in samples])) if samples else 0.0,
        "mean_prob_best_action_after_bc": mean_prob_best,
        "mean_entropy_after_bc": mean_entropy,
    }
    with open(out / "oracle_bc_diagnostics.json", "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, indent=2)
    return diagnostics
