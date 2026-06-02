from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


def plot_survival(values, out_png: str, out_pdf: str | None = None):
    from ..evaluation.survival import survival_curve

    xs, ys = survival_curve(values)
    plt.figure(figsize=(6, 4), facecolor="white")
    plt.step(xs, ys, where="post", label="negative return")
    plt.xlabel("Negative return")
    plt.ylabel("Survival probability")
    plt.legend()
    plt.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=200)
    if out_pdf:
        plt.savefig(out_pdf)
    plt.close()


def plot_survival_by_policy(rows: list[dict], out_png: str, out_pdf: str | None = None, yscale: str = "linear"):
    labels = {
        "do_nothing": "do-nothing",
        "agent": "PPO agent",
        "ppo_agent": "PPO agent",
        "one_step_oracle": "one-step oracle",
    }
    preferred_order = ["do_nothing", "agent", "ppo_agent", "one_step_oracle"]
    policies = [p for p in preferred_order if any(row.get("policy") == p for row in rows)]
    other_policies = {row.get("policy") for row in rows if row.get("policy")} - set(policies)
    policies.extend(sorted(other_policies))
    plt.figure(figsize=(6, 4), facecolor="white")
    for policy in policies:
        vals = sorted(float(row["negative_return"]) for row in rows if row.get("policy") == policy)
        if not vals:
            continue
        xs = vals
        ys = [1.0 - i / len(vals) for i in range(len(vals))]
        plt.step(xs, ys, where="post", label=labels.get(policy, policy))
    plt.xlabel("Negative reward")
    plt.ylabel("Probability greater than")
    if yscale in {"log", "linear"}:
        plt.yscale(yscale)
    plt.legend()
    plt.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=200)
    if out_pdf:
        plt.savefig(out_pdf)
    plt.close()
