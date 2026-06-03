from __future__ import annotations

import argparse

from ._common import ROOT, load_config, make_paper_env
from rl_mitigation.rl.ppo_clip import train_ppo_clip


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee118_paper_ppo.yaml")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--steps", type=int, default=600000)
    parser.add_argument("--variant", default="proposed_pretrain_mask")
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_paper_env(cfg)
    ppo = cfg["ppo"]
    steps = min(args.steps, 2048) if args.smoke else args.steps
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee118"
    pretrain = base / "pretrain" / "policy_pretrained_torch.pt"
    log = base / "train_logs" / f"{args.variant}{'_smoke' if args.smoke else ''}.csv"
    ckpt = base / "checkpoints" / args.variant
    _, rows = train_ppo_clip(
        env,
        total_steps=steps,
        learning_rate=ppo.get("learning_rate", 1e-4),
        gamma=ppo.get("gamma", 1.0),
        gae_lambda=ppo.get("gae_lambda", 0.95),
        entropy_coef=ppo.get("entropy_coef", 0.01),
        clip_range=ppo.get("clip_range", 0.3),
        value_clip=ppo.get("value_clip", 0.3),
        n_steps=min(ppo.get("n_steps", 1024), steps),
        batch_size=ppo.get("batch_size", 256),
        epochs=ppo.get("epochs", 10),
        policy_hidden_layers=ppo.get("policy_hidden_layers", [256, 256]),
        value_hidden_layers=ppo.get("value_hidden_layers", [64, 8]),
        pretrained_actor_path=str(pretrain) if pretrain.exists() else None,
        log_path=str(log),
        checkpoint_dir=str(ckpt),
        seed=cfg.get("seed", 0),
    )
    print(f"IEEE118 paper PPO wrote {len(rows)} episodes to {log}")


if __name__ == "__main__":
    main()

