from __future__ import annotations

import argparse
import csv

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.rl.ppo_clip import train_ppo_clip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--steps", type=int, default=512)
    args = parser.parse_args()
    cfg = load_config(args.config)
    rows = []
    for enabled in [True, False]:
        env = make_ieee14_env_from_config(cfg)
        env.use_action_mask = enabled
        _, logs = train_ppo_clip(env, total_steps=args.steps, n_steps=64, batch_size=64, epochs=1, seed=cfg.get("seed", 0))
        rows.append(_summary("mask=true" if enabled else "mask=false", args.steps, logs))
    out = ROOT / "results" / "rl_mitigation" / "ieee14" / "ablation" / "mask_vs_nomask_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Mask ablation written to {out}")


def _summary(setting: str, steps: int, rows: list[dict]) -> dict:
    def avg(name):
        vals = [float(row.get(name, 0.0)) for row in rows]
        return sum(vals) / max(1, len(vals))
    return {
        "setting": setting,
        "steps": steps,
        "mean_episode_return": avg("episode_return"),
        "mean_negative_return": avg("negative_return"),
        "mean_num_invalid_actions": avg("num_invalid_actions"),
        "sampled_invalid_action_count": sum(int(row.get("sampled_invalid_action_count", 0)) for row in rows),
        "mean_valid_action_count": avg("mean_valid_action_count"),
    }


if __name__ == "__main__":
    main()
