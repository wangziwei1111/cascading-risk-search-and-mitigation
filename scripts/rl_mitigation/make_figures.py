from __future__ import annotations

import argparse
import csv

import matplotlib.pyplot as plt

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.evaluation.survival import survival_by_policy
from rl_mitigation.plotting.plot_learning_curves import plot_learning_curve
from rl_mitigation.plotting.plot_survival import plot_survival_by_policy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    args = parser.parse_args()
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    figures = base / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    train_csv = base / "train_logs" / "ppo_clip_train.csv"
    plot_learning_curve(
        str(train_csv),
        str(figures / "fig_ieee14_learning_curve_smoke.png"),
        str(figures / "fig_ieee14_learning_curve_smoke.pdf"),
    )
    _copy_learning_data(train_csv, figures / "fig_ieee14_learning_curve_smoke.csv")
    _plot_gridsearch_curves(base / "gridsearch_logs", figures)

    eval_csv = base / "eval" / "eval_before_after_100.csv"
    if not eval_csv.exists():
        eval_csv = base / "eval" / "eval_10_smoke.csv"
    if not (base / "checkpoints" / "latest.pt").exists():
        print("Warning: PPO checkpoint not found; survival plot may compare an untrained agent.")
    rows = []
    if eval_csv.exists():
        with open(eval_csv, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    plot_survival_by_policy(
        rows,
        str(figures / "fig_ieee14_survival_negative_return_100.png"),
        str(figures / "fig_ieee14_survival_negative_return_100.pdf"),
    )
    _write_survival_data(rows, figures / "fig_ieee14_survival_negative_return_100.csv")
    print(f"Figures written to {figures}")


def _copy_learning_data(src, dst):
    if not src.exists():
        return
    with open(src, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with open(dst, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["step", "episode_return", "negative_return"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "step": row.get("step", 0),
                "episode_return": row.get("episode_return", 0),
                "negative_return": row.get("negative_return", 0),
            })


def _write_survival_data(rows, dst):
    survival_rows = survival_by_policy(rows)
    with open(dst, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["policy", "negative_return", "survival_probability"])
        writer.writeheader()
        writer.writerows(survival_rows)


def _plot_gridsearch_curves(log_dir, figures):
    files = sorted(log_dir.glob("lr_*_ent_*.csv"))
    if not files:
        return
    combined_rows = []
    plt.figure(figsize=(7, 4.5), facecolor="white")
    for path in files:
        steps, returns = [], []
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                steps.append(float(row["step"]))
                returns.append(float(row["episode_return"]))
        if not steps:
            continue
        smooth = _ema(returns, alpha=0.2)
        label = path.stem.replace("lr_", "lr=").replace("_ent_", ", ent=")
        plt.plot(steps, smooth, label=label, linewidth=1.2)
        for step, value in zip(steps, smooth):
            combined_rows.append({"setting": label, "step": step, "smoothed_episode_return": value})
    plt.xlabel("Training step")
    plt.ylabel("EMA episode return")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(figures / "fig7_learning_curves_gridsearch.png", dpi=200)
    plt.savefig(figures / "fig7_learning_curves_gridsearch.pdf")
    plt.close()
    with open(figures / "fig7_learning_curves_gridsearch.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["setting", "step", "smoothed_episode_return"])
        writer.writeheader()
        writer.writerows(combined_rows)


def _ema(values, alpha=0.2):
    out = []
    cur = None
    for value in values:
        cur = value if cur is None else alpha * value + (1.0 - alpha) * cur
        out.append(cur)
    return out


if __name__ == "__main__":
    main()
