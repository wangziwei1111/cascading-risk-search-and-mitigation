from __future__ import annotations

import argparse
import csv
import json
from statistics import mean

import numpy as np

from ._common import ROOT, load_config, make_ieee14_env_from_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--scales", default="1.05,1.10,1.15,1.20,1.30")
    args = parser.parse_args()
    base_cfg = load_config(args.config)
    rows = []
    for scale in [float(x) for x in args.scales.split(",")]:
        cfg = json.loads(json.dumps(base_cfg))
        cfg.setdefault("powerflow", {})["rate_a_mode"] = "scaled_from_base_flow"
        cfg["powerflow"]["rate_a_scale"] = scale
        env = make_ieee14_env_from_config(cfg)
        episode_rows = [_run_do_nothing_episode(env, seed=i) for i in range(args.episodes)]
        rows.append(_summarize(scale, episode_rows))
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


if __name__ == "__main__":
    main()
