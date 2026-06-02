from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

from ._common import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--train-steps", type=int, default=20000)
    parser.add_argument("--eval-episodes", type=int, default=100)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    _run([sys.executable, "-m", "scripts.rl_mitigation.generate_ieee14_scenario_splits", "--config", args.config, "--train", "300", "--val", "100", "--test", "100"])
    for split in ["train", "val", "test"]:
        _run([sys.executable, "-m", "scripts.rl_mitigation.scan_ieee14_action_values", "--config", args.config, "--split", split])
    _run([sys.executable, "-m", "scripts.rl_mitigation.pretrain_oracle_bc", "--config", args.config, "--episodes", "300"])
    ablation_cmd = [
        sys.executable, "-m", "scripts.rl_mitigation.run_ieee14_training_ablation",
        "--config", args.config, "--train-steps", str(args.train_steps), "--eval-episodes", str(args.eval_episodes),
        *(("--smoke",) if args.smoke else ()),
    ]
    _run(ablation_cmd)
    _run([sys.executable, "-m", "scripts.rl_mitigation.compute_ieee14_paired_stats"])
    _run([sys.executable, "-m", "scripts.rl_mitigation.analyze_improvable_subset"])
    _run([sys.executable, "-m", "scripts.rl_mitigation.make_figures", "--case", "ieee14", "--config", args.config])
    _write_report(args)


def _write_report(args):
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    action = _read_json(base / "action_value_scan" / "test_action_value_summary.json")
    ablation = _read_csv(base / "ablation" / "training_ablation_summary.csv")
    paired = _read_csv(base / "stats" / "paired_policy_comparison.csv")
    subset = _read_csv(base / "analysis" / "improvable_subset_summary.csv")
    best_rows = [row for row in ablation if row["eval_mode"] == "deterministic"]
    lines = [
        "# IEEE14 Learning Pipeline Report",
        "",
        "## Required Answers",
        f"1. 环境中是否存在可缓解空间：是。test better_action_ratio={float(action.get('better_action_ratio', 0.0)):.4f}。",
        f"2. one-step oracle 改善幅度：test mean_best_improvement={float(action.get('mean_best_improvement', 0.0)):.4f}。",
        "3. random init PPO 是否学到：见 training_ablation_summary.csv 中 ppo_random_init。",
        "4. do-nothing init PPO 是否学到：见 training_ablation_summary.csv 中 ppo_do_nothing_init。",
        "5. oracle BC init PPO 是否学到：见 training_ablation_summary.csv 中 ppo_oracle_bc_init。",
        "6. 改善主要出现在哪些场景子集：见 improvable_subset_summary.csv 和 improvable_subset_report.md。",
        "7. 是否可以写 RL 策略具有缓解效果：只能在 paired stats 和 test split 支持时谨慎表述；oracle BC 属于增强实验。",
        "8. 原论文机制复现：MDP、action mask、PPO、N-1/N-2、PYPOWER IEEE14；诊断增强：action scan、one-step oracle、oracle BC、subset analysis、training ablation。",
        "",
        "## Deterministic Test Summary",
    ]
    for row in best_rows:
        lines.append(
            f"- {row['variant']}: mean_negative_return={float(row['mean_negative_return']):.4f}, "
            f"improvement_vs_do_nothing={float(row['mean_improvement_vs_do_nothing']):.4f}, "
            f"argmax_do_nothing_ratio={float(row['argmax_do_nothing_ratio']):.4f}"
        )
    lines.extend(["", "## Paired Stats Snapshot"])
    for row in paired[:8]:
        lines.append(
            f"- {row['policy_a']} vs {row['policy_b']} / {row['metric']}: "
            f"mean_diff={float(row['mean_diff']):.4f}, CI=[{float(row['bootstrap_ci_low']):.4f}, {float(row['bootstrap_ci_high']):.4f}], "
            f"improved_ratio={float(row['improved_ratio']):.3f}"
        )
    lines.extend(["", "## Subset Snapshot"])
    for row in subset[:12]:
        lines.append(
            f"- {row['subset']} / {row['policy']}: mean_negative_return={float(row['mean_negative_return']):.4f}, "
            f"mean_improvement_vs_do_nothing={float(row['mean_improvement_vs_do_nothing']):.4f}"
        )
    out = base / "reports" / "ieee14_learning_pipeline_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Learning pipeline report written to {out}")


def _run(cmd):
    subprocess.run(cmd, cwd=ROOT, check=True)


def _read_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read_csv(path: Path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    main()
