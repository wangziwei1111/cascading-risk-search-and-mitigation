from __future__ import annotations

import argparse

import yaml

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.rl.ppo_clip import train_ppo_clip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--steps", type=int, default=60000)
    args = parser.parse_args()
    with open(ROOT / args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    ppo = cfg.get("ppo", {})
    steps = min(args.steps, 2048) if args.smoke else args.steps
    env = CascadeMitigationEnv(
        make_ieee14_case(),
        seed=cfg.get("seed", 0),
        alpha=cfg.get("alpha", 0.1),
        max_generations=cfg.get("max_generations", 10),
        use_action_mask=ppo.get("use_action_mask", True),
        backend=cfg.get("backend", "pypower_ac"),
    )
    pretrained = ROOT / "results" / "rl_mitigation" / "ieee14" / "pretrain" / "policy_pretrained_torch.pt"
    if ppo.get("use_do_nothing_pretrain", True) and not pretrained.exists():
        print(f"Warning: {pretrained} not found; run pretrain_do_nothing first for paper-style initialization.")
    log = ROOT / "results" / "rl_mitigation" / "ieee14" / "train_logs" / "ppo_clip_train.csv"
    checkpoint_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints"
    _, rows = train_ppo_clip(
        env,
        total_steps=steps,
        learning_rate=ppo.get("learning_rate", 1e-3),
        gamma=ppo.get("gamma", 1.0),
        gae_lambda=ppo.get("gae_lambda", 0.95),
        entropy_coef=ppo.get("entropy_coef", 0.001),
        clip_range=ppo.get("clip_range", 0.2),
        value_clip=ppo.get("value_clip", 0.2),
        n_steps=min(ppo.get("n_steps", 1024), steps),
        batch_size=ppo.get("batch_size", 256),
        epochs=ppo.get("epochs", 10),
        policy_hidden_layers=ppo.get("policy_hidden_layers", [64, 64]),
        value_hidden_layers=ppo.get("value_hidden_layers", [64, 8]),
        pretrained_actor_path=str(pretrained) if pretrained.exists() else None,
        log_path=str(log),
        checkpoint_dir=str(checkpoint_dir),
        seed=cfg.get("seed", 0),
    )
    print(f"PPO-clip {'smoke ' if args.smoke else ''}training wrote {len(rows)} episodes to {log}")


if __name__ == "__main__":
    main()
