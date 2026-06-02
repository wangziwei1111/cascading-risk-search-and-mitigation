from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.action_value import scan_scenario_actions
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios, load_scenarios, save_scenarios


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_ieee14_env_from_config(cfg)
    eval_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval"
    scenario_path = eval_dir / f"eval_scenarios_seed{cfg.get('seed', 0)}_episodes{args.episodes}.json"
    scenarios = load_scenarios(str(scenario_path)) if scenario_path.exists() else generate_eval_scenarios(env, args.episodes, cfg.get("seed", 0))
    save_scenarios(scenarios, str(scenario_path))
    rows = []
    for scenario in scenarios[:args.episodes]:
        rows.extend(scan_scenario_actions(env, scenario))
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "action_value_scan"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"action_value_scan_{args.episodes}.csv"
    _write_csv(rows, csv_path)
    summary = _summarize(rows)
    with open(out_dir / "action_value_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    _plot_improvements(summary["scenario_improvements"], out_dir)
    _plot_best_frequency(summary["top10_best_actions"], out_dir)
    print(f"Action value scan written to {out_dir}; better_action_ratio={summary['better_action_ratio']:.3f}")


def _write_csv(rows, path):
    fields = [
        "scenario_id", "initial_outages", "initial_outage_type", "initial_outage_order",
        "chronic_index", "load_scale", "gen_scale", "action", "action_type",
        "action_line", "is_valid_action", "episode_return", "negative_return",
        "num_generations", "num_line_outages", "load_shed_MW", "load_shed_ratio",
        "num_proactive_actions", "num_invalid_actions", "pf_failed", "cascade_trace_json",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _summarize(rows):
    by_id = {}
    for row in rows:
        by_id.setdefault(str(row["scenario_id"]), []).append(row)
    improvements = []
    best_actions = []
    for sid, cur in by_id.items():
        dn = next(row for row in cur if int(row["action"]) == 0)
        valid = [row for row in cur if row.get("is_valid_action")]
        best = min(valid or cur, key=lambda r: float(r["negative_return"]))
        imp = float(dn["negative_return"]) - float(best["negative_return"])
        improvements.append({"scenario_id": sid, "improvement": imp, "best_action": int(best["action"]), "do_nothing_negative_return": float(dn["negative_return"]), "best_negative_return": float(best["negative_return"])})
        best_actions.append(int(best["action"]))
    positive = [row for row in improvements if row["improvement"] > 1e-9]
    imps = [row["improvement"] for row in improvements]
    freq = {}
    for action in best_actions:
        freq[action] = freq.get(action, 0) + 1
    return {
        "num_scenarios": len(by_id),
        "num_actions_per_scenario": len(rows) // max(1, len(by_id)),
        "num_scenarios_with_better_action_than_do_nothing": len(positive),
        "better_action_ratio": len(positive) / max(1, len(by_id)),
        "mean_best_improvement": float(np.mean(imps)),
        "median_best_improvement": float(np.median(imps)),
        "max_best_improvement": float(np.max(imps)),
        "num_scenarios_where_do_nothing_is_best": sum(1 for row in improvements if row["best_action"] == 0),
        "top10_improvable_scenarios": sorted(positive, key=lambda r: r["improvement"], reverse=True)[:10],
        "top10_best_actions": sorted([{"action": k, "count": v} for k, v in freq.items()], key=lambda r: r["count"], reverse=True)[:10],
        "scenario_improvements": improvements,
    }


def _plot_improvements(improvements, out_dir):
    vals = [row["improvement"] for row in improvements]
    plt.figure(figsize=(6, 4), facecolor="white")
    plt.hist(vals, bins=20)
    plt.xlabel("Best action improvement over do-nothing")
    plt.ylabel("Scenario count")
    plt.tight_layout()
    plt.savefig(out_dir / "fig_action_improvement_distribution.png", dpi=200)
    plt.savefig(out_dir / "fig_action_improvement_distribution.pdf")
    plt.close()


def _plot_best_frequency(actions, out_dir):
    plt.figure(figsize=(6, 4), facecolor="white")
    plt.bar([str(row["action"]) for row in actions], [row["count"] for row in actions])
    plt.xlabel("Best initial action")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(out_dir / "fig_best_action_frequency.png", dpi=200)
    plt.savefig(out_dir / "fig_best_action_frequency.pdf")
    plt.close()


if __name__ == "__main__":
    main()
