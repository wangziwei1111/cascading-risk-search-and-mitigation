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
    mode: str = "full",
):
    by_id = {}
    for row in scan_rows:
        by_id.setdefault(str(row["scenario_id"]), []).append(row)
    samples = []
    dataset_rows = []
    for scenario in scenarios:
        rows = by_id.get(str(scenario["scenario_id"]), [])
        if not rows:
            continue
        dn = next(row for row in rows if int(row["action"]) == 0)
        valid = [row for row in rows if str(row.get("is_valid_action")).lower() == "true"]
        best = min(valid or rows, key=lambda r: float(r["negative_return"]))
        improvement = float(dn["negative_return"]) - float(best["negative_return"])
        is_improvable = improvement >= min_improvement
        label_action = int(best["action"]) if is_improvable else 0
        label_type = "active_mitigation" if label_action != 0 else "do_nothing"
        if mode == "full" or is_improvable:
            obs, info = env.reset(seed=int(scenario["seed"]), options={"scenario": scenario})
            samples.append((obs, info["action_mask"], label_action, improvement, scenario["scenario_id"], label_type, is_improvable))
            dataset_rows.append({
                "scenario_id": scenario["scenario_id"],
                "initial_outages": ",".join(str(x) for x in scenario.get("initial_outages", [])),
                "initial_outage_type": scenario.get("initial_outage_type", ""),
                "do_nothing_negative_return": float(dn["negative_return"]),
                "best_action": int(best["action"]),
                "best_negative_return": float(best["negative_return"]),
                "best_improvement": improvement,
                "label_action": label_action,
                "label_type": label_type,
                "is_improvable": is_improvable,
            })
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prefix = "oracle_bc_full" if mode == "full" else "oracle_bc_positive_only"
    dataset_path = out / f"{prefix}_dataset.csv"
    with open(dataset_path, "w", newline="", encoding="utf-8") as f:
        fields = [
            "scenario_id", "initial_outages", "initial_outage_type",
            "do_nothing_negative_return", "best_action", "best_negative_return",
            "best_improvement", "label_action", "label_type", "is_improvable",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(dataset_rows)
    if mode != "full":
        with open(out / "oracle_bc_dataset.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scenario_id", "action", "improvement"])
            writer.writeheader()
            for _, _, action, improvement, sid, _, _ in samples:
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
    torch.save({"actor_state_dict": model.actor.state_dict(), "obs_dim": model.obs_dim, "action_dim": model.action_dim}, out / f"{prefix}_policy.pt")
    if mode == "full":
        torch.save({"actor_state_dict": model.actor.state_dict(), "obs_dim": model.obs_dim, "action_dim": model.action_dim}, out / "oracle_bc_policy.pt")
    label_actions = [sample[2] for sample in samples]
    label_types = [sample[5] for sample in samples]
    improvements_all = [row["best_improvement"] for row in dataset_rows]
    improvements_improvable = [row["best_improvement"] for row in dataset_rows if row["is_improvable"]]
    prob_dn_non_improvable = 0.0
    prob_active_improvable = 0.0
    if samples:
        with torch.no_grad():
            x = torch.tensor(np.asarray([sample[0] for sample in samples]), dtype=torch.float32)
            masks = torch.tensor(np.asarray([sample[1] for sample in samples]), dtype=torch.bool)
            probs = torch.softmax(model.masked_logits(x, masks), dim=-1)
            non_idx = [i for i, sample in enumerate(samples) if not sample[6]]
            imp_idx = [i for i, sample in enumerate(samples) if sample[6]]
            if non_idx:
                prob_dn_non_improvable = float(probs[non_idx, 0].mean().item())
            if imp_idx:
                prob_active_improvable = float((1.0 - probs[imp_idx, 0]).mean().item())
    diagnostics = {
        "mode": mode,
        "num_train_scenarios": len(scenarios),
        "num_bc_samples": len(samples),
        "num_samples": len(samples),
        "num_improvable": sum(1 for row in dataset_rows if row["is_improvable"]),
        "num_non_improvable": sum(1 for row in dataset_rows if not row["is_improvable"]),
        "improvable_ratio": sum(1 for row in dataset_rows if row["is_improvable"]) / max(1, len(dataset_rows)),
        "min_improvement": min_improvement,
        "action_distribution": dict(Counter(str(x) for x in label_actions)),
        "label_action_distribution": dict(Counter(str(x) for x in label_actions)),
        "label_type_distribution": dict(Counter(label_types)),
        "mean_best_improvement_all": float(np.mean(improvements_all)) if improvements_all else 0.0,
        "mean_best_improvement_improvable": float(np.mean(improvements_improvable)) if improvements_improvable else 0.0,
        "mean_train_improvement": float(np.mean([sample[3] for sample in samples])) if samples else 0.0,
        "mean_prob_best_action_after_bc": mean_prob_best,
        "mean_prob_label_action_after_bc": mean_prob_best,
        "mean_prob_do_nothing_on_non_improvable": prob_dn_non_improvable,
        "mean_prob_active_on_improvable": prob_active_improvable,
        "mean_entropy_after_bc": mean_entropy,
    }
    with open(out / f"{prefix}_diagnostics.json", "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, indent=2)
    if mode == "full":
        with open(out / "oracle_bc_diagnostics.json", "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2)
    return diagnostics
