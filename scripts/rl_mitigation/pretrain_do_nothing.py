from __future__ import annotations

import argparse

import numpy as np

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.rl.pretrain_do_nothing import pretrain_policy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--states", type=int, default=512)
    args = parser.parse_args()
    case = make_ieee14_case()
    env = CascadeMitigationEnv(case, seed=0, use_action_mask=True)
    model, states, actions = pretrain_policy(env, n_states=args.states)
    out = ROOT / "results" / "rl_mitigation" / "ieee14" / "pretrain"
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / "states_actions.npz", states=states, actions=actions)
    model.save(str(out / "policy_pretrained.pt"))
    print(f"do-nothing pretraining artifacts written to {out}")


if __name__ == "__main__":
    main()
