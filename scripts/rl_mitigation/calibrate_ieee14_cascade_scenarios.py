from __future__ import annotations

import argparse
import csv
import json
from statistics import mean

import numpy as np

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.action_value import scan_scenario_actions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--scales", default="1.05,1.10,1.15,1.20,1.30")
    parser.add_argument("--include-action-scan", action="store_true")
    args = parser.parse_args()
    base_cfg = load_config(args.config)
    rows = []
    for scale in [float(x) for x in args.scales.split(",")]:
        cfg = json.loads(json.dumps(base_cfg))
        cfg.setdefault("powerflow", {})["rate_a_mode"] = "scaled_from_base_flow"
        cfg["powerflow"]["rate_a_scale"] = scale
        env = make_ieee14_env_from_config(cfg)
        episode_rows = [_run_do_nothing_episode(env, seed=i) for i in range(args.episodes)]
        summary_row = _summarize(scale, episode_rows)
        if args.include_action_scan:
            summary_row.update(_action_scan_summary(env, args.episodes))
        rows.append(summary_row)
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "calibration"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "cascade_scenario_stats.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    recommended = min(rows, key=lambda r: abs(r["has_random_trip_ratio"] - 0.35) + abs(r["cascade_stop_immediately_ratio"] - 0.45))
    summary = {"recommended_rate_a_scale": recommended["rate_a_scale"], "candidates": rows}
    with open(out_dir / "cascade_scenario_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    if args.include_action_scan:
        with open(out_dir / "cascade_action_calibration_summary.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(f"Calibration written to {out_dir}; recommended rate_a_scale={recommended['rate_a_scale']}")


def _run_do_nothing_episode(env, seed: int) -> dict:
    _, info = env.reset(seed=seed)
    done = False
    total = 0.0
    last_info = info
    while not done:
        _, reward, done, _, last_info = env.step(0)
        total += float(reward)
    trace = last_info.get("cascade_trace", [])
    return {
        "negative_return": -total,
        "num_generations": last_info.get("num_generations", 0),
        "num_line_outages": last_info.get("num_line_outages", 0),
        "load_shed_MW": last_info.get("load_shed_MW", 0.0),
        "pf_failed": last_info.get("pf_failed", False),
        "has_overload": any(row.get("overloaded_lines") for row in trace),
        "has_random_trip": any(row.get("random_trips") for row in trace),
        "stopped_immediately": last_info.get("num_generations", 0) <= 1 and not any(row.get("random_trips") for row in trace),
    }


def _summarize(scale: float, rows: list[dict]) -> dict:
    neg = [row["negative_return"] for row in rows]
    return {
        "rate_a_scale": scale,
        "num_scenarios": len(rows),
        "cascade_stop_immediately_ratio": mean(row["stopped_immediately"] for row in rows),
        "has_overload_ratio": mean(row["has_overload"] for row in rows),
        "has_random_trip_ratio": mean(row["has_random_trip"] for row in rows),
        "pf_failed_ratio": mean(row["pf_failed"] for row in rows),
        "mean_num_generations": mean(row["num_generations"] for row in rows),
        "mean_num_line_outages": mean(row["num_line_outages"] for row in rows),
        "mean_load_shed_MW": mean(row["load_shed_MW"] for row in rows),
        "negative_return_mean": mean(neg),
        "negative_return_p95": float(np.percentile(neg, 95)),
    }


def _action_scan_summary(env, episodes: int) -> dict:
    improvements = []
    dn_values = []
    oracle_values = []
    for seed in range(episodes):
        _, info = env.reset(seed=seed)
        scenario = {
            "scenario_id": seed,
            "seed": seed,
            "chronic_index": info["chronic_index"],
            "load_scale": info["load_scale"],
            "gen_scale": info["gen_scale"],
            "initial_outages": info["initial_outages"],
            "initial_outage_type": info["initial_outage_type"],
            "initial_outage_order": info["initial_outage_order"],
            "initial_outage_mode": info["initial_outage_mode"],
        }
        rows = scan_scenario_actions(env, scenario)
        dn = next(row for row in rows if int(row["action"]) == 0)
        valid = [row for row in rows if row.get("is_valid_action")]
        best = min(valid or rows, key=lambda r: float(r["negative_return"]))
        improvement = float(dn["negative_return"]) - float(best["negative_return"])
        improvements.append(improvement)
        dn_values.append(float(dn["negative_return"]))
        oracle_values.append(float(best["negative_return"]))
    return {
        "improvable_scenario_ratio": mean(x > 1e-9 for x in improvements),
        "mean_best_improvement": mean(improvements),
        "oracle_mean_negative_return": mean(oracle_values),
        "do_nothing_mean_negative_return": mean(dn_values),
        "oracle_gap": mean(dn_values) - mean(oracle_values),
    }


if __name__ == "__main__":
    main()
