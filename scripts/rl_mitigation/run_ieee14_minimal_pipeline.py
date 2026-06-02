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
        [sys.executable, "-m", "scripts.rl_mitigation.calibrate_ieee14_cascade_scenarios", "--config", args.config, "--episodes", str(args.episodes), "--include-action-scan"],
        [sys.executable, "-m", "scripts.rl_mitigation.evaluate_policy", "--case", "ieee14", "--episodes", str(args.episodes), "--without-agent", "--config", args.config, "--eval-mode", "deterministic"],
        [sys.executable, "-m", "scripts.rl_mitigation.scan_ieee14_action_values", "--config", args.config, "--episodes", str(args.episodes)],
        [sys.executable, "-m", "scripts.rl_mitigation.pretrain_do_nothing", "--case", "ieee14", "--config", args.config],
        [sys.executable, "-m", "scripts.rl_mitigation.train_ppo", "--case", "ieee14", "--config", args.config, "--smoke", "--steps", str(args.smoke_steps)],
        [sys.executable, "-m", "scripts.rl_mitigation.diagnose_policy_actions", "--config", args.config, "--episodes", str(args.episodes)],
        [sys.executable, "-m", "scripts.rl_mitigation.evaluate_policy", "--case", "ieee14", "--episodes", str(args.episodes), "--with-agent", "--without-agent", "--config", args.config, "--eval-mode", "deterministic"],
        [sys.executable, "-m", "scripts.rl_mitigation.evaluate_policy", "--case", "ieee14", "--episodes", str(args.episodes), "--with-agent", "--without-agent", "--config", args.config, "--eval-mode", "stochastic"],
        [sys.executable, "-m", "scripts.rl_mitigation.evaluate_oracle_policy", "--config", args.config, "--episodes", str(args.episodes), "--eval-mode", "stochastic"],
        [sys.executable, "-m", "scripts.rl_mitigation.list_high_risk_ieee14_scenarios", "--config", args.config, "--top-k", "50"],
        [sys.executable, "-m", "scripts.rl_mitigation.make_figures", "--case", "ieee14", "--config", args.config],
        [sys.executable, "-m", "scripts.rl_mitigation.export_ieee14_thesis_tables"],
        [sys.executable, "-m", "scripts.rl_mitigation.check_ieee14_results_integrity"],
    ]
    for cmd in commands:
        subprocess.run(cmd, cwd=ROOT, check=True)
    _write_report(args, started)


def _write_report(args, started):
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    cfg = load_config(args.config)
    eval_rows = _read_csv(base / "eval" / f"eval_before_after_{args.episodes}.csv")
    oracle_rows = _read_csv(base / "eval" / f"eval_do_nothing_agent_oracle_{args.episodes}.csv")
    action_summary = _read_json(base / "action_value_scan" / "action_value_summary.json")
    policy_summary = _read_json(base / "diagnostics" / "policy_action_summary.json")
    high_risk = _read_csv(base / "high_risk" / "high_risk_scenarios_top50.csv")[:5]
    grouped = {p: [r for r in eval_rows if r["policy"] == p] for p in ["do_nothing", "agent"]}
    oracle_grouped = {p: [r for r in oracle_rows if r["policy"] == p] for p in ["do_nothing", "ppo_agent", "one_step_oracle"]}
    dn_mean = mean(float(r["negative_return"]) for r in grouped["do_nothing"])
    agent_mean = mean(float(r["negative_return"]) for r in grouped["agent"])
    oracle_mean = mean(float(r["negative_return"]) for r in oracle_grouped["one_step_oracle"])
    agent_actions = mean(float(r["num_proactive_actions"]) for r in grouped["agent"])

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
        "## 关键诊断结论",
        f"- action scan 可改善场景比例: {action_summary.get('better_action_ratio', 0.0):.4f}",
        f"- action scan 平均最佳改善量: {action_summary.get('mean_best_improvement', 0.0):.4f}",
        f"- PPO agent 主动断线次数均值: {agent_actions:.4f}",
        f"- PPO argmax 为 do-nothing 的比例: {policy_summary.get('argmax_do_nothing_ratio', 0.0):.4f}",
        f"- do-nothing / PPO / one-step oracle 平均 negative_return: {dn_mean:.4f} / {agent_mean:.4f} / {oracle_mean:.4f}",
        _conclusion(dn_mean, agent_mean, oracle_mean, agent_actions, action_summary),
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
        f"- agent 平均主动断线次数: {agent_actions:.4f}",
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
        "- `results/rl_mitigation/ieee14/figures/fig_action_improvement_distribution.png`",
        "- `results/rl_mitigation/ieee14/figures/fig_oracle_vs_do_nothing_vs_agent_survival.png`",
        "- `results/rl_mitigation/ieee14/figures/fig_policy_action_probability.png`",
        "",
        "## 复现边界",
        "本实验基于 PYPOWER IEEE14、surrogate chronics 和文档化容量校准，只用于检验 IEEE14 缓解模块可信度；不得声称精确复现原论文 Figure 7/8 数值。",
    ])
    out = base / "reports" / "ieee14_minimal_pipeline_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Pipeline report written to {out}")


def _read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _conclusion(dn_mean: float, agent_mean: float, oracle_mean: float, agent_actions: float, action_summary: dict) -> str:
    if action_summary.get("better_action_ratio", 0.0) <= 1e-9:
        return "- 结论: 当前校准下没有发现明显优于 do-nothing 的单步主动断线动作，PPO 学不到改善主要是环境/校准本身的问题。"
    if agent_actions <= 1e-9 or agent_mean >= dn_mean - 1e-9:
        return "- 结论: 单步 oracle 证明存在可改善动作，但当前 PPO 仍接近 do-nothing；应优先检查探索、预训练偏置和奖励尺度。"
    return "- 结论: 当前 PPO 已产生非零主动动作，并相对 do-nothing 有改善；one-step oracle 仅作为诊断上界。"


if __name__ == "__main__":
    main()
