from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean

from ._common import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="test")
    parser.add_argument("--eval-dir", default="results/rl_mitigation/ieee14/eval")
    parser.add_argument("--summary-file", default="results/rl_mitigation/ieee14/action_value_scan/test_action_value_summary.json")
    parser.add_argument("--eval-mode", choices=["deterministic", "stochastic"], default="deterministic")
    args = parser.parse_args()
    rows = _load_eval_rows(ROOT / args.eval_dir, args.split, args.eval_mode)
    with open(ROOT / args.summary_file, encoding="utf-8") as f:
        action_summary = json.load(f)
    improvable = set(str(x) for x in action_summary.get("improvable_scenario_ids", []))
    all_ids = {str(row["scenario_id"]) for row in rows}
    non_improvable = all_ids - improvable
    dn = [row for row in rows if row["policy"] == "do_nothing"]
    high_risk_cut = sorted(float(row["negative_return"]) for row in dn)[max(0, int(len(dn) * 0.9) - 1)] if dn else 0.0
    high_risk = {str(row["scenario_id"]) for row in dn if float(row["negative_return"]) >= high_risk_cut}
    subsets = {
        "all_test": all_ids,
        "improvable": improvable,
        "non_improvable": non_improvable,
        "high_risk_top10pct": high_risk,
    }
    out_rows = []
    for subset, ids in subsets.items():
        for policy in sorted({row["policy"] for row in rows}):
            cur = [row for row in rows if row["policy"] == policy and str(row["scenario_id"]) in ids]
            if cur:
                out_rows.append(_summary(cur, rows, policy, subset))
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_rows, out_dir / "improvable_subset_summary.csv")
    _write_report(out_rows, out_dir / "improvable_subset_report.md")
    print(f"Improvable subset analysis written to {out_dir}")


def _load_eval_rows(eval_dir: Path, split: str, eval_mode: str) -> list[dict]:
    rows = []
    for path in sorted(eval_dir.glob(f"{split}_eval_*.csv")):
        if "before_after" in path.name or "do_nothing_agent_oracle" in path.name:
            continue
        if any(mode in path.name for mode in ["deterministic", "stochastic"]) and eval_mode not in path.name:
            continue
        with open(path, newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
    return rows


def _summary(cur, all_rows, policy, subset):
    baseline = {str(row["scenario_id"]): row for row in all_rows if row["policy"] == "do_nothing"}
    improvements = [
        float(baseline[str(row["scenario_id"])]["negative_return"]) - float(row["negative_return"])
        for row in cur if str(row["scenario_id"]) in baseline
    ]
    return {
        "policy": policy,
        "subset": subset,
        "episodes": len(cur),
        "mean_negative_return": mean(float(row["negative_return"]) for row in cur),
        "mean_improvement_vs_do_nothing": mean(improvements) if improvements else 0.0,
        "improved_ratio_vs_do_nothing": mean(x > 1e-9 for x in improvements) if improvements else 0.0,
        "mean_num_generations": mean(float(row["num_generations"]) for row in cur),
        "mean_num_line_outages": mean(float(row["num_line_outages"]) for row in cur),
        "mean_load_shed_MW": mean(float(row["load_shed_MW"]) for row in cur),
        "mean_num_proactive_actions": mean(float(row["num_proactive_actions"]) for row in cur),
    }


def _write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(rows, path):
    lines = ["# IEEE14 Improvable Subset Analysis", ""]
    for row in rows:
        lines.append(
            f"- {row['subset']} / {row['policy']}: mean_negative_return={float(row['mean_negative_return']):.4f}, "
            f"mean_improvement_vs_do_nothing={float(row['mean_improvement_vs_do_nothing']):.4f}, "
            f"improved_ratio={float(row['improved_ratio_vs_do_nothing']):.3f}"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
