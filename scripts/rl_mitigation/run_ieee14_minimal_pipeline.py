from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean

from ._common import ROOT, load_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--smoke-steps", type=int, default=2048)
    args = parser.parse_args()
    started = datetime.now()
    commands = [
        ["python", "-m", "scripts.rl_mitigation.calibrate_ieee14_cascade_scenarios", "--config", args.config],
        ["python", "-m", "scripts.rl_mitigation.pretrain_do_nothing", "--case", "ieee14", "--config", args.config],
        ["python", "-m", "scripts.rl_mitigation.train_ppo", "--case", "ieee14", "--config", args.config, "--smoke", "--steps", str(args.smoke_steps)],
        ["python", "-m", "scripts.rl_mitigation.evaluate_policy", "--case", "ieee14", "--episodes", str(args.episodes), "--with-agent", "--without-agent", "--config", args.config],
        ["python", "-m", "scripts.rl_mitigation.list_high_risk_ieee14_scenarios", "--config", args.config, "--top-k", "50"],
        ["python", "-m", "scripts.rl_mitigation.make_figures", "--case", "ieee14"],
    ]
    for cmd in commands:
        subprocess.run(cmd, cwd=ROOT, check=True)
    _write_report(args, started)


def _write_report(args, started):
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    cfg = load_config(args.config)
    eval_rows = _read_csv(base / "eval" / f"eval_before_after_{args.episodes}.csv")
    high_risk = _read_csv(base / "high_risk" / "high_risk_scenarios_top50.csv")[:5]
    grouped = {p: [r for r in eval_rows if r["policy"] == p] for p in ["do_nothing", "agent"]}
    lines = [
        "# IEEE14 Minimal Pipeline Report",
        "",
        f"- 运行时间: {started.isoformat()} -> {datetime.now().isoformat()}",
        f"- 配置文件: `{args.config}`",
        f"- backend: `{cfg.get('backend')}`",
        f"- rate_a_mode: `{cfg.get('powerflow', {}).get('rate_a_mode')}`",
        f"- rate_a_scale: `{cfg.get('powerflow', {}).get('rate_a_scale')}`",
        f"- 初始故障模式: `{cfg.get('initial_outages', {}).get('mode')}`",
        f"- 评估 episodes: `{args.episodes}`",
        "",
        "## Before/After Summary",
    ]
    for policy, rows in grouped.items():
        lines.extend([
            f"- {policy} 平均 negative_return: {mean(float(r['negative_return']) for r in rows):.4f}",
            f"- {policy} 平均 num_generations: {mean(float(r['num_generations']) for r in rows):.4f}",
            f"- {policy} 平均 num_line_outages: {mean(float(r['num_line_outages']) for r in rows):.4f}",
            f"- {policy} 平均 load_shed_MW: {mean(float(r['load_shed_MW']) for r in rows):.4f}",
        ])
    lines.extend([
        f"- agent 平均主动断线次数: {mean(float(r['num_proactive_actions']) for r in grouped['agent']):.4f}",
        f"- agent 平均无效动作次数: {mean(float(r['num_invalid_actions']) for r in grouped['agent']):.4f}",
        "",
        "## 高风险场景 Top5",
    ])
    for row in high_risk:
        lines.append(f"- rank {row['rank']}: outages={row['initial_outages']}, type={row['initial_outage_type']}, negative_return={row['negative_return']}")
    lines.extend([
        "",
        "## 图表路径",
        "- `results/rl_mitigation/ieee14/figures/fig7_learning_curves_gridsearch.png`",
        "- `results/rl_mitigation/ieee14/figures/fig_ieee14_survival_negative_return_100.png`",
        "",
        "## 复现边界",
        "本实验基于 PYPOWER IEEE14、surrogate chronics 和文档化容量校准，不能声称完全复现论文原始 Figure 7/8 数值。",
    ])
    out = base / "reports" / "ieee14_minimal_pipeline_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Pipeline report written to {out}")


def _read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    main()
