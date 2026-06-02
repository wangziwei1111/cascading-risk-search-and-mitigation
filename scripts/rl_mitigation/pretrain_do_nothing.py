from __future__ import annotations

import argparse

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.rl.pretrain_do_nothing_torch import pretrain_do_nothing_actor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--states", type=int, default=1024)
    args = parser.parse_args()
    cfg = load_config(args.config)
    ppo = cfg.get("ppo", {})
    env = make_ieee14_env_from_config(cfg)
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
