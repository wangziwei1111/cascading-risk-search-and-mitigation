from __future__ import annotations

import argparse
import csv
import json

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.action_value import run_episode_with_first_action
from rl_mitigation.evaluation.evaluate_agent import run_policy
from rl_mitigation.evaluation.oracle_policy import choose_best_initial_action
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios, load_scenarios, save_scenarios
from rl_mitigation.evaluation.evaluate_agent import save_eval_csv
from rl_mitigation.rl.ppo_clip import load_checkpoint
from rl_mitigation.rl.torch_networks import TorchActorCritic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--eval-mode", choices=["deterministic", "stochastic"], default="deterministic")
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_ieee14_env_from_config(cfg)
    eval_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval"
    scenario_path = eval_dir / f"eval_scenarios_seed{cfg.get('seed', 0)}_episodes{args.episodes}.json"
    scenarios = load_scenarios(str(scenario_path)) if scenario_path.exists() else generate_eval_scenarios(env, args.episodes, cfg.get("seed", 0))
    save_scenarios(scenarios, str(scenario_path))
    rows = []
    ckpt = ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints" / "latest.pt"
    model = load_checkpoint(str(ckpt)) if ckpt.exists() else TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    agent_rows = run_policy(env, args.episodes, model=model, with_agent=True, scenarios=scenarios, eval_mode=args.eval_mode)
    for row in agent_rows:
        row["policy"] = "ppo_agent"
    rows.extend(agent_rows)
    for scenario in scenarios[:args.episodes]:
        dn = run_episode_with_first_action(env, scenario, 0)
        dn["policy"] = "do_nothing"
        rows.append(dn)
        _, best = choose_best_initial_action(env, scenario)
        best["policy"] = "one_step_oracle"
        rows.append(best)
    out = eval_dir / f"eval_do_nothing_agent_oracle_{args.episodes}.csv"
    save_eval_csv(rows, str(out))
    summary = _summary(rows)
    with open(eval_dir / f"oracle_summary_{args.episodes}.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Oracle evaluation written to {out}; oracle_gap={summary['oracle_gap']:.4f}")


def _summary(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["policy"], []).append(float(row["negative_return"]))
    dn = sum(grouped.get("do_nothing", [0])) / max(1, len(grouped.get("do_nothing", [])))
    agent = sum(grouped.get("ppo_agent", [0])) / max(1, len(grouped.get("ppo_agent", [])))
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
