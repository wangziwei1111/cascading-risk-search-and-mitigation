from __future__ import annotations

import argparse
import csv
from itertools import product

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.rl.ppo_train import train_ppo_smoke


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_gridsearch.yaml")
    parser.add_argument("--steps", type=int, default=1024)
    args = parser.parse_args()
    out = ROOT / "results" / "rl_mitigation" / "ieee14" / "gridsearch_logs" / "gridsearch_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for lr, ent in product([1e-3, 1e-4, 1e-5], [0.1, 0.01, 0.001]):
        env = CascadeMitigationEnv(make_ieee14_case(), seed=int(lr * 1e6 + ent * 1e4), use_action_mask=True)
        _, log_rows = train_ppo_smoke(env, steps=args.steps)
        rows.append({"learning_rate": lr, "entropy_coef": ent, "episodes": len(log_rows)})
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["learning_rate", "entropy_coef", "episodes"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"9-setting gridsearch smoke summary written to {out}")


if __name__ == "__main__":
    main()
