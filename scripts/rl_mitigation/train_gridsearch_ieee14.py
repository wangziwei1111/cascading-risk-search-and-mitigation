from __future__ import annotations

import argparse
import csv
from itertools import product
from pathlib import Path

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.rl.ppo_clip import train_ppo_clip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_gridsearch.yaml")
    parser.add_argument("--steps", type=int, default=1024)
    args = parser.parse_args()
    cfg = load_config(args.config)
    grid = cfg.get("grid", {})
    ppo = cfg.get("ppo", {})
    out = ROOT / "results" / "rl_mitigation" / "ieee14" / "gridsearch_logs" / "gridsearch_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for lr, ent in product(grid.get("learning_rate", [1e-3]), grid.get("entropy_coef", [0.001])):
        env = make_ieee14_env_from_config(cfg)
        lr_label = f"{float(lr):.0e}".replace("e-0", "e-").replace("e+0", "e")
        ent_label = str(ent).replace(".", "p")
        log_path = out.parent / f"lr_{lr_label}_ent_{ent_label}.csv"
        _, log_rows = train_ppo_clip(
            env,
            total_steps=args.steps,
            learning_rate=float(lr),
            entropy_coef=float(ent),
            n_steps=min(ppo.get("n_steps", 1024), args.steps),
            batch_size=ppo.get("batch_size", 256),
            epochs=1,
            log_path=str(log_path),
            seed=cfg.get("seed", 0),
        )
        rows.append({"learning_rate": lr, "entropy_coef": ent, "episodes": len(log_rows), "log_path": str(log_path)})
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["learning_rate", "entropy_coef", "episodes", "log_path"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"9-setting PPO-clip gridsearch smoke summary written to {out}")


if __name__ == "__main__":
    main()
