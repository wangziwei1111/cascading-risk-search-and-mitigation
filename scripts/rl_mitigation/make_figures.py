from __future__ import annotations

import argparse
import csv

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.plotting.plot_learning_curves import plot_learning_curve
from rl_mitigation.plotting.plot_survival import plot_survival


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    args = parser.parse_args()
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    plot_learning_curve(
        str(base / "train_logs" / "ppo_smoke.csv"),
        str(base / "fig7_learning_curves_gridsearch.png"),
        str(base / "fig7_learning_curves_gridsearch.pdf"),
    )
    values = []
    eval_csv = base / "eval_1000_before_after.csv"
    if not eval_csv.exists():
        eval_csv = base / "eval_10_smoke.csv"
    if eval_csv.exists():
        with open(eval_csv, newline="", encoding="utf-8") as f:
            values = [float(row["negative_return"]) for row in csv.DictReader(f)]
    plot_survival(values or [0.0], str(base / "fig8_survival_negative_return.png"), str(base / "fig8_survival_negative_return.pdf"))
    print(f"Figures written to {base}")


if __name__ == "__main__":
    main()
