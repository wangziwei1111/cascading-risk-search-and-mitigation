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


def plot_survival_by_policy(rows: list[dict], out_png: str, out_pdf: str | None = None):
    labels = {"do_nothing": "do-nothing", "agent": "PPO agent"}
    plt.figure(figsize=(6, 4), facecolor="white")
    for policy in ["do_nothing", "agent"]:
        vals = sorted(float(row["negative_return"]) for row in rows if row.get("policy") == policy)
        if not vals:
            continue
        xs = vals
        ys = [1.0 - i / len(vals) for i in range(len(vals))]
        plt.step(xs, ys, where="post", label=labels.get(policy, policy))
    plt.xlabel("Negative return")
    plt.ylabel("P(NegativeReturn > x)")
    plt.legend()
    plt.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=200)
    if out_pdf:
        plt.savefig(out_pdf)
    plt.close()
