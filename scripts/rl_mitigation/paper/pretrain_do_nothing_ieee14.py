from __future__ import annotations

import argparse

from ._common import ROOT, load_config, make_paper_env
from rl_mitigation.rl.paper_do_nothing_pretrain import pretrain_paper_do_nothing_actor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee14_paper_ppo.yaml")
    parser.add_argument("--states", type=int)
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_paper_env(cfg)
    ppo = cfg["ppo"]
    pre = cfg.get("pretrain", {})
    out = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14" / "pretrain"
    pretrain_paper_do_nothing_actor(
        env,
        str(out),
        n_states=args.states or pre.get("n_states", 2048),
        epochs=pre.get("epochs", 5),
        learning_rate=ppo.get("learning_rate", 1e-3),
        entropy_coef=pre.get("entropy_coef", 0.01),
        seed=cfg.get("seed", 0),
        target_do_nothing_prob=pre.get("target_do_nothing_prob", 0.60),
    )
    print(f"Paper do-nothing pretraining written to {out}")


if __name__ == "__main__":
    main()

