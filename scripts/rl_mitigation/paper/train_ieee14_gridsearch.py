from __future__ import annotations

import argparse
import csv
import copy

import matplotlib.pyplot as plt
import yaml

from ._common import ROOT, load_config, resolve, make_paper_env
from rl_mitigation.rl.ppo_clip import train_ppo_clip


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee14_paper_gridsearch.yaml")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--steps", type=int, default=60000)
    args = parser.parse_args()
    grid = load_config(args.config)
    base_cfg = load_config(grid.get("base_config", "configs/rl_mitigation/paper/ieee14_paper_ppo.yaml"))
    out = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14" / "gridsearch"
    out.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for lr in grid["learning_rates"]:
        for ent in grid["entropy_coefs"]:
            cfg = copy.deepcopy(base_cfg)
            cfg["ppo"]["learning_rate"] = float(lr)
            cfg["ppo"]["entropy_coef"] = float(ent)
            env = make_paper_env(cfg)
            steps = min(args.steps, 2048) if args.smoke else args.steps
            name = f"lr_{_fmt(lr)}_ent_{_fmt(ent)}"
            log = out / f"{name}{'_smoke' if args.smoke else ''}.csv"
            _, rows = train_ppo_clip(
                env,
                total_steps=steps,
                learning_rate=float(lr),
                gamma=cfg["ppo"].get("gamma", 1.0),
                gae_lambda=cfg["ppo"].get("gae_lambda", 0.95),
                entropy_coef=float(ent),
                clip_range=cfg["ppo"].get("clip_range", 0.2),
                value_clip=cfg["ppo"].get("value_clip", 0.2),
                n_steps=min(cfg["ppo"].get("n_steps", 1024), steps),
                batch_size=cfg["ppo"].get("batch_size", 256),
                epochs=cfg["ppo"].get("epochs", 10),
                policy_hidden_layers=cfg["ppo"].get("policy_hidden_layers", [64, 64]),
                value_hidden_layers=cfg["ppo"].get("value_hidden_layers", [64, 8]),
                log_path=str(log),
                checkpoint_dir=str(out / "checkpoints" / name),
                seed=cfg.get("seed", 0),
            )
            for row in rows:
                row["setting"] = name
                all_rows.append(row)
    _plot_grid(all_rows, ROOT / "results" / "rl_mitigation" / "paper" / "ieee14" / "figures", smoke=args.smoke)
    print(f"IEEE14 gridsearch logs written to {out}")


def _fmt(value) -> str:
    return f"{float(value):.0e}".replace("+", "")


def _plot_grid(rows, figures, smoke: bool) -> None:
    figures.mkdir(parents=True, exist_ok=True)
    out_csv = figures / "fig7_ieee14_learning_curves_gridsearch.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        fields = sorted({k for row in rows for k in row})
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    plt.figure(figsize=(8, 4.8), facecolor="white")
    for setting in sorted({row["setting"] for row in rows}):
        cur = [row for row in rows if row["setting"] == setting]
        if not cur:
            continue
        plt.plot([float(r["step"]) for r in cur], [float(r["episode_return"]) for r in cur], label=setting, linewidth=1.0)
    plt.xlabel("Training steps")
    plt.ylabel("Episode return")
    plt.legend(fontsize=7)
    plt.tight_layout()
    suffix = "_smoke" if smoke else ""
    plt.savefig(figures / f"fig7_ieee14_learning_curves_gridsearch{suffix}.png", dpi=200)
    plt.savefig(figures / f"fig7_ieee14_learning_curves_gridsearch{suffix}.pdf")
    plt.close()


if __name__ == "__main__":
    main()

