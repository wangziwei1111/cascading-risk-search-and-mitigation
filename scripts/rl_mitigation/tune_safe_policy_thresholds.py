from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean

import numpy as np

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.evaluate_agent import run_policy
from rl_mitigation.evaluation.paired_stats import paired_improvement_summary
from rl_mitigation.evaluation.safe_policy import load_actor_policy, run_safe_policy
from rl_mitigation.evaluation.scenario_split import SPLIT_SEEDS, load_or_create_scenario_split
from rl_mitigation.rl.torch_networks import TorchActorCritic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--policy-path", default="results/rl_mitigation/ieee14/pretrain/oracle_bc_full_policy.pt")
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_ieee14_env_from_config(cfg)
    scenarios, _ = load_or_create_scenario_split(env, ROOT / "results" / "rl_mitigation" / "ieee14" / "scenarios", "val", 100, SPLIT_SEEDS["val"])
    scenarios = scenarios[:args.episodes]
    model = load_actor_policy(_resolve(args.policy_path))
    baseline = run_policy(env, len(scenarios), model=TorchActorCritic(env.observation_space_shape[0], env.action_space_n), with_agent=False, scenarios=scenarios)
    safe_cfg = cfg.get("safe_policy", {})
    rows = []
    for active in safe_cfg.get("active_prob_grid", [0.35]):
        for margin in safe_cfg.get("margin_grid", [0.05]):
            eval_rows = run_safe_policy(env, scenarios, model, "safe_oracle_bc_full", active, margin)
            combined = baseline + eval_rows
            row = _summary(eval_rows, combined, active, margin)
            rows.append(row)
    selected = sorted(rows, key=lambda r: (float(r["mean_negative_return"]), float(r["mean_num_proactive_actions"])))[0]
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "ablation"
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(rows, out_dir / "safe_policy_threshold_tuning.csv")
    with open(out_dir / "safe_policy_threshold_selected.json", "w", encoding="utf-8") as f:
        json.dump({
            "active_prob_threshold": float(selected["active_prob_threshold"]),
            "margin_threshold": float(selected["margin_threshold"]),
            "mean_negative_return": float(selected["mean_negative_return"]),
            "mean_num_proactive_actions": float(selected["mean_num_proactive_actions"]),
            "worse_scenario_ratio_vs_do_nothing": float(selected["worse_scenario_ratio_vs_do_nothing"]),
        }, f, indent=2)
    print(f"Safe policy tuning written to {out_dir}; selected active={selected['active_prob_threshold']} margin={selected['margin_threshold']}")


def _summary(rows, combined, active, margin):
    neg = [float(row["negative_return"]) for row in rows]
    paired = paired_improvement_summary(combined, "safe_oracle_bc_full", "do_nothing")
    return {
        "active_prob_threshold": active,
        "margin_threshold": margin,
        "episodes": len(rows),
        "mean_negative_return": mean(neg),
        "p95_negative_return": float(np.percentile(neg, 95)),
        "mean_num_proactive_actions": mean(float(row["num_proactive_actions"]) for row in rows),
        "mean_num_line_outages": mean(float(row["num_line_outages"]) for row in rows),
        "mean_load_shed_MW": mean(float(row["load_shed_MW"]) for row in rows),
        "worse_scenario_ratio_vs_do_nothing": paired["worse_scenario_ratio_vs_do_nothing"],
        "improved_scenario_ratio_vs_do_nothing": paired["improved_scenario_ratio_vs_do_nothing"],
    }


def _write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _resolve(path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
