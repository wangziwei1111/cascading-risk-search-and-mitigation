from __future__ import annotations

import argparse
import json
from pathlib import Path

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.evaluate_agent import save_eval_csv
from rl_mitigation.evaluation.safe_policy import load_actor_policy, run_safe_policy
from rl_mitigation.evaluation.scenarios import load_scenarios
from rl_mitigation.evaluation.scenario_split import SPLIT_SEEDS, load_or_create_scenario_split


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--split", choices=["train", "val", "test"], default="test")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--eval-mode", choices=["deterministic", "stochastic"], default="deterministic")
    parser.add_argument("--scenario-file")
    parser.add_argument("--policy-path", default="results/rl_mitigation/ieee14/pretrain/oracle_bc_full_policy.pt")
    parser.add_argument("--policy-name", default="safe_oracle_bc_full")
    parser.add_argument("--active-prob-threshold", type=float)
    parser.add_argument("--margin-threshold", type=float)
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_ieee14_env_from_config(cfg)
    scenarios = _load_scenarios(env, args)
    thresholds = _thresholds(args, cfg)
    model = load_actor_policy(_resolve(args.policy_path))
    rows = run_safe_policy(env, scenarios, model, args.policy_name, thresholds["active_prob_threshold"], thresholds["margin_threshold"], args.episodes)
    out = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval" / f"{args.split}_eval_{args.policy_name}_{args.eval_mode}.csv"
    save_eval_csv(rows, str(out))
    print(f"Safe policy evaluation written to {out}")


def _load_scenarios(env, args):
    if args.scenario_file:
        return load_scenarios(str(_resolve(args.scenario_file)))
    scenarios, _ = load_or_create_scenario_split(
        env,
        ROOT / "results" / "rl_mitigation" / "ieee14" / "scenarios",
        args.split,
        {"train": 300, "val": 100, "test": 100}[args.split],
        SPLIT_SEEDS[args.split],
    )
    return scenarios


def _thresholds(args, cfg):
    selected = ROOT / "results" / "rl_mitigation" / "ieee14" / "ablation" / "safe_policy_threshold_selected.json"
    if args.active_prob_threshold is not None and args.margin_threshold is not None:
        return {"active_prob_threshold": args.active_prob_threshold, "margin_threshold": args.margin_threshold}
    if selected.exists():
        with open(selected, encoding="utf-8") as f:
            return json.load(f)
    safe_cfg = cfg.get("safe_policy", {})
    return {
        "active_prob_threshold": safe_cfg.get("active_prob_threshold", 0.35),
        "margin_threshold": safe_cfg.get("margin_threshold", 0.05),
    }


def _resolve(path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
