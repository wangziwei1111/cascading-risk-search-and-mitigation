from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.evaluate_agent import save_eval_csv
from rl_mitigation.evaluation.safe_policy import load_actor_policy, run_actor_policy
from rl_mitigation.evaluation.scenarios import load_scenarios


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--eval-episodes", type=int, default=100)
    args = parser.parse_args()
    episodes = min(args.eval_episodes, 50) if args.smoke else args.eval_episodes
    _ensure_inputs(args.config)
    _run([sys.executable, "-m", "scripts.rl_mitigation.pretrain_oracle_bc", "--config", args.config, "--episodes", "300", "--mode", "full"])
    _run([sys.executable, "-m", "scripts.rl_mitigation.pretrain_oracle_bc", "--config", args.config, "--episodes", "300", "--mode", "positive_only"])
    _run([sys.executable, "-m", "scripts.rl_mitigation.tune_safe_policy_thresholds", "--config", args.config])
    _run([sys.executable, "-m", "scripts.rl_mitigation.evaluate_policy", "--config", args.config, "--split", "test", "--episodes", str(episodes), "--without-agent"])
    _run([sys.executable, "-m", "scripts.rl_mitigation.evaluate_oracle_policy", "--config", args.config, "--split", "test", "--episodes", str(episodes)])
    _eval_ppo_do_nothing(args.config, episodes)
    _eval_actor_policies(args.config, episodes)
    for mode in ["deterministic", "stochastic"]:
        _run([sys.executable, "-m", "scripts.rl_mitigation.evaluate_safe_policy", "--config", args.config, "--split", "test", "--episodes", str(episodes), "--eval-mode", mode])
    _run([sys.executable, "-m", "scripts.rl_mitigation.compute_ieee14_paired_stats", "--eval-mode", "deterministic"])
    _run([sys.executable, "-m", "scripts.rl_mitigation.analyze_improvable_subset", "--eval-mode", "deterministic"])
    _run([sys.executable, "-m", "scripts.rl_mitigation.export_policy_multimetric_summary", "--eval-mode", "deterministic"])
    _run([sys.executable, "-m", "scripts.rl_mitigation.make_figures", "--case", "ieee14"])
    _write_report(args, episodes)


def _ensure_inputs(config):
    _run([sys.executable, "-m", "scripts.rl_mitigation.generate_ieee14_scenario_splits", "--config", config, "--train", "300", "--val", "100", "--test", "100"])
    for split in ["train", "val", "test"]:
        summary = ROOT / "results" / "rl_mitigation" / "ieee14" / "action_value_scan" / f"{split}_action_value_summary.json"
        if not summary.exists():
            _run([sys.executable, "-m", "scripts.rl_mitigation.scan_ieee14_action_values", "--config", config, "--split", split])


def _eval_actor_policies(config, episodes):
    cfg = load_config(config)
    env = make_ieee14_env_from_config(cfg)
    scenarios = load_scenarios(str(ROOT / "results" / "rl_mitigation" / "ieee14" / "scenarios" / "test_scenarios_seed2_episodes100.json"))[:episodes]
    eval_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval"
    policies = [
        ("oracle_bc_positive_only", ROOT / "results" / "rl_mitigation" / "ieee14" / "pretrain" / "oracle_bc_positive_only_policy.pt"),
        ("oracle_bc_full", ROOT / "results" / "rl_mitigation" / "ieee14" / "pretrain" / "oracle_bc_full_policy.pt"),
    ]
    for policy_name, path in policies:
        model = load_actor_policy(path)
        for mode in ["deterministic", "stochastic"]:
            rows = run_actor_policy(env, scenarios, model, policy_name, mode, episodes)
            save_eval_csv(rows, str(eval_dir / f"test_eval_{policy_name}_{mode}.csv"))


def _eval_ppo_do_nothing(config, episodes):
    ckpt = ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints" / "ppo_init_do_nothing" / "latest.pt"
    if not ckpt.exists():
        _run([sys.executable, "-m", "scripts.rl_mitigation.train_ppo", "--case", "ieee14", "--config", config, "--smoke", "--steps", "2048", "--init", "do_nothing"])
    for mode in ["deterministic", "stochastic"]:
        _run([
            sys.executable, "-m", "scripts.rl_mitigation.evaluate_policy", "--config", config, "--split", "test",
            "--episodes", str(episodes), "--with-agent", "--checkpoint", str(ckpt),
            "--policy-name", "ppo_do_nothing_init", "--eval-mode", mode,
        ])


def _write_report(args, episodes):
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    full = _read_json(base / "pretrain" / "oracle_bc_full_diagnostics.json")
    positive = _read_json(base / "pretrain" / "oracle_bc_positive_only_diagnostics.json")
    selected = _read_json(base / "ablation" / "safe_policy_threshold_selected.json")
    multi = _read_csv(base / "tables" / "table_policy_multi_metric_test_summary.csv")
    paired = _read_csv(base / "stats" / "paired_policy_comparison.csv")
    safe = next((row for row in multi if row["policy"] == "safe_oracle_bc_full"), {})
    safe_pair = next((row for row in paired if row["policy_a"] == "safe_oracle_bc_full" and row["policy_b"] == "do_nothing" and row["metric"] == "negative_return"), {})
    lines = [
        "# IEEE14 Safe Oracle-BC Pipeline Report",
        "",
        "## Required Answers",
        "1. positive-only oracle BC 会失败的原因：训练集只包含主动缓解正样本，缺少 non-improvable 场景应当 do-nothing 的负样本，容易盲目主动断线。",
        f"2. full oracle BC 是否降低 non-improvable 误动作：full dataset 包含 {full.get('num_non_improvable')} 个 do-nothing 标签，mean_prob_do_nothing_on_non_improvable={full.get('mean_prob_do_nothing_on_non_improvable', 0.0):.4f}。",
        f"3. safe gate 是否进一步降低误动作：val 选择 active_prob_threshold={selected.get('active_prob_threshold')}, margin_threshold={selected.get('margin_threshold')}。",
        f"4. safe_oracle_bc_full test mean_negative_return={float(safe.get('mean_negative_return', 0.0)):.4f}, pf_failed_ratio={float(safe.get('pf_failed_ratio', 0.0)):.4f}。",
        f"   paired negative_return direction={safe_pair.get('direction', 'n/a')}, mean_diff={float(safe_pair.get('mean_diff', 0.0)):.4f}, CI=[{float(safe_pair.get('bootstrap_ci_low', 0.0)):.4f}, {float(safe_pair.get('bootstrap_ci_high', 0.0)):.4f}]。",
        "5. 改善是否集中在 improvable/high-risk 子集：见 analysis/improvable_subset_summary.csv。",
        "6. 这不属于原论文方法；属于 oracle 辅助初始化和安全门控诊断增强。",
        "7. 毕业论文应表述为增强实验，不应声称原论文 PPO 已稳定学到缓解策略。",
        "",
        "## BC Diagnostics",
        f"- positive_only samples: {positive.get('num_bc_samples')}",
        f"- full samples: {full.get('num_bc_samples')}, improvable={full.get('num_improvable')}, non_improvable={full.get('num_non_improvable')}",
        "",
        "## Multi-Metric Safe Policy Summary",
        json.dumps(safe, indent=2, ensure_ascii=False),
    ]
    out = base / "reports" / "ieee14_safe_bc_pipeline_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Safe BC report written to {out}")


def _run(cmd):
    subprocess.run(cmd, cwd=ROOT, check=True)


def _read_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    main()
