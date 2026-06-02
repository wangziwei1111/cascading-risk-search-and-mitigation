from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


def plot_learning_curve(csv_path: str, out_png: str, out_pdf: str | None = None):
    steps, returns = [], []
    if Path(csv_path).exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                steps.append(float(row["step"]))
                returns.append(float(row["episode_return"]))
    if not steps:
        steps, returns = [0], [0]
    plt.figure(figsize=(6, 4), facecolor="white")
    plt.plot(steps, returns, label="PPO smoke")
    plt.xlabel("Training step")
    plt.ylabel("Episode return")
    plt.legend()
    plt.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=200)
    if out_pdf:
        plt.savefig(out_pdf)
    plt.close()
