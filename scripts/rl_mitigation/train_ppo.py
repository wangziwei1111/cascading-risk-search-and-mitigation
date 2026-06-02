from __future__ import annotations

import argparse

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.rl.networks import ActorCritic
from rl_mitigation.rl.ppo_train import train_ppo_smoke


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--steps", type=int, default=60000)
    args = parser.parse_args()
    steps = min(args.steps, 2048) if args.smoke else args.steps
    case = make_ieee14_case()
    env = CascadeMitigationEnv(case, seed=1, use_action_mask=True)
    model = ActorCritic(env.observation_space_shape[0], env.action_space_n)
    pretrained = ROOT / "results" / "rl_mitigation" / "ieee14" / "pretrain" / "policy_pretrained.pt"
    if pretrained.exists():
        model = ActorCritic.load(str(pretrained))
    log = ROOT / "results" / "rl_mitigation" / "ieee14" / "train_logs" / "ppo_smoke.csv"
    model, rows = train_ppo_smoke(env, steps=steps, log_path=str(log), model=model)
    model.save(str(ROOT / "results" / "rl_mitigation" / "ieee14" / "train_logs" / "ppo_policy.pt"))
    print(f"PPO {'smoke ' if args.smoke else ''}training wrote {len(rows)} episodes to {log}")


if __name__ == "__main__":
    main()
