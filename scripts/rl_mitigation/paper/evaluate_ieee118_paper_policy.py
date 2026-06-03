from __future__ import annotations

import argparse

from ._common import ROOT, load_config, make_paper_env
from rl_mitigation.evaluation.evaluate_agent import run_policy, save_eval_csv
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios
from rl_mitigation.rl.ppo_clip import load_checkpoint


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee118_paper_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)
    episodes = min(args.episodes, 20) if args.smoke else args.episodes
    env = make_paper_env(cfg)
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee118"
    ckpt = base / "checkpoints" / "proposed_pretrain_mask" / "latest.pt"
    model = None
    if ckpt.exists():
        try:
            model = load_checkpoint(str(ckpt))
        except RuntimeError:
            model = None
    scenarios = generate_eval_scenarios(env, episodes=episodes, seed=cfg.get("seed", 0))
    rows = run_policy(env, episodes=episodes, model=model, with_agent=False, scenarios=scenarios)
    if model is not None:
        agent = run_policy(env, episodes=episodes, model=model, with_agent=True, scenarios=scenarios)
        for row in agent:
            row["policy"] = "paper_proposed_policy"
        rows.extend(agent)
    out = base / "eval" / f"eval_{episodes}_before_after{'_smoke' if args.smoke else ''}.csv"
    save_eval_csv(rows, str(out))
    print(f"IEEE118 paper eval written to {out}")


if __name__ == "__main__":
    main()
