from __future__ import annotations

import argparse

from ._common import ROOT, load_config, make_paper_env
from rl_mitigation.rl.paper_do_nothing_pretrain import pretrain_paper_do_nothing_actor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee118_paper_ppo.yaml")
    parser.add_argument("--states", type=int, default=256)
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_paper_env(cfg)
    out = ROOT / "results" / "rl_mitigation" / "paper" / "ieee118" / "pretrain"
    ppo = cfg["ppo"]
    pretrain_paper_do_nothing_actor(
        env,
        str(out),
        n_states=args.states,
        epochs=cfg.get("pretrain", {}).get("epochs", 5),
        learning_rate=ppo.get("learning_rate", 1e-4),
        entropy_coef=cfg.get("pretrain", {}).get("entropy_coef", 0.01),
        seed=cfg.get("seed", 0),
        target_do_nothing_prob=cfg.get("pretrain", {}).get("target_do_nothing_prob", 0.60),
        policy_hidden_layers=ppo.get("policy_hidden_layers", [256, 256]),
        value_hidden_layers=ppo.get("value_hidden_layers", [64, 8]),
    )
    print(f"IEEE118 paper pretrain written to {out}")


if __name__ == "__main__":
    main()
