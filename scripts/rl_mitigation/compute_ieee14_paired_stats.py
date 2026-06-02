from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ._common import ROOT
from rl_mitigation.evaluation.paired_stats import paired_metric_stats


DEFAULT_COMPARISONS = [
    ("ppo_do_nothing_init", "do_nothing"),
    ("ppo_oracle_bc_init", "do_nothing"),
    ("oracle_bc_positive_only", "do_nothing"),
    ("oracle_bc_full", "do_nothing"),
    ("safe_oracle_bc_full", "do_nothing"),
    ("one_step_oracle", "do_nothing"),
    ("ppo_oracle_bc_init", "ppo_do_nothing_init"),
    ("safe_oracle_bc_full", "oracle_bc_full"),
    ("oracle_bc_full", "oracle_bc_positive_only"),
]
DEFAULT_METRICS = ["negative_return", "num_generations", "num_line_outages", "load_shed_MW"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-dir", default="results/rl_mitigation/ieee14/eval")
    parser.add_argument("--split", default="test")
    parser.add_argument("--eval-mode", choices=["deterministic", "stochastic"], default="deterministic")
    args = parser.parse_args()
    eval_dir = ROOT / args.eval_dir
    rows = _load_eval_rows(eval_dir, args.split, args.eval_mode)
    stats = []
    policies = {row["policy"] for row in rows}
    for policy_a, policy_b in DEFAULT_COMPARISONS:
        if policy_a not in policies or policy_b not in policies:
            continue
        for metric in DEFAULT_METRICS:
            stats.append(paired_metric_stats(rows, policy_a, policy_b, metric))
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "stats"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "paired_policy_comparison.csv"
    _write_csv(stats, csv_path)
    _write_md(stats, out_dir / "paired_policy_comparison.md")
    print(f"Paired stats written to {csv_path}")


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


def _write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_md(rows, path):
    lines = [
        "# IEEE14 Paired Policy Comparison",
        "",
        "All comparisons are paired by identical test scenario_id. Lower values are better for negative_return, num_generations, num_line_outages, and load_shed_MW.",
        "",
    ]
    if not rows:
        lines.append("No paired comparisons were available.")
    for row in rows:
        conclusion = {
            "policy_a_better": "improved",
            "policy_a_worse": "worse",
            "no_clear_difference": "indistinguishable",
        }.get(row.get("direction"), "indistinguishable")
        lines.append(
            f"- {row['policy_a']} vs {row['policy_b']} on {row['metric']}: "
            f"mean_diff={float(row['mean_diff']):.4f}, CI=[{float(row['bootstrap_ci_low']):.4f}, {float(row['bootstrap_ci_high']):.4f}], "
            f"direction={row.get('direction')}, improved_ratio={float(row['improved_ratio']):.3f}, "
            f"worse_ratio={float(row['worse_ratio']):.3f} ({conclusion})."
        )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
