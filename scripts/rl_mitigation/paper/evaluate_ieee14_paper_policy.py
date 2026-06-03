from __future__ import annotations

import argparse

from ._common import ROOT, MODE_DEFAULTS, load_config, make_paper_env, mode_suffix, normalize_mode
from rl_mitigation.evaluation.evaluate_agent import run_policy, save_eval_csv
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios
from rl_mitigation.rl.ppo_clip import load_checkpoint


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee14_paper_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--checkpoint")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--mode", choices=["smoke", "medium", "formal"])
    args = parser.parse_args()
    mode = normalize_mode(args.mode, args.smoke)
    cfg = load_config(args.config)
    episodes = args.episodes if args.episodes != 1000 else MODE_DEFAULTS[mode]["eval_episodes"]
    env = make_paper_env(cfg)
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14"
    suffix = mode_suffix(mode)
    ckpt = args.checkpoint or str(base / "checkpoints" / f"proposed_pretrain_mask{suffix}" / "latest.pt")
    model = load_checkpoint(ckpt) if ckpt and __import__("pathlib").Path(ckpt).exists() else None
    scenarios = generate_eval_scenarios(env, episodes=episodes, seed=cfg.get("seed", 0))
    rows = []
    rows.extend(run_policy(env, episodes=episodes, model=model, with_agent=False, scenarios=scenarios))
    agent_rows = run_policy(env, episodes=episodes, model=model, with_agent=bool(model), scenarios=scenarios, eval_mode="deterministic")
    for row in agent_rows:
        row["policy"] = "paper_proposed_policy"
    rows.extend(agent_rows)
    out = base / "eval" / f"eval_{episodes}_before_after{suffix}.csv"
    save_eval_csv(rows, str(out))
    print(f"IEEE14 paper eval written to {out}")


if __name__ == "__main__":
    main()
