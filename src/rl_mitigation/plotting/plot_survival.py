from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from ..evaluation.survival import survival_curve


def plot_survival(values, out_png: str, out_pdf: str | None = None):
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
