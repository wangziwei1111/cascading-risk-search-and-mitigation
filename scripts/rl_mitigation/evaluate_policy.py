from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.evaluation.evaluate_agent import run_policy, save_eval_csv
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios, load_scenarios, save_scenarios
from rl_mitigation.evaluation.scenario_split import SPLIT_SEEDS, load_or_create_scenario_split
from rl_mitigation.rl.ppo_clip import load_checkpoint
from rl_mitigation.rl.torch_networks import TorchActorCritic
from scripts.rl_mitigation._common import make_ieee14_env_from_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--with-agent", action="store_true")
    parser.add_argument("--without-agent", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--eval-mode", choices=["deterministic", "stochastic"], default="deterministic")
    parser.add_argument("--split", choices=["train", "val", "test"])
    parser.add_argument("--scenario-file")
    parser.add_argument("--checkpoint")
    parser.add_argument("--policy-name", default="agent")
    args = parser.parse_args()
    with open(ROOT / args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    episodes = min(args.episodes, 10) if args.smoke else args.episodes
    env = make_ieee14_env_from_config(cfg)
    model = TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    policy_path = _resolve_path(args.checkpoint) if args.checkpoint else ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints" / "latest.pt"
    if policy_path.exists():
        model = load_checkpoint(str(policy_path))
    scenarios, label = _load_scenarios(env, cfg, args, episodes)
    rows = []
    if args.with_agent or not args.without_agent:
        agent_rows = run_policy(env, episodes=episodes, model=model, with_agent=True, scenarios=scenarios, eval_mode=args.eval_mode)
        for row in agent_rows:
            row["policy"] = args.policy_name
        rows.extend(agent_rows)
    if args.without_agent or not args.with_agent:
        rows.extend(run_policy(env, episodes=episodes, model=model, with_agent=False, scenarios=scenarios, eval_mode=args.eval_mode))
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval"
    out = _output_path(out_dir, args, episodes, label)
    legacy_out = out_dir / f"eval_before_after_{episodes}.csv"
    save_eval_csv(rows, str(out))
    if args.eval_mode == "deterministic" and not args.smoke:
        save_eval_csv(rows, str(legacy_out))
    summary = {
        "episodes": episodes,
        "policies": sorted(set(row["policy"] for row in rows)),
        "mean_negative_return": sum(row["negative_return"] for row in rows) / max(1, len(rows)),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / ("metrics_summary_10.json" if args.smoke else f"metrics_summary_{episodes}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Evaluation rows written to {out}")


def _load_scenarios(env, cfg, args, episodes):
    if args.scenario_file:
        path = _resolve_path(args.scenario_file)
        return load_scenarios(str(path)), args.split or "custom"
    if args.split:
        counts = {"train": 300, "val": 100, "test": 100}
        scenarios, _ = load_or_create_scenario_split(
            env,
            ROOT / "results" / "rl_mitigation" / "ieee14" / "scenarios",
            args.split,
            counts[args.split],
            SPLIT_SEEDS[args.split],
        )
        return scenarios, args.split
    scenario_path = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval" / f"eval_scenarios_seed{cfg.get('seed', 0)}_episodes{episodes}.json"
    scenarios = generate_eval_scenarios(env, episodes=episodes, seed=cfg.get("seed", 0))
    save_scenarios(scenarios, str(scenario_path))
    return scenarios, ""


def _output_path(out_dir, args, episodes, label):
    if args.smoke:
        return out_dir / "eval_10_smoke.csv"
    if label:
        if args.with_agent and not args.without_agent:
            return out_dir / f"{label}_eval_{args.policy_name}_{args.eval_mode}.csv"
        if args.without_agent and not args.with_agent:
            return out_dir / f"{label}_eval_do_nothing.csv"
        return out_dir / f"{label}_eval_before_after_{args.eval_mode}.csv"
    return out_dir / f"eval_before_after_{episodes}_{args.eval_mode}.csv"


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


if __name__ == "__main__":
    main()
