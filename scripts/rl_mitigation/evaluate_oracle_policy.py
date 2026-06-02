from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.action_value import run_episode_with_first_action
from rl_mitigation.evaluation.evaluate_agent import run_policy
from rl_mitigation.evaluation.oracle_policy import choose_best_initial_action
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios, load_scenarios, save_scenarios
from rl_mitigation.evaluation.scenario_split import SPLIT_SEEDS, load_or_create_scenario_split
from rl_mitigation.evaluation.evaluate_agent import save_eval_csv
from rl_mitigation.rl.ppo_clip import load_checkpoint
from rl_mitigation.rl.torch_networks import TorchActorCritic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--eval-mode", choices=["deterministic", "stochastic"], default="deterministic")
    parser.add_argument("--split", choices=["train", "val", "test"])
    parser.add_argument("--scenario-file")
    parser.add_argument("--checkpoint")
    parser.add_argument("--policy-name", default="ppo_agent")
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_ieee14_env_from_config(cfg)
    eval_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval"
    scenarios, label = _load_scenarios(env, cfg, args)
    episodes = min(args.episodes, len(scenarios))
    rows = []
    ckpt = _resolve_path(args.checkpoint) if args.checkpoint else ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints" / "latest.pt"
    model = load_checkpoint(str(ckpt)) if ckpt.exists() else TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    agent_rows = run_policy(env, episodes, model=model, with_agent=True, scenarios=scenarios, eval_mode=args.eval_mode)
    for row in agent_rows:
        row["policy"] = args.policy_name
    rows.extend(agent_rows)
    oracle_rows = []
    dn_rows = []
    for scenario in scenarios[:episodes]:
        dn = run_episode_with_first_action(env, scenario, 0)
        dn["policy"] = "do_nothing"
        rows.append(dn)
        dn_rows.append(dn)
        _, best = choose_best_initial_action(env, scenario)
        best["policy"] = "one_step_oracle"
        rows.append(best)
        oracle_rows.append(best)
    out = eval_dir / (f"{label}_eval_do_nothing_agent_oracle_{args.eval_mode}.csv" if label else f"eval_do_nothing_agent_oracle_{episodes}.csv")
    save_eval_csv(rows, str(out))
    if label:
        save_eval_csv(dn_rows, str(eval_dir / f"{label}_eval_do_nothing.csv"))
        save_eval_csv(oracle_rows, str(eval_dir / f"{label}_eval_one_step_oracle.csv"))
    summary = _summary(rows)
    summary_path = eval_dir / (f"{label}_oracle_summary_{args.eval_mode}.json" if label else f"oracle_summary_{episodes}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Oracle evaluation written to {out}; oracle_gap={summary['oracle_gap']:.4f}")


def _load_scenarios(env, cfg, args):
    if args.scenario_file:
        return load_scenarios(str(_resolve_path(args.scenario_file))), args.split or "custom"
    if args.split:
        scenarios, _ = load_or_create_scenario_split(
            env,
            ROOT / "results" / "rl_mitigation" / "ieee14" / "scenarios",
            args.split,
            {"train": 300, "val": 100, "test": 100}[args.split],
            SPLIT_SEEDS[args.split],
        )
        return scenarios, args.split
    eval_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval"
    scenario_path = eval_dir / f"eval_scenarios_seed{cfg.get('seed', 0)}_episodes{args.episodes}.json"
    scenarios = load_scenarios(str(scenario_path)) if scenario_path.exists() else generate_eval_scenarios(env, args.episodes, cfg.get("seed", 0))
    save_scenarios(scenarios, str(scenario_path))
    return scenarios, ""


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _summary(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["policy"], []).append(float(row["negative_return"]))
    dn = sum(grouped.get("do_nothing", [0])) / max(1, len(grouped.get("do_nothing", [])))
    agent_keys = [key for key in grouped if key not in {"do_nothing", "one_step_oracle"}]
    agent_values = grouped.get(agent_keys[0], [0]) if agent_keys else [0]
    agent = sum(agent_values) / max(1, len(agent_values))
    oracle = sum(grouped.get("one_step_oracle", [0])) / max(1, len(grouped.get("one_step_oracle", [])))
    return {
        "do_nothing_mean_negative_return": dn,
        "ppo_agent_mean_negative_return": agent,
        "oracle_mean_negative_return": oracle,
        "oracle_gap": dn - oracle,
        "agent_gap_vs_do_nothing": dn - agent,
    }


if __name__ == "__main__":
    main()
