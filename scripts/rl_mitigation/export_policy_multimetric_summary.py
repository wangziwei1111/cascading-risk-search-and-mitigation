from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean

import numpy as np

from ._common import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-dir", default="results/rl_mitigation/ieee14/eval")
    parser.add_argument("--split", default="test")
    parser.add_argument("--eval-mode", choices=["deterministic", "stochastic"], default="deterministic")
    args = parser.parse_args()
    rows = _load_rows(ROOT / args.eval_dir, args.split, args.eval_mode)
    out_rows = [_summary(rows, policy, args.split, args.eval_mode) for policy in sorted({row["policy"] for row in rows})]
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_rows, out_dir / "table_policy_multi_metric_test_summary.csv")
    print(f"Multi-metric summary written to {out_dir}")


def _load_rows(eval_dir: Path, split: str, eval_mode: str):
    rows = []
    for path in sorted(eval_dir.glob(f"{split}_eval_*.csv")):
        if "before_after" in path.name or "do_nothing_agent_oracle" in path.name:
            continue
        if any(mode in path.name for mode in ["deterministic", "stochastic"]) and eval_mode not in path.name:
            continue
        with open(path, newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
    return rows


def _summary(rows, policy, split, eval_mode):
    cur = [row for row in rows if row["policy"] == policy]
    neg = [float(row["negative_return"]) for row in cur]
    return {
        "policy": policy,
        "split": split,
        "eval_mode": eval_mode,
        "episodes": len(cur),
        "mean_negative_return": mean(neg),
        "p95_negative_return": float(np.percentile(neg, 95)),
        "pf_failed_ratio": mean(str(row["pf_failed"]).lower() == "true" for row in cur),
        "mean_num_generations": mean(float(row["num_generations"]) for row in cur),
        "mean_num_line_outages": mean(float(row["num_line_outages"]) for row in cur),
        "mean_load_shed_MW": mean(float(row["load_shed_MW"]) for row in cur),
        "mean_load_shed_ratio": mean(float(row["load_shed_ratio"]) for row in cur),
        "mean_num_proactive_actions": mean(float(row["num_proactive_actions"]) for row in cur),
        "improved_ratio_negative_return": _paired_ratio(rows, policy, "negative_return"),
        "worse_ratio_negative_return": _paired_ratio(rows, policy, "negative_return", worse=True),
        "improved_ratio_line_outages": _paired_ratio(rows, policy, "num_line_outages"),
        "improved_ratio_load_shed": _paired_ratio(rows, policy, "load_shed_MW"),
    }


def _paired_ratio(rows, policy, metric, worse=False):
    baseline = {str(row["scenario_id"]): row for row in rows if row["policy"] == "do_nothing"}
    cur = [row for row in rows if row["policy"] == policy and str(row["scenario_id"]) in baseline]
    if not cur:
        return 0.0
    diffs = [float(baseline[str(row["scenario_id"])][metric]) - float(row[metric]) for row in cur]
    return mean(x < -1e-9 for x in diffs) if worse else mean(x > 1e-9 for x in diffs)


def _write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
