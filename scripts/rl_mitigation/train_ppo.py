from __future__ import annotations

import argparse
import shutil

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.rl.ppo_clip import train_ppo_clip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--steps", type=int, default=60000)
    parser.add_argument("--init", choices=["none", "do_nothing", "oracle_bc"], default=None)
    args = parser.parse_args()
    cfg = load_config(args.config)
    ppo = cfg.get("ppo", {})
    steps = min(args.steps, 2048) if args.smoke else args.steps
    env = make_ieee14_env_from_config(cfg)
    init = args.init or ("do_nothing" if ppo.get("use_do_nothing_pretrain", True) else "none")
    pretrained = _pretrained_path(init)
    if init != "none" and (pretrained is None or not pretrained.exists()):
        print(f"Warning: pretrained actor for init={init} not found; training will use random initialization.")
        pretrained = None
    log = ROOT / "results" / "rl_mitigation" / "ieee14" / "train_logs" / f"ppo_init_{init}.csv"
    checkpoint_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints" / f"ppo_init_{init}"
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
        pretrained_actor_path=str(pretrained) if pretrained else None,
        log_path=str(log),
        checkpoint_dir=str(checkpoint_dir),
        seed=cfg.get("seed", 0),
    )
    if init == "do_nothing":
        _write_legacy_outputs(log, checkpoint_dir)
    print(f"PPO-clip {'smoke ' if args.smoke else ''}training wrote {len(rows)} episodes to {log}")


def _pretrained_path(init: str):
    base = ROOT / "results" / "rl_mitigation" / "ieee14" / "pretrain"
    if init == "do_nothing":
        return base / "policy_pretrained_torch.pt"
    if init == "oracle_bc":
        return base / "oracle_bc_full_policy.pt"
    return None


def _write_legacy_outputs(log, checkpoint_dir):
    legacy_log = ROOT / "results" / "rl_mitigation" / "ieee14" / "train_logs" / "ppo_clip_train.csv"
    legacy_ckpt = ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints"
    legacy_ckpt.mkdir(parents=True, exist_ok=True)
    if log.exists():
        shutil.copyfile(log, legacy_log)
    for name in ["latest.pt", "best.pt"]:
        src = checkpoint_dir / name
        if src.exists():
            shutil.copyfile(src, legacy_ckpt / name)


if __name__ == "__main__":
    main()
