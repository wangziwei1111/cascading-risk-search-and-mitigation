from __future__ import annotations

import argparse

import yaml

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.rl.pretrain_do_nothing_torch import pretrain_do_nothing_actor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--states", type=int, default=1024)
    args = parser.parse_args()
    with open(ROOT / args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    ppo = cfg.get("ppo", {})
    env = CascadeMitigationEnv(
        make_ieee14_case(),
        seed=cfg.get("seed", 0),
        alpha=cfg.get("alpha", 0.1),
        max_generations=cfg.get("max_generations", 10),
        use_action_mask=ppo.get("use_action_mask", True),
        backend=cfg.get("backend", "pypower_ac"),
    )
    out = ROOT / "results" / "rl_mitigation" / "ieee14" / "pretrain"
    pretrain_do_nothing_actor(
        env,
        output_dir=str(out),
        n_states=args.states,
        epochs=10,
        learning_rate=ppo.get("learning_rate", 1e-3),
        entropy_coef=ppo.get("entropy_coef", 0.001),
        seed=cfg.get("seed", 0),
    )
    print(f"PyTorch do-nothing pretraining artifacts written to {out}")


if __name__ == "__main__":
    main()
