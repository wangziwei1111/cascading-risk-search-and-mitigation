from __future__ import annotations

import argparse
import csv

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.evaluation.survival import survival_curve
from rl_mitigation.plotting.plot_learning_curves import plot_learning_curve
from rl_mitigation.plotting.plot_survival import plot_survival


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

    values = []
    eval_csv = base / "eval" / "eval_before_after_100.csv"
    if not eval_csv.exists():
        eval_csv = base / "eval" / "eval_10_smoke.csv"
    if eval_csv.exists():
        with open(eval_csv, newline="", encoding="utf-8") as f:
            values = [float(row["negative_return"]) for row in csv.DictReader(f)]
    plot_survival(
        values or [0.0],
        str(figures / "fig_ieee14_survival_negative_return_100.png"),
        str(figures / "fig_ieee14_survival_negative_return_100.pdf"),
    )
    _write_survival_data(values or [0.0], figures / "fig_ieee14_survival_negative_return_100.csv")
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


def _write_survival_data(values, dst):
    xs, ys = survival_curve(values)
    with open(dst, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["negative_return", "survival_probability"])
        writer.writeheader()
        for x, y in zip(xs, ys):
            writer.writerow({"negative_return": float(x), "survival_probability": float(y)})


if __name__ == "__main__":
    main()
