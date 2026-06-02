from __future__ import annotations

import argparse
import json

import yaml

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.evaluate_agent import run_policy, save_eval_csv
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios, save_scenarios
from rl_mitigation.rl.ppo_clip import load_checkpoint
from rl_mitigation.rl.torch_networks import TorchActorCritic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--with-agent", action="store_true")
    parser.add_argument("--without-agent", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    args = parser.parse_args()
    with open(ROOT / args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    episodes = min(args.episodes, 10) if args.smoke else args.episodes
    env = CascadeMitigationEnv(
        make_ieee14_case(),
        seed=cfg.get("seed", 0),
        alpha=cfg.get("alpha", 0.1),
        max_generations=cfg.get("max_generations", 10),
        use_action_mask=cfg.get("ppo", {}).get("use_action_mask", True),
        backend=cfg.get("backend", "pypower_ac"),
    )
    model = TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    policy_path = ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints" / "latest.pt"
    if policy_path.exists():
        model = load_checkpoint(str(policy_path))
    scenario_path = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval" / f"eval_scenarios_seed{cfg.get('seed', 0)}_episodes{episodes}.json"
    scenarios = generate_eval_scenarios(env, episodes=episodes, seed=cfg.get("seed", 0))
    save_scenarios(scenarios, str(scenario_path))
    rows = []
    if args.with_agent or not args.without_agent:
        rows.extend(run_policy(env, episodes=episodes, model=model, with_agent=True, scenarios=scenarios))
    if args.without_agent or not args.with_agent:
        rows.extend(run_policy(env, episodes=episodes, model=model, with_agent=False, scenarios=scenarios))
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval"
    out = out_dir / ("eval_10_smoke.csv" if args.smoke else f"eval_before_after_{episodes}.csv")
    save_eval_csv(rows, str(out))
    summary = {
        "episodes": episodes,
        "policies": sorted(set(row["policy"] for row in rows)),
        "mean_negative_return": sum(row["negative_return"] for row in rows) / max(1, len(rows)),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / ("metrics_summary_10.json" if args.smoke else f"metrics_summary_{episodes}.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Evaluation rows written to {out}")


if __name__ == "__main__":
    main()
