from __future__ import annotations

import argparse
import json

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.evaluate_agent import run_policy, save_eval_csv
from rl_mitigation.rl.networks import ActorCritic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--with-agent", action="store_true")
    parser.add_argument("--without-agent", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    episodes = min(args.episodes, 10) if args.smoke else args.episodes
    env = CascadeMitigationEnv(make_ieee14_case(), seed=2, use_action_mask=True)
    model = ActorCritic(env.observation_space_shape[0], env.action_space_n)
    policy_path = ROOT / "results" / "rl_mitigation" / "ieee14" / "train_logs" / "ppo_policy.pt"
    if policy_path.exists():
        model = ActorCritic.load(str(policy_path))
    rows = []
    if args.with_agent or not args.without_agent:
        rows.extend(run_policy(env, episodes=episodes, model=model, with_agent=True))
    if args.without_agent or not args.with_agent:
        rows.extend(run_policy(env, episodes=episodes, model=model, with_agent=False))
    out = ROOT / "results" / "rl_mitigation" / "ieee14" / ("eval_10_smoke.csv" if args.smoke else "eval_1000_before_after.csv")
    save_eval_csv(rows, str(out))
    summary = {
        "episodes": episodes,
        "policies": sorted(set(row["policy"] for row in rows)),
        "mean_negative_return": sum(row["negative_return"] for row in rows) / max(1, len(rows)),
    }
    with open(ROOT / "results" / "rl_mitigation" / "ieee14" / "metrics_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Evaluation rows written to {out}")


if __name__ == "__main__":
    main()
