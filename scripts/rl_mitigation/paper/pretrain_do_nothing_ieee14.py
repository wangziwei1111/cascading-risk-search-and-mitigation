from __future__ import annotations

import argparse

from ._common import ROOT, MODE_DEFAULTS, load_config, make_paper_env, normalize_mode
from rl_mitigation.rl.paper_do_nothing_pretrain import pretrain_paper_do_nothing_actor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee14_paper_ppo.yaml")
    parser.add_argument("--states", type=int)
    parser.add_argument("--mode", choices=["smoke", "medium", "formal"])
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    mode = normalize_mode(args.mode, args.smoke)
    cfg = load_config(args.config)
    env = make_paper_env(cfg)
    ppo = cfg["ppo"]
    pre = cfg.get("pretrain", {})
    out = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14" / "pretrain"
    pretrain_paper_do_nothing_actor(
        env,
        str(out),
        n_states=args.states or MODE_DEFAULTS[mode]["pretrain_states"],
        epochs=pre.get("epochs", 20),
        learning_rate=pre.get("learning_rate", ppo.get("learning_rate", 1e-3)),
        entropy_coef=pre.get("entropy_coef", 0.01),
        seed=cfg.get("seed", 0),
        target_do_nothing_prob=pre.get("target_do_nothing_prob", 0.60),
        target_do_nothing_prob_min=pre.get("target_do_nothing_prob_min", 0.35),
        target_do_nothing_prob_max=pre.get("target_do_nothing_prob_max", 0.80),
        early_stop_when_target_reached=pre.get("early_stop_when_target_reached", True),
        policy_hidden_layers=ppo.get("policy_hidden_layers", [64, 64]),
        value_hidden_layers=ppo.get("value_hidden_layers", [64, 8]),
    )
    print(f"Paper do-nothing pretraining written to {out}")


if __name__ == "__main__":
    main()
