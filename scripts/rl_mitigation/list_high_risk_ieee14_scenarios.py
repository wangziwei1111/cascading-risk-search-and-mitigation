from __future__ import annotations

import argparse
import csv
import json

from ._common import ROOT, load_config, make_ieee14_env_from_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--episodes", type=int, default=200)
    args = parser.parse_args()
    env = make_ieee14_env_from_config(load_config(args.config))
    rows = []
    for idx in range(args.episodes):
        _, info = env.reset(seed=idx)
        done = False
        total = 0.0
        last_info = info
        while not done:
            _, reward, done, _, last_info = env.step(0)
            total += float(reward)
        rows.append({
            "initial_outages": ",".join(str(x) for x in last_info["initial_outages"]),
            "initial_outage_type": last_info["initial_outage_type"],
            "negative_return": -total,
            "num_generations": last_info["num_generations"],
            "num_line_outages": last_info["num_line_outages"],
            "load_shed_MW": last_info["load_shed_MW"],
            "load_shed_ratio": last_info["load_shed_ratio"],
            "pf_failed": last_info["pf_failed"],
            "cascade_trace_json": json.dumps(last_info["cascade_trace"], ensure_ascii=False),
        })
    rows.sort(key=lambda r: (r["negative_return"], r["num_generations"], r["num_line_outages"], r["load_shed_MW"]), reverse=True)
    out = ROOT / "results" / "rl_mitigation" / "ieee14" / "high_risk" / f"high_risk_scenarios_top{args.top_k}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["rank", "initial_outages", "initial_outage_type", "negative_return", "num_generations", "num_line_outages", "load_shed_MW", "load_shed_ratio", "pf_failed", "cascade_trace_json"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rank, row in enumerate(rows[:args.top_k], start=1):
            writer.writerow({"rank": rank, **row})
    print(f"High-risk scenarios written to {out}")


if __name__ == "__main__":
    main()
